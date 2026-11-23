"""Persistencia relacional (ADR-04): PostgreSQL en 3FN como fuente de verdad.

* La creación de la partida y la liquidación de cada ronda se ejecutan en **una
  única transacción ACID** (mitigación R1).
* La ronda se bloquea con ``SELECT ... FOR UPDATE`` y debe seguir ``OPEN``; un
  segundo cierre simultáneo se rechaza (mitigación R6).
* Las jugadas acumuladas en Redis (Outbox) se vuelcan en la misma transacción.

Funciona también con SQLite (pruebas locales y modo desarrollo); en SQLite el
``FOR UPDATE`` se ignora y la exclusión la da el cerrojo SET NX de Redis.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Engine, create_engine, select, update
from sqlalchemy.engine import Connection
from sqlalchemy.pool import StaticPool

from app.core.errors import ConcurrencyError
from app.infrastructure.models import metadata
from app.infrastructure.models.game_session import (
    game_sessions,
    game_snapshots,
    player_sessions,
    plays,
    rooms,
    rounds,
    scores,
)
from app.infrastructure.models.user import users, wallets


def create_db_engine(url: str) -> Engine:
    options: dict[str, Any] = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False}
        if url in ("sqlite://", "sqlite:///:memory:"):
            options["poolclass"] = StaticPool
    engine = create_engine(url, **options)
    metadata.create_all(engine)  # Release checklist: esquema aplicado al iniciar (idempotente)
    return engine


def _ts(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _iso_utc(value: datetime) -> str:
    """SQLite pierde la zona horaria; PostgreSQL la conserva. Se normaliza a UTC."""
    return (value if value.tzinfo else value.replace(tzinfo=timezone.utc)).isoformat()


def _new_id() -> uuid.UUID:
    return uuid.uuid4()


class PostgresHistoryStore:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    # ---------------------------------------------------------------- escritura
    def create_session(self, snapshot: dict[str, Any], plays_: list[dict[str, Any]]) -> None:
        session_id = uuid.UUID(snapshot["id"])
        with self._engine.begin() as conn:
            user_ids = [self._guest(conn, p["name"]) for p in snapshot["players"]]
            room_id = _new_id()
            conn.execute(rooms.insert().values(
                id=room_id, pin_code=snapshot["room_pin"], host_id=user_ids[0],
                status="IN_PROGRESS", max_players=len(user_ids), turn_seconds=snapshot["turn_seconds"],
            ))
            conn.execute(game_sessions.insert().values(
                id=session_id, room_id=room_id, modality=snapshot["mode_id"], status="IN_PROGRESS",
            ))
            for player, user_id in zip(snapshot["players"], user_ids):
                conn.execute(player_sessions.insert().values(
                    id=_new_id(), session_id=session_id, user_id=user_id, seat=player["id"],
                    accumulated_score=0, is_connected=True,
                ))
            self._open_round(conn, session_id, snapshot["round_number"])
            self._insert_plays(conn, session_id, plays_)
            self._insert_snapshot(conn, session_id, snapshot)

    def settle_round(
        self,
        game_id: str,
        round_number: int,
        closer_seat: str,
        penalties: dict[str, int],
        totals: dict[str, int],
        plays_: list[dict[str, Any]],
        snapshot: dict[str, Any],
        next_round: int | None,
    ) -> None:
        session_id = uuid.UUID(game_id)
        with self._engine.begin() as conn:
            round_id = self._lock_open_round(conn, session_id, round_number)
            seats = self._seats(conn, session_id)
            conn.execute(update(rounds).where(rounds.c.id == round_id).values(
                status="CLOSED", winner_id=seats[closer_seat],
            ))
            for seat, ps_id in seats.items():
                conn.execute(scores.insert().values(
                    id=_new_id(), round_id=round_id, player_session_id=ps_id,
                    points=penalties[seat], accumulated_after=totals[seat],
                ))
                conn.execute(update(player_sessions).where(player_sessions.c.id == ps_id).values(
                    accumulated_score=totals[seat],
                ))
            if next_round is not None:
                self._open_round(conn, session_id, next_round)
            else:
                self._finish(conn, session_id)
            self._insert_plays(conn, session_id, plays_)
            self._insert_snapshot(conn, session_id, snapshot)

    # ---------------------------------------------------------------- lectura
    def latest_snapshot(self, game_id: str) -> dict[str, Any] | None:
        query = (
            select(game_snapshots.c.state)
            .where(game_snapshots.c.session_id == uuid.UUID(game_id))
            .order_by(game_snapshots.c.version.desc())
            .limit(1)
        )
        with self._engine.connect() as conn:
            row = conn.execute(query).first()
        return dict(row.state) if row else None

    def find_by_pin(self, pin: str) -> str | None:
        query = (
            select(game_sessions.c.id)
            .join(rooms, rooms.c.id == game_sessions.c.room_id)
            .where(rooms.c.pin_code == pin)
            .order_by(game_sessions.c.started_at.desc())
            .limit(1)
        )
        with self._engine.connect() as conn:
            row = conn.execute(query).first()
        return str(row.id) if row else None

    def plays(self, game_id: str) -> list[dict[str, Any]]:
        session_id = uuid.UUID(game_id)
        query = (
            select(plays.c.timestamp, plays.c.action_type, plays.c.payload,
                   rounds.c.round_number, player_sessions.c.seat)
            .join(rounds, rounds.c.id == plays.c.round_id)
            .outerjoin(player_sessions, player_sessions.c.id == plays.c.player_id)
            .where(rounds.c.session_id == session_id)
            .order_by(plays.c.timestamp)
        )
        with self._engine.connect() as conn:
            rows = conn.execute(query).all()
        return [
            {"ts": _iso_utc(r.timestamp), "round": r.round_number, "event": r.action_type,
             "player_id": r.seat, "data": r.payload}
            for r in rows
        ]

    def list_sessions(self, limit: int = 20) -> list[dict[str, Any]]:
        query = (
            select(game_sessions.c.id, game_sessions.c.modality, game_sessions.c.status,
                   game_sessions.c.started_at, rooms.c.pin_code)
            .join(rooms, rooms.c.id == game_sessions.c.room_id)
            .order_by(game_sessions.c.started_at.desc())
            .limit(limit)
        )
        with self._engine.connect() as conn:
            rows = conn.execute(query).all()
        return [
            {"game_id": str(r.id), "mode": r.modality, "status": r.status,
             "started_at": _iso_utc(r.started_at) if r.started_at else None, "room_pin": r.pin_code}
            for r in rows
        ]

    # ---------------------------------------------------------------- internos
    @staticmethod
    def _guest(conn: Connection, name: str) -> uuid.UUID:
        user_id = _new_id()
        conn.execute(users.insert().values(id=user_id, username=f"{name}#{user_id.hex[:8]}", is_guest=True))
        conn.execute(wallets.insert().values(id=_new_id(), user_id=user_id, balance=0))
        return user_id

    @staticmethod
    def _open_round(conn: Connection, session_id: uuid.UUID, number: int) -> None:
        conn.execute(rounds.insert().values(
            id=_new_id(), session_id=session_id, round_number=number, status="OPEN",
        ))

    @staticmethod
    def _lock_open_round(conn: Connection, session_id: uuid.UUID, number: int) -> uuid.UUID:
        row = conn.execute(
            select(rounds.c.id, rounds.c.status)
            .where(rounds.c.session_id == session_id, rounds.c.round_number == number)
            .with_for_update()
        ).first()
        if row is None or row.status != "OPEN":
            raise ConcurrencyError(f"La ronda {number} ya fue cerrada.")
        return row.id

    @staticmethod
    def _seats(conn: Connection, session_id: uuid.UUID) -> dict[str, uuid.UUID]:
        rows = conn.execute(
            select(player_sessions.c.seat, player_sessions.c.id)
            .where(player_sessions.c.session_id == session_id)
        ).all()
        return {r.seat: r.id for r in rows}

    @staticmethod
    def _finish(conn: Connection, session_id: uuid.UUID) -> None:
        conn.execute(update(game_sessions).where(game_sessions.c.id == session_id).values(
            status="FINISHED", ended_at=datetime.now(timezone.utc),
        ))
        room_id = conn.execute(
            select(game_sessions.c.room_id).where(game_sessions.c.id == session_id)
        ).scalar_one()
        conn.execute(update(rooms).where(rooms.c.id == room_id).values(status="FINISHED"))

    def _insert_plays(self, conn: Connection, session_id: uuid.UUID, plays_: list[dict[str, Any]]) -> None:
        round_ids = {
            r.round_number: r.id
            for r in conn.execute(
                select(rounds.c.round_number, rounds.c.id).where(rounds.c.session_id == session_id)
            ).all()
        }
        seats = self._seats(conn, session_id)
        for play in plays_:
            data = play["data"]
            conn.execute(plays.insert().values(
                id=_new_id(),
                round_id=round_ids[play["round"]],
                player_id=seats.get(play["player_id"]) if play["player_id"] else None,
                action_type=play["event"],
                card_played=data.get("carta") or data.get("descarte") or data.get("descarte_automatico"),
                payload=data,
                timestamp=_ts(play["ts"]),
            ))

    @staticmethod
    def _insert_snapshot(conn: Connection, session_id: uuid.UUID, snapshot: dict[str, Any]) -> None:
        conn.execute(game_snapshots.insert().values(
            id=_new_id(), session_id=session_id, round_number=snapshot["round_number"],
            version=snapshot["version"], state=snapshot,
        ))
