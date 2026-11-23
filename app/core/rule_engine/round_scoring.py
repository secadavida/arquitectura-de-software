"""RoundScoringComponent: aplica penalizaciones tras un cierre de ronda y calcula
el acumulado frente al límite de la modalidad (rol declarado en el E1, 4.2).

Trabaja con datos planos (manos y acumulados por jugador) para no depender del
estado de la sesión: así el Rule Engine sigue siendo la capa más baja.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from app.core.deck_card.cards import Card
from app.core.rule_engine.interfaces import IRuleEvaluator, VictoryResult


@dataclass(frozen=True)
class ResultadoRonda:
    cerrador: str
    penalizaciones: dict[str, int]
    acumulados: dict[str, int]
    victoria: VictoryResult | None

    @property
    def fin_de_partida(self) -> bool:
        return self.victoria is not None


class RoundScoring:
    def liquidar(
        self,
        regla: IRuleEvaluator,
        manos: dict[str, Sequence[Card]],
        acumulados: dict[str, int],
        cerrador: str,
    ) -> ResultadoRonda:
        penalizaciones = {
            jugador: 0 if jugador == cerrador else regla.calcular_penalizacion(mano)
            for jugador, mano in manos.items()
        }
        nuevos = dict(acumulados)
        if regla.acumula_puntos:
            nuevos = {j: acumulados[j] + penalizaciones[j] for j in acumulados}
        return ResultadoRonda(cerrador, penalizaciones, nuevos, regla.es_fin_de_partida(nuevos, cerrador))
