"""Fitness Functions de gobernanza (E2 sección 5, ampliadas en el E3).

Prueba 1: aislamiento de las estrategias de reglas (contratos 1, 2 y 4).
Prueba 2: aislamiento de la capa de entrada respecto al almacenamiento (contratos 5 y 6).
Prueba 3: ausencia de dependencias cíclicas (contrato 3 + grafo AST completo).
Además: complejidad ciclomática <= 10 y distancia a la secuencia principal.
"""
import subprocess
import sys
from pathlib import Path

import pytest
from radon.complexity import cc_visit
from radon.visitors import Function

from tests.architecture.import_graph import PACKAGE_DIR, ROOT, build_graph, find_cycles
from tests.architecture.metrics import STRATEGIES, compute

CC_MAX = 10
LINT_IMPORTS = Path(sys.executable).with_name("lint-imports")


def _cc_offenders(path: Path) -> list[str]:
    return [
        f"{path.relative_to(ROOT).as_posix()}:{b.name} CC={b.complexity}"
        for b in cc_visit(path.read_text(encoding="utf-8"))
        if isinstance(b, Function) and b.complexity > CC_MAX
    ]


# ------------------------------------------------------------------ E2 5.2.2 (originales)
def test_import_linter_contracts():
    """Valida las reglas de aislamiento definidas en .importlinter."""
    result = subprocess.run([str(LINT_IMPORTS)], capture_output=True, text=True, cwd=ROOT)
    assert result.returncode == 0, f"Violación de arquitectura:\n{result.stdout}"


def test_complejidad_ciclomatica_hand_evaluator():
    """Valida que la complejidad del HandEvaluator sea <= 10."""
    assert _cc_offenders(ROOT / "app/core/rule_engine/hand_evaluator.py") == []


def test_complejidad_ciclomatica_round_scoring():
    """Valida que la complejidad del RoundScoring sea <= 10."""
    assert _cc_offenders(ROOT / "app/core/rule_engine/round_scoring.py") == []


# ------------------------------------------------------------------ Ampliaciones E3
def test_complejidad_ciclomatica_de_toda_la_solucion():
    offenders = [o for path in PACKAGE_DIR.rglob("*.py") for o in _cc_offenders(path)]
    assert offenders == [], "Funciones con CC > 10: " + ", ".join(offenders)


def test_sin_dependencias_ciclicas_entre_modulos():
    cycles = find_cycles(build_graph().edges())
    assert cycles == [], f"Dependencias cíclicas: {cycles}"


@pytest.mark.parametrize("strategy", STRATEGIES)
def test_estrategias_cerca_de_la_secuencia_principal(strategy):
    metrics = {m.name: m for m in compute(build_graph())}
    m = metrics[strategy]
    assert m.distance <= 0.5, f"{m.name} D={m.distance:.2f} ({m.zone})"
