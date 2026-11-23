"""DeckManagementComponent: inicializar la baraja, mezclarla y suministrar cartas
al mazo o al pozo de descarte (declaración de rol del E1, sección 4.2)."""
from __future__ import annotations

import random

from app.core.deck_card.cards import RANKS, Card, Suit
from app.core.errors import GameRuleError

HAND_SIZE = 11


def build_deck(copies: int = 1) -> list[Card]:
    """Crea ``copies`` barajas españolas de 40 cartas."""
    return [Card(rank, suit, copy) for copy in range(copies) for suit in Suit for rank in RANKS]


def decks_needed(players: int) -> int:
    """Con 4 jugadores x 11 cartas no alcanza una baraja de 40: se usan 2."""
    return 1 if players * HAND_SIZE + 1 <= 40 else 2


class Deck:
    """Mazo boca abajo del que se roba."""

    def __init__(self, cards: list[Card]) -> None:
        self._cards = list(cards)

    @classmethod
    def shuffled(cls, copies: int, rng: random.Random) -> "Deck":
        cards = build_deck(copies)
        rng.shuffle(cards)
        return cls(cards)

    def draw(self) -> Card:
        if not self._cards:
            raise GameRuleError("El mazo está vacío.")
        return self._cards.pop()

    def refill(self, cards: list[Card], rng: random.Random) -> None:
        """Rebaraja las cartas recibidas (normalmente el pozo) como nuevo mazo."""
        self._cards = list(cards)
        rng.shuffle(self._cards)

    def __len__(self) -> int:
        return len(self._cards)

    @property
    def cards(self) -> list[Card]:
        return list(self._cards)


class DiscardPile:
    """Pozo de descarte: sólo la carta del tope es visible y robable."""

    def __init__(self, cards: list[Card] | None = None) -> None:
        self._cards = list(cards or [])

    def push(self, card: Card) -> None:
        self._cards.append(card)

    def top(self) -> Card | None:
        return self._cards[-1] if self._cards else None

    def take_top(self) -> Card:
        if not self._cards:
            raise GameRuleError("El pozo está vacío.")
        return self._cards.pop()

    def take_all_but_top(self) -> list[Card]:
        """Retira todas las cartas salvo la del tope (para rebarajar el mazo)."""
        rest, self._cards = self._cards[:-1], self._cards[-1:]
        return rest

    def __len__(self) -> int:
        return len(self._cards)

    @property
    def cards(self) -> list[Card]:
        return list(self._cards)
