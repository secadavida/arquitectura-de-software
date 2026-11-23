"""Entidades de identidad (diagrams/entity_and_mapping.uml).

En el MVP los jugadores son *invitados*: se crea un User por jugador sin
credenciales (Identity & Profile y Economy quedan fuera del alcance, ADR-07).
"""
from __future__ import annotations

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Numeric, String, Table, Uuid, func

from app.infrastructure.models.base import metadata

users = Table(
    "users",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("username", String(80), nullable=False, unique=True),
    Column("email", String(120), nullable=True),
    Column("password_hash", String(200), nullable=True),
    Column("is_guest", Boolean, nullable=False, default=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

wallets = Table(
    "wallets",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("user_id", Uuid, ForeignKey("users.id"), nullable=False, unique=True),
    Column("balance", Numeric(12, 2), nullable=False, default=0),
)
