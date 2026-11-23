"""API REST. Todas las operaciones pasan por el TurnOrchestratorComponent
(ADR-05: la capa de entrada nunca toca reglas ni persistencia directamente)."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.orchestrator.turn_orchestrator import TurnOrchestratorComponent


class CreateGameRequest(BaseModel):
    mode: str
    players: list[str] = Field(min_length=2, max_length=4)
    turn_seconds: int = Field(default=60, ge=0, le=600)
    seed: int | None = None


class DrawRequest(BaseModel):
    player: str
    source: str = Field(pattern="^(mazo|pozo)$")
    version: int


class CardRequest(BaseModel):
    player: str
    card: str
    version: int


def http_router(orchestrator: TurnOrchestratorComponent) -> APIRouter:
    router = APIRouter(prefix="/api")

    @router.get("/modes")
    def modes() -> list[dict[str, Any]]:
        return orchestrator.modalidades()

    @router.get("/games")
    def recent() -> list[dict[str, Any]]:
        return orchestrator.partidas_recientes()

    @router.post("/games", status_code=201)
    def create(body: CreateGameRequest) -> dict[str, Any]:
        return orchestrator.crear_partida(body.mode, body.players, body.turn_seconds, body.seed)

    @router.get("/rooms/{pin}")
    def by_pin(pin: str) -> dict[str, Any]:
        return orchestrator.buscar_por_pin(pin)

    @router.get("/games/{game_id}")
    def state(game_id: str, player: str | None = None) -> dict[str, Any]:
        return orchestrator.estado(game_id, player)

    @router.get("/games/{game_id}/events")
    def events(game_id: str) -> list[dict[str, Any]]:
        return orchestrator.eventos(game_id)

    @router.post("/games/{game_id}/draw")
    def draw(game_id: str, body: DrawRequest) -> dict[str, Any]:
        return orchestrator.robar(game_id, body.player, body.source, body.version)

    @router.post("/games/{game_id}/discard")
    def discard(game_id: str, body: CardRequest) -> dict[str, Any]:
        return orchestrator.descartar(game_id, body.player, body.card, body.version)

    @router.post("/games/{game_id}/close")
    def close(game_id: str, body: CardRequest) -> dict[str, Any]:
        return orchestrator.declarar_cierre(game_id, body.player, body.card, body.version)

    return router
