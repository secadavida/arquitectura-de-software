"""Implementación en memoria del GameStateStore (pruebas y modo desarrollo sin Redis).

Mismo contrato que ``RedisGameStateStore``: cerrojo no bloqueante con espera
corta y ``ConcurrencyError`` si está tomado.
"""
from __future__ import annotations

import copy
import threading
from collections import defaultdict
from contextlib import contextmanager
from typing import Any, Iterator

from app.core.errors import ConcurrencyError

LOCK_WAIT_SECONDS = 0.3


class InMemoryGameStateStore:
    def __init__(self) -> None:
        self._states: dict[str, dict[str, Any]] = {}
        self._plays: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self._locks: dict[str, threading.Lock] = defaultdict(threading.Lock)
        self._active: set[str] = set()
        self._guard = threading.Lock()

    def load(self, game_id: str) -> dict[str, Any] | None:
        data = self._states.get(game_id)
        return copy.deepcopy(data) if data else None

    def save(self, game_id: str, snapshot: dict[str, Any]) -> None:
        self._states[game_id] = copy.deepcopy(snapshot)
        if snapshot["status"] == "IN_PROGRESS":
            self._active.add(game_id)

    @contextmanager
    def lock(self, game_id: str) -> Iterator[None]:
        with self._guard:
            game_lock = self._locks[game_id]
        if not game_lock.acquire(timeout=LOCK_WAIT_SECONDS):
            raise ConcurrencyError("Otra acción está modificando la partida; reintenta.")
        try:
            yield
        finally:
            game_lock.release()

    def append_play(self, game_id: str, play: dict[str, Any]) -> None:
        self._plays[game_id].append(copy.deepcopy(play))

    def pending_plays(self, game_id: str) -> list[dict[str, Any]]:
        return copy.deepcopy(self._plays[game_id])

    def clear_plays(self, game_id: str, count: int) -> None:
        del self._plays[game_id][:count]

    def active_games(self) -> list[str]:
        return sorted(self._active)

    def deactivate(self, game_id: str) -> None:
        self._active.discard(game_id)

    def flush_state(self, game_id: str) -> None:
        """Simula una caída de Redis para la partida (pruebas de R4)."""
        self._states.pop(game_id, None)
