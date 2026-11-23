"""HandEvaluatorComponent: analiza un arreglo de cartas y verifica la estructura de
cuartas y ternas, o calcula el valor de las sobrantes (rol declarado en el E1, 4.2).

Una *combinación* (terna = 3 cartas, cuarta = 4 cartas) puede ser:

* **Grupo**: mismo valor, palos distintos (p. ej. 7 de oros, 7 de copas, 7 de bastos).
* **Escalera**: mismo palo y valores consecutivos en la secuencia 1..7, 10, 11, 12.

El buscador recorre las combinaciones disjuntas con bitmasks; con manos de 11-12
cartas el espacio es pequeño y la búsqueda es exacta (no heurística).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from itertools import combinations
from typing import Iterator, Sequence

from app.core.deck_card.cards import Card, hand_points


class MeldKind(str, Enum):
    GROUP = "grupo"
    RUN = "escalera"


@dataclass(frozen=True)
class Meld:
    kind: MeldKind
    cards: tuple[Card, ...]

    @property
    def size(self) -> int:
        return len(self.cards)


@dataclass(frozen=True)
class Arrangement:
    """Reparto de una mano en combinaciones + cartas sobrantes."""

    melds: tuple[Meld, ...] = ()
    leftovers: tuple[Card, ...] = field(default_factory=tuple)

    @property
    def leftover_points(self) -> int:
        return hand_points(self.leftovers)


def is_group(cards: Sequence[Card]) -> bool:
    suits = {c.suit for c in cards}
    return len({c.rank for c in cards}) == 1 and len(suits) == len(cards)


def is_run(cards: Sequence[Card]) -> bool:
    if len({c.suit for c in cards}) != 1:
        return False
    ordinals = sorted(c.ordinal for c in cards)
    return ordinals == list(range(ordinals[0], ordinals[0] + len(cards)))


def classify(cards: Sequence[Card]) -> Meld | None:
    """Devuelve la combinación si las cartas forman terna/cuarta válida."""
    if len(cards) not in (3, 4):
        return None
    if is_group(cards):
        return Meld(MeldKind.GROUP, tuple(cards))
    if is_run(cards):
        return Meld(MeldKind.RUN, tuple(sorted(cards, key=lambda c: c.ordinal)))
    return None


def candidate_melds(cards: Sequence[Card], sizes: set[int]) -> list[tuple[int, Meld]]:
    """Todas las combinaciones válidas (con su bitmask) de los tamaños pedidos."""
    found: list[tuple[int, Meld]] = []
    indexed = list(enumerate(cards))
    for size in sorted(sizes):
        for combo in combinations(indexed, size):
            meld = classify([card for _, card in combo])
            if meld is not None:
                mask = sum(1 << i for i, _ in combo)
                found.append((mask, meld))
    return found


def _remove_size(sizes: tuple[int, ...], size: int) -> tuple[int, ...]:
    as_list = list(sizes)
    as_list.remove(size)
    return tuple(as_list)


def _disjoint_selections(
    candidates: list[tuple[int, Meld]], sizes: tuple[int, ...], used: int, start: int
) -> Iterator[tuple[int, tuple[Meld, ...]]]:
    """Genera selecciones de combinaciones disjuntas cuyos tamaños son ``sizes``."""
    if not sizes:
        yield used, ()
        return
    for idx in range(start, len(candidates)):
        mask, meld = candidates[idx]
        if mask & used or meld.size not in sizes:
            continue
        rest = _remove_size(sizes, meld.size)
        for final_mask, tail in _disjoint_selections(candidates, rest, used | mask, idx + 1):
            yield final_mask, (meld,) + tail


def best_arrangement(cards: Sequence[Card], plan: tuple[int, ...]) -> Arrangement | None:
    """Mejor reparto (mínimo de puntos sobrantes) usando combinaciones de tamaños ``plan``.

    Devuelve ``None`` si no existe ninguna selección que cumpla el plan.
    """
    candidates = candidate_melds(cards, set(plan))
    best: Arrangement | None = None
    for mask, melds in _disjoint_selections(candidates, plan, 0, 0):
        leftovers = tuple(c for i, c in enumerate(cards) if not mask & (1 << i))
        option = Arrangement(melds, leftovers)
        if best is None or option.leftover_points < best.leftover_points:
            best = option
    return best


def best_of_plans(cards: Sequence[Card], plans: Sequence[tuple[int, ...]]) -> Arrangement | None:
    """Mejor reparto considerando varios planes alternativos."""
    options = [a for a in (best_arrangement(cards, p) for p in plans) if a is not None]
    return min(options, key=lambda a: a.leftover_points, default=None)


#: Planes parciales: de 0 a 3 combinaciones de 3 o 4 cartas.
PARTIAL_PLANS: tuple[tuple[int, ...], ...] = (
    (), (3,), (4,), (3, 3), (4, 3), (4, 4), (3, 3, 3), (4, 3, 3), (4, 4, 3),
)


def best_partial(cards: Sequence[Card]) -> Arrangement:
    """Organización que minimiza los puntos sobrantes (siempre existe)."""
    best = best_of_plans(cards, PARTIAL_PLANS)
    return best if best is not None else Arrangement((), tuple(cards))
