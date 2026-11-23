"""Contrato estable del Rule Engine (ADR-02 / ADR-03).

``IRuleEvaluator`` es la interfaz ``ReglaJuego`` del E1: el TurnOrchestrator y el
GameSession solo dependen de esta abstracción, nunca de ReglaClasicaStrategy ni de
ReglaApuntadoStrategy (contrato 2 de ``.importlinter``).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Sequence

from app.core.deck_card.cards import Card
from app.core.rule_engine.hand_evaluator import Arrangement


@dataclass(frozen=True)
class ResultadoValidacion:
    """Veredicto del cierre y su causa: el orquestador no necesita conocer el algoritmo."""

    es_valida: bool
    causa: str
    puntos_sobrantes: int = 0
    organizacion: Arrangement | None = field(default=None, compare=False)


@dataclass(frozen=True)
class VictoryResult:
    """Resultado determinista de evaluar el final de la partida (RD del E1)."""

    ganadores: list[str]
    perdedores: list[str]


class IRuleEvaluator(ABC):
    """Strategy de una modalidad de juego (ReglaJuego)."""

    #: Identificador estable de la modalidad (GameMode).
    mode_id: str = ""
    nombre: str = ""
    descripcion: str = ""
    #: ``True`` si las penalizaciones se acumulan entre rondas (Apuntado).
    acumula_puntos: bool = False
    umbral_derrota: int | None = None

    @abstractmethod
    def validar_cierre(self, mano: Sequence[Card]) -> ResultadoValidacion:
        """Valida las cartas que quedan tras el descarte de cierre."""

    @abstractmethod
    def calcular_penalizacion(self, mano: Sequence[Card]) -> int:
        """Puntos que suma un jugador que NO cerró, con su mejor organización."""

    @abstractmethod
    def es_fin_de_partida(self, acumulados: dict[str, int], cerrador: str) -> VictoryResult | None:
        """Decide si la partida terminó tras liquidar la ronda."""

    @abstractmethod
    def sugerir(self, mano: Sequence[Card]) -> Arrangement:
        """Mejor organización de la mano (ayuda visual para el jugador)."""
