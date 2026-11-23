"""Composition root: único lugar que conoce todos los módulos y los conecta.

* Registra las modalidades en el GameModeRegistry al iniciar (ADR-03).
* Conecta Redis (estado vivo) y PostgreSQL (historial) según ADR-04.

Variables de entorno:
  REDIS_URL     redis://localhost:6379/0  (si falta: almacén en memoria, solo desarrollo)
  DATABASE_URL  postgresql+psycopg2://...  (si falta: SQLite local, solo desarrollo)
"""
from __future__ import annotations

import logging
import os

from fastapi import FastAPI

from app.api import create_app
from app.api.websockets import SessionNotificationComponent
from app.core.game_session.session import GameSessionComponent
from app.core.orchestrator.turn_orchestrator import TurnOrchestratorComponent
from app.core.rule_engine.regla_apuntado import ReglaApuntadoStrategy
from app.core.rule_engine.regla_clasica import ReglaClasicaStrategy
from app.core.rule_engine.registry import GameModeRegistry
from app.infrastructure.persistence.memory_repo import InMemoryGameStateStore
from app.infrastructure.persistence.postgres_repo import PostgresHistoryStore, create_db_engine
from app.infrastructure.persistence.redis_repo import RedisGameStateStore

logger = logging.getLogger("app")
DEV_DATABASE_URL = "sqlite:///data/apuntado-dev.db"


def build_registry() -> GameModeRegistry:
    return GameModeRegistry().registrar(ReglaClasicaStrategy()).registrar(ReglaApuntadoStrategy())


def _state_store(redis_url: str | None):
    if redis_url:
        return RedisGameStateStore.from_url(redis_url)
    logger.warning("REDIS_URL no definido: estado vivo en memoria (solo desarrollo).")
    return InMemoryGameStateStore()


def _database_url(url: str | None) -> str:
    if url:
        return url
    logger.warning("DATABASE_URL no definido: SQLite local %s (solo desarrollo).", DEV_DATABASE_URL)
    os.makedirs("data", exist_ok=True)
    return DEV_DATABASE_URL


def build_app(redis_url: str | None = None, database_url: str | None = None, run_timer: bool = True) -> FastAPI:
    gateway = SessionNotificationComponent()
    session = GameSessionComponent(
        registry=build_registry(),
        state_store=_state_store(redis_url),
        history=PostgresHistoryStore(create_db_engine(_database_url(database_url))),
        notifier=gateway,
    )
    return create_app(TurnOrchestratorComponent(session), gateway, run_timer=run_timer)
