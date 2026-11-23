"""Capa de entrada: API REST, WebSocket Gateway y cliente web estático."""
from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.http import http_router
from app.api.websockets import SessionNotificationComponent, websocket_router
from app.core.errors import ConcurrencyError, GameRuleError, NotFoundError, StaleStateError
from app.core.orchestrator.turn_orchestrator import TurnOrchestratorComponent

STATIC_DIR = Path(__file__).with_name("static")
TIMER_TICK_SECONDS = 1.0
logger = logging.getLogger(__name__)

_ERRORS = {
    GameRuleError: 409,
    StaleStateError: 409,
    ConcurrencyError: 423,
    NotFoundError: 404,
    ValueError: 400,
}


async def _timer_loop(orchestrator: TurnOrchestratorComponent) -> None:
    """Actor Sistema/Temporizador: expira turnos vencidos (RF10, CU06)."""
    while True:
        await asyncio.sleep(TIMER_TICK_SECONDS)
        try:
            await run_in_threadpool(orchestrator.expirar_turnos)
        except Exception:  # noqa: BLE001 - el temporizador no debe morir; se registra el error
            logger.exception("Fallo al expirar turnos")


def create_app(
    orchestrator: TurnOrchestratorComponent,
    gateway: SessionNotificationComponent,
    run_timer: bool = True,
) -> FastAPI:
    @contextlib.asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        gateway.bind_loop(asyncio.get_running_loop())
        task = asyncio.create_task(_timer_loop(orchestrator)) if run_timer else None
        yield
        if task:
            task.cancel()

    app = FastAPI(title="Apuntado Digital", version="1.0.0", lifespan=lifespan)

    for error, status in _ERRORS.items():
        app.add_exception_handler(error, _handler(status))

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(http_router(orchestrator))
    app.include_router(websocket_router(gateway))
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
    return app


def _handler(status: int):
    async def handle(_: Request, exc: Exception) -> JSONResponse:
        content = {"detail": str(exc)}
        if isinstance(exc, StaleStateError):
            content["current_version"] = exc.current_version
        return JSONResponse(status_code=status, content=content)

    return handle
