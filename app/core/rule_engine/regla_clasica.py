"""ReglaClasicaStrategy — Modalidad Clásica (4-3-3).

Al cerrar, el jugador descarta una carta al pozo y las 11 que conserva deben
formar 1 cuarta + 2 ternas disjuntas + 1 sobrante. Partida de mano cerrada:
el primer cierre válido gana, sin acumulación de penalizaciones (ADR-03).
"""
from __future__ import annotations

from typing import Sequence

from app.core.deck_card.cards import Card
from app.core.rule_engine.hand_evaluator import Arrangement, best_arrangement, best_partial
from app.core.rule_engine.interfaces import IRuleEvaluator, ResultadoValidacion, VictoryResult

PLAN_CIERRE = (4, 3, 3)


class ReglaClasicaStrategy(IRuleEvaluator):
    mode_id = "CLASICA"
    nombre = "Clásica (4-3-3)"
    descripcion = "Cierra con 1 cuarta + 2 ternas + 1 carta sobrante. Gana el primero en cerrar."
    acumula_puntos = False
    umbral_derrota = None

    def validar_cierre(self, mano: Sequence[Card]) -> ResultadoValidacion:
        organizacion = best_arrangement(mano, PLAN_CIERRE)
        if organizacion is None:
            return ResultadoValidacion(
                False,
                "Cierre inválido: se necesita 1 cuarta y 2 ternas (además del descarte).",
                best_partial(mano).leftover_points,
            )
        return ResultadoValidacion(
            True, "Cierre válido: 1 cuarta + 2 ternas.", organizacion.leftover_points, organizacion
        )

    def calcular_penalizacion(self, mano: Sequence[Card]) -> int:
        return best_partial(mano).leftover_points

    def es_fin_de_partida(self, acumulados: dict[str, int], cerrador: str) -> VictoryResult:
        return VictoryResult([cerrador], [j for j in acumulados if j != cerrador])

    def sugerir(self, mano: Sequence[Card]) -> Arrangement:
        return best_arrangement(mano, PLAN_CIERRE) or best_partial(mano)
