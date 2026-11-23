"""GameSessionComponent: mediador del ciclo de vida de la partida (E2, 1.2).

Coordina el inicio de partida, la liquidación de ronda (RoundScoring + transacción
ACID en PostgreSQL), la reanudación desde snapshot (R4) y la publicación de
eventos para auditoría y notificación.
"""
from __future__ import annotations

import time
from contextlib import AbstractContextManager
from datetime import datetime, timezone
from typing import Any, Callable

from app.core.errors import NotFoundError
from app.core.game_session.ports import GameStateStore, HistoryStore, Notifier, NullNotifier
from app.core.game_session.snapshot import from_dict, to_dict
from app.core.game_session.state import GameState
from app.core.game_session.views import game_view, mode_view
from app.core.rule_engine.interfaces import IRuleEvaluator
from app.core.rule_engine.registry import GameModeRegistry
from app.core.rule_engine.round_scoring import ResultadoRonda, RoundScoring


def _play(state: GameState, event: str, player_id: str | None, data: dict[str, Any]) -> dict[str, Any]:
    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "round": state.round_number,
        "event": event,
        "player_id": player_id,
        "data": data,
    }


class GameSessionComponent:
    def __init__(
        self,
        registry: GameModeRegistry,
        state_store: GameStateStore,
        history: HistoryStore,
        notifier: Notifier | None = None,
        scoring: RoundScoring | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.registry = registry
        self._store = state_store
        self._history = history
        self._notifier = notifier or NullNotifier()
        self._scoring = scoring or RoundScoring()
        self.clock = clock

    def set_notifier(self, notifier: Notifier) -> None:
        self._notifier = notifier

    # ---------------------------------------------------------------- consultas
    def modalidades(self) -> list[dict[str, Any]]:
        return [mode_view(r) for r in self.registry.modalidades()]

    def regla_de(self, state: GameState) -> IRuleEvaluator:
        return self.registry.obtener(state.mode_id)

    def vista(self, game_id: str, player_id: str | None) -> dict[str, Any]:
        state = self.cargar(game_id)
        return game_view(state, self.regla_de(state), player_id, self.clock())

    def eventos(self, game_id: str) -> list[dict[str, Any]]:
        self.cargar(game_id)
        return self._history.plays(game_id) + self._store.pending_plays(game_id)

    def buscar_por_pin(self, pin: str) -> str:
        game_id = self._history.find_by_pin(pin)
        if game_id is None:
            raise NotFoundError(f"No existe una sala con PIN {pin}")
        return game_id

    def partidas_recientes(self) -> list[dict[str, Any]]:
        return self._history.list_sessions()

    def partidas_activas(self) -> list[str]:
        return self._store.active_games()

    def bloquear(self, game_id: str) -> AbstractContextManager[None]:
        return self._store.lock(game_id)

    # ---------------------------------------------------------------- ciclo de vida
    def crear_partida(
        self, mode_id: str, nombres: list[str], turn_seconds: int, seed: int | None = None
    ) -> GameState:
        regla = self.registry.obtener(mode_id)
        state = GameState.create(regla.mode_id, nombres, turn_seconds, self.clock(), seed)
        plays = [
            _play(state, "partida_creada", None, {
                "modalidad": mode_id,
                "jugadores": [p.name for p in state.players],
                "pin": state.room_pin,
                "seed": state.seed,
            }),
            _play(state, "ronda_iniciada", None, {"ronda": state.round_number}),
        ]
        snapshot = to_dict(state)
        self._history.create_session(snapshot, plays)
        self._store.save(state.id, snapshot)
        return state

    def cargar(self, game_id: str) -> GameState:
        """Lee el estado vivo de Redis; si no está (caída/reinicio) reanuda desde el
        último snapshot de PostgreSQL (mitigación R4)."""
        data = self._store.load(game_id)
        if data is not None:
            return from_dict(data)
        snapshot = self._history.latest_snapshot(game_id)
        if snapshot is None:
            raise NotFoundError(f"Partida no encontrada: {game_id}")
        state = from_dict(snapshot)
        self._store.save(state.id, snapshot)
        self._store.append_play(state.id, _play(state, "partida_reanudada", None, {"version": state.version}))
        return state

    def guardar(self, state: GameState, evento: str, player_id: str | None, datos: dict[str, Any]) -> None:
        """Persiste una jugada en Redis (estado + bandeja Outbox) y notifica."""
        state.version += 1
        self._store.save(state.id, to_dict(state))
        self._store.append_play(state.id, _play(state, evento, player_id, datos))
        self._notifier.publish(state.id, evento, state.version)

    def registrar(self, state: GameState, evento: str, player_id: str | None, datos: dict[str, Any]) -> None:
        """Registra un hecho de auditoría que no cambia el estado (p. ej. cierre inválido)."""
        self._store.append_play(state.id, _play(state, evento, player_id, datos))

    def cerrar_ronda(self, state: GameState, cerrador: str, datos_cierre: dict[str, Any]) -> ResultadoRonda:
        """Liquidación: RoundScoring -> transacción ACID (PostgreSQL) -> Redis -> notificar."""
        regla = self.regla_de(state)
        cerrada = state.round_number
        resultado = self._scoring.liquidar(
            regla,
            {p.id: p.hand for p in state.players},
            {p.id: p.score for p in state.players},
            cerrador,
        )
        state.apply_settlement(cerrador, resultado.penalizaciones, resultado.acumulados)
        pendientes = self._store.pending_plays(state.id)
        plays = list(pendientes)
        plays.append(_play(state, "cierre_intentado", cerrador, datos_cierre))
        plays.append(_play(state, "ronda_liquidada", cerrador, {
            "ronda": cerrada,
            "penalizaciones": resultado.penalizaciones,
            "acumulados": resultado.acumulados,
        }))
        self._avanzar(state, resultado, plays)
        state.version += 1
        snapshot = to_dict(state)
        self._history.settle_round(
            state.id, cerrada, cerrador, resultado.penalizaciones, resultado.acumulados,
            plays, snapshot, None if state.is_finished else state.round_number,
        )
        self._store.clear_plays(state.id, len(pendientes))
        self._store.save(state.id, snapshot)
        self._despues_de_liquidar(state)
        return resultado

    def _avanzar(self, state: GameState, resultado: ResultadoRonda, plays: list[dict[str, Any]]) -> None:
        if resultado.victoria is not None:
            state.finish(resultado.victoria.ganadores, resultado.victoria.perdedores)
            plays.append(_play(state, "partida_finalizada", None, {
                "ganadores": resultado.victoria.ganadores,
                "perdedores": resultado.victoria.perdedores,
            }))
        else:
            state.start_round(self.clock())
            plays.append(_play(state, "ronda_iniciada", None, {"ronda": state.round_number}))

    def _despues_de_liquidar(self, state: GameState) -> None:
        if state.is_finished:
            self._store.deactivate(state.id)
            self._notifier.publish(state.id, "GameFinished", state.version)
        else:
            self._notifier.publish(state.id, "RoundClosed", state.version)
