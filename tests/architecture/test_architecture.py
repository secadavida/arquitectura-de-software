import pytest
import subprocess
from radon.complexity import cc_visit
from radon.visitors import Function

def test_import_linter_contracts():
    """Valida las reglas de aislamiento definidas en .importlinter"""
    result = subprocess.run(["lint-imports"], capture_output=True, text=True)
    assert result.returncode == 0, f"Violación de arquitectura:\n{result.stdout}"

def test_complejidad_ciclomatica_hand_evaluator():
    """Valida que la complejidad del motor de reglas sea <= 10"""
    ruta_archivo = "app/core/rule_engine/hand_evaluator.py"
    try:
        with open(ruta_archivo, "r") as f:
            codigo = f.read()
        bloques = cc_visit(codigo)
        for bloque in bloques:
            if isinstance(bloque, Function):
                assert bloque.complexity <= 10, f"Función '{bloque.name}' excede CC=10."
    except FileNotFoundError:
        pytest.skip("Archivo no implementado aún.")
