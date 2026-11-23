"""Serialización del GameState a/desde un diccionario plano (JSON).

Lo usan Redis (estado vivo) y PostgreSQL (snapshot por ronda, mitigación R4).
"""
from __future__ import annotations

from typing import Any

from app.core.deck_card.cards import Card
from app.core.deck_card.deck import Deck, DiscardPile
from app.core.game_session.state import GameState, GameStatus, Phase, PlayerState, RoundRecord

SNAPSHOT_VERSION = 1


def _codes(cards: list[Card]) -> list[str]:
    return [c.code for c in cards]


def _cards(codes: list[str]) -> list[Card]:
    return [Card.from_code(c) for c in codes]


def to_dict(state: GameState) -> dict[str, Any]:
    return {
        "snapshot_version": SNAPSHOT_VERSION,
        "id": state.id,
        "mode_id": state.mode_id,
        "room_pin": state.room_pin,
        "seed": state.seed,
        "turn_seconds": state.turn_seconds,
        "turn_deadline": state.turn_deadline,
        "last_drawn": state.last_drawn,
        "round_number": state.round_number,
        "turn_index": state.turn_index,
        "phase": state.phase.value,
        "status": state.status.value,
        "version": state.version,
        "refills": state.refills,
        "deck": _codes(state.deck.cards),
        "pile": _codes(state.pile.cards),
        "players": [
            {"id": p.id, "name": p.name, "hand": _codes(p.hand), "score": p.score}
            for p in state.players
        ],
        "history": [vars(r) for r in state.history],
        "winner_ids": state.winner_ids,
        "loser_ids": state.loser_ids,
    }


def from_dict(data: dict[str, Any]) -> GameState:
    players = [
        PlayerState(id=p["id"], name=p["name"], hand=_cards(p["hand"]), score=p["score"])
        for p in data["players"]
    ]
    state = GameState(data["id"], data["mode_id"], players, data["seed"])
    state.room_pin = data["room_pin"]
    state.turn_seconds = data["turn_seconds"]
    state.turn_deadline = data["turn_deadline"]
    state.last_drawn = data["last_drawn"]
    state.round_number = data["round_number"]
    state.turn_index = data["turn_index"]
    state.phase = Phase(data["phase"])
    state.status = GameStatus(data["status"])
    state.version = data["version"]
    state.refills = data["refills"]
    state.deck = Deck(_cards(data["deck"]))
    state.pile = DiscardPile(_cards(data["pile"]))
    state.history = [RoundRecord(**r) for r in data["history"]]
    state.winner_ids = list(data["winner_ids"])
    state.loser_ids = list(data["loser_ids"])
    return state
