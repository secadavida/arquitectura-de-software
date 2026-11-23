"""Entidades de partida en 3FN (E2 2.2 / 2.3, diagrams/entity_and_mapping.uml).

Extensiones respecto al diagrama del E2 (documentadas en ADR-04):
* ``player_sessions.seat``: asiento del jugador en la partida (p1..p4).
* ``scores``: puntaje de cada jugador en cada ronda (Round 1:N Score, E2 2.2).
* ``plays.payload``: detalle de la jugada (causa de un cierre inválido, etc.).
* ``game_snapshots``: snapshot del estado al cerrar cada ronda (mitigación R4).
"""
from __future__ import annotations

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    UniqueConstraint,
    Uuid,
    func,
)

from app.infrastructure.models.base import metadata

rooms = Table(
    "rooms",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("pin_code", String(6), nullable=False, index=True),
    Column("host_id", Uuid, ForeignKey("users.id"), nullable=False),
    Column("status", String(20), nullable=False),  # WAITING | IN_PROGRESS | FINISHED
    Column("max_players", Integer, nullable=False),
    Column("turn_seconds", Integer, nullable=False),
)

game_sessions = Table(
    "game_sessions",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("room_id", Uuid, ForeignKey("rooms.id"), nullable=False),
    Column("modality", String(20), nullable=False),  # CLASICA | APUNTADO
    Column("status", String(20), nullable=False),
    Column("started_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("ended_at", DateTime(timezone=True), nullable=True),
)

player_sessions = Table(
    "player_sessions",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("session_id", Uuid, ForeignKey("game_sessions.id"), nullable=False),
    Column("user_id", Uuid, ForeignKey("users.id"), nullable=False),
    Column("seat", String(4), nullable=False),
    Column("accumulated_score", Integer, nullable=False, default=0),
    Column("is_connected", Boolean, nullable=False, default=True),
    UniqueConstraint("session_id", "seat"),
)

rounds = Table(
    "rounds",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("session_id", Uuid, ForeignKey("game_sessions.id"), nullable=False),
    Column("round_number", Integer, nullable=False),
    Column("winner_id", Uuid, ForeignKey("player_sessions.id"), nullable=True),
    Column("status", String(10), nullable=False),  # OPEN | CLOSED
    UniqueConstraint("session_id", "round_number"),
)

scores = Table(
    "scores",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("round_id", Uuid, ForeignKey("rounds.id"), nullable=False),
    Column("player_session_id", Uuid, ForeignKey("player_sessions.id"), nullable=False),
    Column("points", Integer, nullable=False),
    Column("accumulated_after", Integer, nullable=False),
    UniqueConstraint("round_id", "player_session_id"),
)

plays = Table(
    "plays",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("round_id", Uuid, ForeignKey("rounds.id"), nullable=False),
    Column("player_id", Uuid, ForeignKey("player_sessions.id"), nullable=True),
    Column("action_type", String(40), nullable=False),
    Column("card_played", String(8), nullable=True),
    Column("payload", JSON, nullable=False),
    Column("timestamp", DateTime(timezone=True), nullable=False),
)

game_snapshots = Table(
    "game_snapshots",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("session_id", Uuid, ForeignKey("game_sessions.id"), nullable=False),
    Column("round_number", Integer, nullable=False),
    Column("version", Integer, nullable=False),
    Column("state", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)
