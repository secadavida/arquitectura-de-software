"""Módulo Deck & Card: entidades de la baraja española de 40 cartas."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Suit(str, Enum):
    """Palos de la baraja española."""

    OROS = "O"
    COPAS = "C"
    ESPADAS = "E"
    BASTOS = "B"


#: Valores de la baraja española de 40 cartas (sin 8 ni 9). El 7 y la Sota (10)
#: se consideran consecutivos para las escaleras.
RANKS: tuple[int, ...] = (1, 2, 3, 4, 5, 6, 7, 10, 11, 12)

#: Las figuras (Sota, Caballo, Rey) valen 10 puntos en el conteo de sobrantes.
FIGURE_POINTS = 10


@dataclass(frozen=True, order=True)
class Card:
    """Carta inmutable. ``copy`` distingue cartas idénticas cuando se usan 2 barajas."""

    rank: int
    suit: Suit
    copy: int = 0

    def __post_init__(self) -> None:
        if self.rank not in RANKS:
            raise ValueError(f"Valor de carta inválido: {self.rank}")

    @property
    def points(self) -> int:
        """Puntos que suma la carta cuando queda como sobrante."""
        return self.rank if self.rank <= 7 else FIGURE_POINTS

    @property
    def ordinal(self) -> int:
        """Posición de la carta en la secuencia 1..7, 10, 11, 12 (0..9)."""
        return RANKS.index(self.rank)

    @property
    def code(self) -> str:
        """Código compacto y estable, p. ej. ``12E0`` = Rey de espadas (baraja 0)."""
        return f"{self.rank}{self.suit.value}{self.copy}"

    @classmethod
    def from_code(cls, code: str) -> "Card":
        if len(code) < 3:
            raise ValueError(f"Código de carta inválido: {code!r}")
        return cls(int(code[:-2]), Suit(code[-2]), int(code[-1]))


def hand_points(cards: list[Card] | tuple[Card, ...]) -> int:
    """Suma los puntos de un conjunto de cartas."""
    return sum(card.points for card in cards)
