"""ReglaApuntadoStrategy — Modalidad Apuntado a 101.

Cierre: 3 ternas (se admite que alguna sea cuarta) con sobrantes **< 5** puntos
(exactamente 5 es inválido). Quien cierra suma 0; los demás suman sus sobrantes.
Sesión multironda: quien acumule >= 101 pierde y la partida termina.
"""
from __future__ import annotations

from typing import Sequence

from app.core.deck_card.cards import Card
from app.core.rule_engine.hand_evaluator import Arrangement, best_of_plans, best_partial
from app.core.rule_engine.interfaces import IRuleEvaluator, ResultadoValidacion, VictoryResult

PLANES_CIERRE = ((3, 3, 3), (4, 3, 3), (4, 4, 3))
MAX_SOBRANTE_EXCLUSIVO = 5
UMBRAL_DERROTA = 101


class ReglaApuntadoStrategy(IRuleEvaluator):
    mode_id = "APUNTADO"
    nombre = "Apuntado (101)"
    descripcion = (
        "Cierra con 3 ternas y sobrantes < 5 pts. Los demás suman sus sobrantes; "
        "quien llegue a 101 pierde."
    )
    acumula_puntos = True
    umbral_derrota = UMBRAL_DERROTA

    def validar_cierre(self, mano: Sequence[Card]) -> ResultadoValidacion:
        organizacion = best_of_plans(mano, PLANES_CIERRE)
        if organizacion is None:
            return ResultadoValidacion(
                False, "Cierre inválido: se necesitan 3 ternas.", best_partial(mano).leftover_points
            )
        puntos = organizacion.leftover_points
        if puntos >= MAX_SOBRANTE_EXCLUSIVO:
            return ResultadoValidacion(
                False,
                f"Cierre inválido: tus sobrantes suman {puntos} pts y deben ser menos de "
                f"{MAX_SOBRANTE_EXCLUSIVO}.",
                puntos,
                organizacion,
            )
        return ResultadoValidacion(
            True, f"Cierre válido: 3 ternas y {puntos} pts sobrantes.", puntos, organizacion
        )

    def calcular_penalizacion(self, mano: Sequence[Card]) -> int:
        return best_partial(mano).leftover_points

    def es_fin_de_partida(self, acumulados: dict[str, int], cerrador: str) -> VictoryResult | None:
        perdedores = [j for j, puntos in acumulados.items() if puntos >= UMBRAL_DERROTA]
        if not perdedores:
            return None
        restantes = {j: p for j, p in acumulados.items() if j not in perdedores}
        mejor = min(restantes.values(), default=None)
        return VictoryResult([j for j, p in restantes.items() if p == mejor], perdedores)

    def sugerir(self, mano: Sequence[Card]) -> Arrangement:
        return best_of_plans(mano, PLANES_CIERRE) or best_partial(mano)
