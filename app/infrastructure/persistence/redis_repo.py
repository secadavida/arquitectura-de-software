"""Estado efímero de la sala en vivo (ADR-04) y control de concurrencia (ADR-05).

Claves:
* ``game:{id}:state`` — snapshot JSON del GameState (mazo, manos, turno, temporizador).
* ``game:{id}:plays`` — bandeja Outbox con las jugadas aún no volcadas a PostgreSQL.
* ``game:{id}:lock``  — cerrojo ``SET NX PX`` (una sola acción modifica la partida a la vez).
* ``games:active``    — partidas en curso (las recorre el temporizador).
"""
from __future__ import annotations

import json
import time
import uuid
from contextlib import contextmanager
from typing import Any, Iterator

from redis import Redis
from redis.exceptions import WatchError

from app.core.errors import ConcurrencyError

STATE_TTL_SECONDS = 7 * 24 * 3600
LOCK_TTL_MS = 5000
LOCK_WAIT_SECONDS = 0.3


class RedisGameStateStore:
    def __init__(self, client: Redis) -> None:
        self._r = client

    @classmethod
    def from_url(cls, url: str) -> "RedisGameStateStore":
        return cls(Redis.from_url(url, decode_responses=True))

    def load(self, game_id: str) -> dict[str, Any] | None:
        raw = self._r.get(f"game:{game_id}:state")
        return json.loads(raw) if raw else None

    def save(self, game_id: str, snapshot: dict[str, Any]) -> None:
        pipe = self._r.pipeline()
        pipe.set(f"game:{game_id}:state", json.dumps(snapshot), ex=STATE_TTL_SECONDS)
        if snapshot["status"] == "IN_PROGRESS":
            pipe.sadd("games:active", game_id)
        pipe.execute()

    @contextmanager
    def lock(self, game_id: str) -> Iterator[None]:
        key, token = f"game:{game_id}:lock", uuid.uuid4().hex
        deadline = time.monotonic() + LOCK_WAIT_SECONDS
        while not self._r.set(key, token, nx=True, px=LOCK_TTL_MS):
            if time.monotonic() >= deadline:
                raise ConcurrencyError("Otra acción está modificando la partida; reintenta.")
            time.sleep(0.02)
        try:
            yield
        finally:
            self._release(key, token)

    def _release(self, key: str, token: str) -> None:
        """Libera el cerrojo sólo si sigue siendo nuestro (WATCH/MULTI)."""
        with self._r.pipeline() as pipe:
            try:
                pipe.watch(key)
                if pipe.get(key) == token:
                    pipe.multi()
                    pipe.delete(key)
                    pipe.execute()
            except WatchError:
                pass  # expiró y otro proceso lo tomó: no es nuestro, no se borra

    def append_play(self, game_id: str, play: dict[str, Any]) -> None:
        self._r.rpush(f"game:{game_id}:plays", json.dumps(play))

    def pending_plays(self, game_id: str) -> list[dict[str, Any]]:
        return [json.loads(p) for p in self._r.lrange(f"game:{game_id}:plays", 0, -1)]

    def clear_plays(self, game_id: str, count: int) -> None:
        if count:
            self._r.ltrim(f"game:{game_id}:plays", count, -1)

    def active_games(self) -> list[str]:
        return sorted(self._r.smembers("games:active"))

    def deactivate(self, game_id: str) -> None:
        self._r.srem("games:active", game_id)
