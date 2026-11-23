"""SessionNotificationComponent — WebSocket Gateway (ADR-05).

Mantiene conexiones full-duplex por partida y difunde eventos (TurnStarted,
CardPlayed, RoundClosed, GameFinished...). El mensaje solo lleva el tipo de
evento y la versión: cada cliente vuelve a pedir **su** vista, así nunca recibe
manos ajenas (RNF03). Al reconectar, el cliente recibe el estado completo (R5).
"""
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

#: Traducción de eventos internos a los eventos de dominio del E2 (ADR-05).
EVENT_NAMES = {
    "robo": "CardDrawn",
    "descarte": "CardPlayed",
    "turno_expirado": "TurnExpired",
    "RoundClosed": "RoundClosed",
    "GameFinished": "GameFinished",
}


class SessionNotificationComponent:
    def __init__(self) -> None:
        self._clients: dict[str, set[WebSocket]] = defaultdict(set)
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    async def connect(self, game_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._loop = asyncio.get_running_loop()
        self._clients[game_id].add(websocket)

    def disconnect(self, game_id: str, websocket: WebSocket) -> None:
        self._clients[game_id].discard(websocket)

    def publish(self, game_id: str, event: str, version: int) -> None:
        """Puede llamarse desde hilos del threadpool: se agenda en el event loop."""
        if self._loop is None or not self._clients.get(game_id):
            return
        message = {"type": EVENT_NAMES.get(event, event), "version": version}
        asyncio.run_coroutine_threadsafe(self._broadcast(game_id, message), self._loop)

    async def _broadcast(self, game_id: str, message: dict) -> None:
        for websocket in list(self._clients[game_id]):
            try:
                await websocket.send_json(message)
            except Exception:  # noqa: BLE001 - socket cerrado: se registra y se retira
                logger.info("WebSocket cerrado durante el envío a la partida %s", game_id)
                self.disconnect(game_id, websocket)


def websocket_router(gateway: SessionNotificationComponent) -> APIRouter:
    router = APIRouter()

    @router.websocket("/ws/games/{game_id}")
    async def live(websocket: WebSocket, game_id: str) -> None:
        await gateway.connect(game_id, websocket)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            gateway.disconnect(game_id, websocket)

    return router
