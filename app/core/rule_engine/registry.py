"""GameModeRegistry: catálogo de modalidades (ADR-03).

El registro se llena **al iniciar el servidor** desde el composition root
(``app/main.py``). No hay carga dinámica de plug-ins: agregar una modalidad es
crear una clase que implemente ``IRuleEvaluator`` y registrarla (trade-off
aceptado en ADR-03: requiere redesplegar).
"""
from __future__ import annotations

from app.core.errors import NotFoundError
from app.core.rule_engine.interfaces import IRuleEvaluator


class GameModeRegistry:
    def __init__(self) -> None:
        self._modalidades: dict[str, IRuleEvaluator] = {}

    def registrar(self, regla: IRuleEvaluator) -> "GameModeRegistry":
        if not regla.mode_id:
            raise ValueError("La regla debe declarar mode_id")
        if regla.mode_id in self._modalidades:
            raise ValueError(f"Modalidad duplicada: {regla.mode_id}")
        self._modalidades[regla.mode_id] = regla
        return self

    def obtener(self, mode_id: str) -> IRuleEvaluator:
        try:
            return self._modalidades[mode_id]
        except KeyError as exc:
            raise NotFoundError(f"Modalidad desconocida: {mode_id}") from exc

    def modalidades(self) -> list[IRuleEvaluator]:
        return list(self._modalidades.values())
