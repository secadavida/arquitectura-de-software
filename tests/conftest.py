"""Fixtures compartidas.

Por defecto se usan dobles locales (almacén en memoria + SQLite en memoria). Si
existen ``REDIS_URL`` y ``DATABASE_URL`` (job de integración del CI con
servicios Redis y PostgreSQL), las pruebas marcadas con ``real_infra`` usan los
motores reales.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import pytest

from app.bootstrap import build_registry
from app.core.game_session.session import GameSessionComponent
from app.core.orchestrator.turn_orchestrator import TurnOrchestratorComponent
from app.infrastructure.persistence.memory_repo import InMemoryGameStateStore
from app.infrastructure.persistence.postgres_repo import PostgresHistoryStore, create_db_engine


class FakeClock:
    def __init__(self, now: float = 1_000_000.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@dataclass
class Env:
    orch: TurnOrchestratorComponent
    session: GameSessionComponent
    store: InMemoryGameStateStore
    history: PostgresHistoryStore
    clock: FakeClock


@pytest.fixture()
def env() -> Env:
    clock = FakeClock()
    store = InMemoryGameStateStore()
    history = PostgresHistoryStore(create_db_engine("sqlite://"))
    session = GameSessionComponent(build_registry(), store, history, clock=clock)
    return Env(TurnOrchestratorComponent(session), session, store, history, clock)


def real_infra_urls() -> tuple[str, str] | None:
    redis_url, db_url = os.getenv("REDIS_URL"), os.getenv("DATABASE_URL")
    return (redis_url, db_url) if redis_url and db_url else None
