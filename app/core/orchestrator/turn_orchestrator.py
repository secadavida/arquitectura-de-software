"""TurnOrchestratorComponent: mediador del flujo de turnos (E1 4.2, E2 1.2).

Coordina robar, descartar y declarar cierre, y la acción por defecto cuando vence
el temporizador (RF10 / CU06 / R8). Depende sólo de la interfaz IRuleEvaluator a
través de GameModeRegistry; nunca de ReglaClasicaStrategy ni ReglaApuntadoStrategy
(contrato 2 de .importlinter). Es la única puerta de entrada para la capa api
(ADR-05: la entrada no toca reglas ni persistencia sin el orquestador).
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Iterator

from app.core.errors import ConcurrencyError, NotFoundError, StaleStateError
from app.core.game_session.session import GameSessionComponent
from app.core.game_session.state import DrawSource, GameState, Phase

logger = logging.getLogger(__name__)


class TurnOrchestratorComponent:
    def __init__(self, session: GameSessionComponent) -> None:
        self._session = session

    # ---------------------------------------------------------------- consultas
    def modalidades(self) -> list[dict[str, Any]]:
        return self._session.modalidades()

    def estado(self, game_id: str, player_id: str | None = None) -> dict[str, Any]:
        return self._session.vista(game_id, player_id)

    def eventos(self, game_id: str) -> list[dict[str, Any]]:
        return self._session.eventos(game_id)

    def buscar_por_pin(self, pin: str) -> dict[str, Any]:
        return self.estado(self._session.buscar_por_pin(pin))

    def partidas_recientes(self) -> list[dict[str, Any]]:
        return self._session.partidas_recientes()

    # ---------------------------------------------------------------- comandos
    def crear_partida(
        self, mode_id: str, nombres: list[str], turn_seconds: int = 60, seed: int | None = None
    ) -> dict[str, Any]:
        state = self._session.crear_partida(mode_id, nombres, turn_seconds, seed)
        return {
            "game_id": state.id,
            "room_pin": state.room_pin,
            "mode": state.mode_id,
            "players": [{"id": p.id, "name": p.name} for p in state.players],
        }

    def robar(self, game_id: str, player_id: str, origen: str, version: int) -> dict[str, Any]:
        with self._comando(game_id, version) as state:
            card = state.draw(player_id, DrawSource(origen))
            self._session.guardar(state, "robo", player_id, {"origen": origen, "carta": card.code})
        return self.estado(game_id, player_id)

    def descartar(self, game_id: str, player_id: str, carta: str, version: int) -> dict[str, Any]:
        with self._comando(game_id, version) as state:
            card = state.discard(player_id, carta, self._session.clock())
            self._session.guardar(state, "descarte", player_id, {"carta": card.code})
        return self.estado(game_id, player_id)

    def declarar_cierre(self, game_id: str, player_id: str, carta: str, version: int) -> dict[str, Any]:
        """Flujo crítico: validar con IRuleEvaluator -> liquidar (GameSession) -> notificar."""
        with self._comando(game_id, version) as state:
            regla = self._session.regla_de(state)
            resultado = regla.validar_cierre(state.hand_after_discard(player_id, carta))
            datos = {
                "ronda": state.round_number,
                "descarte": carta,
                "valido": resultado.es_valida,
                "causa": resultado.causa,
                "puntos_sobrantes": resultado.puntos_sobrantes,
            }
            if resultado.es_valida:
                state.apply_close(player_id, carta)
                self._session.cerrar_ronda(state, player_id, datos)
            else:
                self._session.registrar(state, "cierre_intentado", player_id, datos)
        return {
            "valid": resultado.es_valida,
            "cause": resultado.causa,
            "leftover_points": resultado.puntos_sobrantes,
            "state": self.estado(game_id, player_id),
        }

    # ---------------------------------------------------------------- temporizador
    def expirar_turnos(self) -> int:
        """Aplica la acción por defecto a los turnos vencidos. Devuelve cuántos expiró."""
        expirados = 0
        for game_id in self._session.partidas_activas():
            try:
                expirados += self._expirar(game_id)
            except (ConcurrencyError, NotFoundError):
                logger.debug("Turno de %s no expirado: partida ocupada o inexistente", game_id)
        return expirados

    def _expirar(self, game_id: str) -> int:
        with self._session.bloquear(game_id):
            state = self._session.cargar(game_id)
            if not state.turn_expired(self._session.clock()):
                return 0
            jugador = state.current_player.id
            if state.phase is Phase.DRAW:
                state.draw(jugador, DrawSource.DECK)
            carta = state.last_drawn or state.current_player.hand[-1].code
            state.discard(jugador, carta, self._session.clock())
            self._session.guardar(state, "turno_expirado", jugador, {"descarte_automatico": carta})
            return 1

    # ---------------------------------------------------------------- internos
    @contextmanager
    def _comando(self, game_id: str, version: int) -> Iterator[GameState]:
        """Cerrojo SET NX + verificación de versión (mitigaciones R2 y R6)."""
        with self._session.bloquear(game_id):
            state = self._session.cargar(game_id)
            if version != state.version:
                raise StaleStateError(state.version)
            yield state
