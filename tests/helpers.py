"""Utilidades de prueba: construcción legible de manos."""
from __future__ import annotations

from app.core.deck_card.cards import Card, Suit

_SUITS = {"o": Suit.OROS, "c": Suit.COPAS, "e": Suit.ESPADAS, "b": Suit.BASTOS}


def cards(spec: str) -> list[Card]:
    """``cards("7o 7c 7e 12b")`` -> lista de cartas. Un sufijo ``'`` usa la copia 1."""
    result = []
    for token in spec.split():
        copy = 1 if token.endswith("'") else 0
        token = token.rstrip("'")
        result.append(Card(int(token[:-1]), _SUITS[token[-1]], copy))
    return result


def code(spec: str) -> str:
    """Código interno de una carta: ``code("12e") == "12E0"``."""
    return cards(spec)[0].code
