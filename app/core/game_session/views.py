"""Proyecciones de lectura (DTOs) para la capa de entrada.

Cada jugador sólo ve su propia mano (RNF03: el servidor es la fuente de verdad).
"""
from __future__ import annotations

from typing import Any

from app.core.deck_card.cards import Card
from app.core.game_session.state import GameState
from app.core.rule_engine.hand_evaluator import Arrangement
from app.core.rule_engine.interfaces import IRuleEvaluator

SUIT_NAMES = {"O": "oros", "C": "copas", "E": "espadas", "B": "bastos"}
RANK_NAMES = {1: "As", 10: "Sota", 11: "Caballo", 12: "Rey"}


def card_view(card: Card) -> dict[str, Any]:
    rank_name = RANK_NAMES.get(card.rank, str(card.rank))
    return {
        "code": card.code,
        "rank": card.rank,
        "suit": card.suit.value,
        "points": card.points,
        "label": f"{rank_name} de {SUIT_NAMES[card.suit.value]}",
    }


def arrangement_view(arrangement: Arrangement) -> dict[str, Any]:
    return {
        "melds": [
            {"kind": m.kind.value, "cards": [c.code for c in m.cards]} for m in arrangement.melds
        ],
        "leftovers": [c.code for c in arrangement.leftovers],
        "leftover_points": arrangement.leftover_points,
    }


def mode_view(regla: IRuleEvaluator) -> dict[str, Any]:
    return {
        "id": regla.mode_id,
        "name": regla.nombre,
        "description": regla.descripcion,
        "accumulates_points": regla.acumula_puntos,
        "loss_threshold": regla.umbral_derrota,
    }


def _names(state: GameState, ids: list[str]) -> list[str]:
    return [state.player(i).name for i in ids]


def _last_round(state: GameState) -> dict[str, Any] | None:
    if not state.history:
        return None
    record = state.history[-1]
    name = lambda pid: state.player(pid).name  # noqa: E731
    return {
        "number": record.number,
        "closer": name(record.closer_id),
        "penalties": {name(k): v for k, v in record.penalties.items()},
        "totals": {name(k): v for k, v in record.totals.items()},
        "hands": {name(k): v for k, v in record.hands.items()},
    }


def _me(state: GameState, regla: IRuleEvaluator, player_id: str | None) -> dict[str, Any] | None:
    if not player_id:
        return None
    player = state.player(player_id)
    return {
        "id": player.id,
        "name": player.name,
        "hand": [card_view(c) for c in player.hand],
        "suggestion": arrangement_view(regla.sugerir(player.hand)),
    }


def game_view(state: GameState, regla: IRuleEvaluator, player_id: str | None, now: float) -> dict[str, Any]:
    top = state.pile.top()
    return {
        "game_id": state.id,
        "room_pin": state.room_pin,
        "version": state.version,
        "mode": mode_view(regla),
        "status": state.status.value,
        "round": state.round_number,
        "phase": state.phase.value,
        "current_player_id": None if state.is_finished else state.current_player.id,
        "turn_seconds": state.turn_seconds,
        "turn_remaining": None if state.turn_deadline is None else max(0.0, state.turn_deadline - now),
        "me": _me(state, regla, player_id),
        "players": [
            {"id": p.id, "name": p.name, "score": p.score, "cards": len(p.hand)} for p in state.players
        ],
        "deck_count": len(state.deck),
        "pile_count": len(state.pile),
        "pile_top": card_view(top) if top else None,
        "last_round": _last_round(state),
        "winners": _names(state, state.winner_ids),
        "losers": _names(state, state.loser_ids),
    }
