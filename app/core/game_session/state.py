"""GameState: fuente lógica del estado actual de la partida (RD del E1).

Agnóstico de la modalidad: no sabe qué es una cuarta ni cuánto es 101. Cada
mutación incrementa ``version`` (mitigación R2 del E2: toda jugada declara la
versión sobre la que se hizo).
"""
from __future__ import annotations

import random
import secrets
import uuid
from dataclasses import dataclass, field
from enum import Enum

from app.core.deck_card.cards import Card
from app.core.deck_card.deck import HAND_SIZE, Deck, DiscardPile, decks_needed
from app.core.errors import GameRuleError, NotFoundError

MIN_PLAYERS = 2
MAX_PLAYERS = 4


class Phase(str, Enum):
    DRAW = "robar"
    DISCARD = "descartar"


class GameStatus(str, Enum):
    IN_PROGRESS = "IN_PROGRESS"
    FINISHED = "FINISHED"


class DrawSource(str, Enum):
    DECK = "mazo"
    PILE = "pozo"


@dataclass
class PlayerState:
    id: str
    name: str
    hand: list[Card] = field(default_factory=list)
    score: int = 0

    def find(self, code: str) -> Card:
        for card in self.hand:
            if card.code == code:
                return card
        raise GameRuleError(f"La carta {code} no está en la mano de {self.name}.")


@dataclass
class RoundRecord:
    number: int
    closer_id: str
    penalties: dict[str, int]
    totals: dict[str, int]
    hands: dict[str, list[str]]


class GameState:
    def __init__(self, game_id: str, mode_id: str, players: list[PlayerState], seed: int) -> None:
        self.id = game_id
        self.mode_id = mode_id
        self.players = players
        self.seed = seed
        self.room_pin = ""
        self.turn_seconds = 0
        self.turn_deadline: float | None = None
        self.last_drawn: str | None = None
        self.deck = Deck([])
        self.pile = DiscardPile()
        self.round_number = 0
        self.turn_index = 0
        self.phase = Phase.DRAW
        self.status = GameStatus.IN_PROGRESS
        self.version = 0
        self.refills = 0
        self.history: list[RoundRecord] = []
        self.winner_ids: list[str] = []
        self.loser_ids: list[str] = []

    # ------------------------------------------------------------------ creación
    @classmethod
    def create(
        cls, mode_id: str, names: list[str], turn_seconds: int, now: float, seed: int | None = None
    ) -> "GameState":
        clean = [n.strip()[:24] for n in names if n and n.strip()]
        if not MIN_PLAYERS <= len(clean) <= MAX_PLAYERS:
            raise GameRuleError(f"Se requieren entre {MIN_PLAYERS} y {MAX_PLAYERS} jugadores.")
        players = [PlayerState(id=f"p{i + 1}", name=name) for i, name in enumerate(clean)]
        seed = seed if seed is not None else secrets.randbelow(2**31)
        state = cls(str(uuid.uuid4()), mode_id, players, seed)
        state.room_pin = f"{secrets.randbelow(10**6):06d}"
        state.turn_seconds = max(0, turn_seconds)
        state.start_round(now)
        return state

    def _rng(self, purpose: str) -> random.Random:
        return random.Random(f"{self.seed}-{self.round_number}-{purpose}")

    def start_round(self, now: float) -> None:
        """Baraja, reparte 11 cartas por jugador y abre el pozo."""
        self.round_number += 1
        self.refills = 0
        self.deck = Deck.shuffled(decks_needed(len(self.players)), self._rng("deal"))
        for player in self.players:
            player.hand = [self.deck.draw() for _ in range(HAND_SIZE)]
        self.pile = DiscardPile([self.deck.draw()])
        self.turn_index = (self.round_number - 1) % len(self.players)
        self._start_turn(now)

    def _start_turn(self, now: float) -> None:
        self.phase = Phase.DRAW
        self.last_drawn = None
        self.turn_deadline = now + self.turn_seconds if self.turn_seconds else None

    # ------------------------------------------------------------------ consultas
    @property
    def current_player(self) -> PlayerState:
        return self.players[self.turn_index]

    @property
    def is_finished(self) -> bool:
        return self.status is GameStatus.FINISHED

    def player(self, player_id: str) -> PlayerState:
        for p in self.players:
            if p.id == player_id:
                return p
        raise NotFoundError(f"Jugador desconocido: {player_id}")

    def turn_expired(self, now: float) -> bool:
        return not self.is_finished and self.turn_deadline is not None and now >= self.turn_deadline

    def _require_turn(self, player_id: str, phase: Phase) -> PlayerState:
        if self.is_finished:
            raise GameRuleError("La partida ya terminó.")
        player = self.player(player_id)
        if player is not self.current_player:
            raise GameRuleError(f"No es tu turno: juega {self.current_player.name}.")
        if self.phase is not phase:
            raise GameRuleError(f"Acción no permitida: ahora toca {self.phase.value}.")
        return player

    # ------------------------------------------------------------------ acciones
    def draw(self, player_id: str, source: DrawSource) -> Card:
        player = self._require_turn(player_id, Phase.DRAW)
        card = self.pile.take_top() if source is DrawSource.PILE else self._draw_from_deck()
        player.hand.append(card)
        self.phase = Phase.DISCARD
        self.last_drawn = card.code
        return card

    def _draw_from_deck(self) -> Card:
        if len(self.deck) == 0:
            self.refills += 1
            self.deck.refill(self.pile.take_all_but_top(), self._rng(f"refill-{self.refills}"))
        return self.deck.draw()

    def discard(self, player_id: str, code: str, now: float) -> Card:
        player = self._require_turn(player_id, Phase.DISCARD)
        card = player.find(code)
        player.hand.remove(card)
        self.pile.push(card)
        self.turn_index = (self.turn_index + 1) % len(self.players)
        self._start_turn(now)
        return card

    def hand_after_discard(self, player_id: str, code: str) -> list[Card]:
        """Mano que quedaría si el jugador descarta ``code`` (no muta el estado)."""
        player = self._require_turn(player_id, Phase.DISCARD)
        remaining = list(player.hand)
        remaining.remove(player.find(code))
        return remaining

    def apply_close(self, player_id: str, code: str) -> Card:
        """Ejecuta el descarte de cierre sin pasar el turno."""
        player = self._require_turn(player_id, Phase.DISCARD)
        card = player.find(code)
        player.hand.remove(card)
        self.pile.push(card)
        return card

    def apply_settlement(self, closer_id: str, penalties: dict[str, int], totals: dict[str, int]) -> None:
        for player in self.players:
            player.score = totals[player.id]
        self.history.append(RoundRecord(
            number=self.round_number,
            closer_id=closer_id,
            penalties=penalties,
            totals=totals,
            hands={p.id: [c.code for c in p.hand] for p in self.players},
        ))

    def finish(self, winner_ids: list[str], loser_ids: list[str]) -> None:
        self.status = GameStatus.FINISHED
        self.winner_ids = winner_ids
        self.loser_ids = loser_ids
        self.turn_deadline = None
