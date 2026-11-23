"""Genera el reporte de métricas estructurales (sección 4.2 del informe).

Uso:  python -m scripts.metrics_report [salida.md]

Incluye complejidad ciclomática (Radon), mantenibilidad y Ca/Ce/I/A/D por
componente. En CI se publica como resumen del job y como artefacto.
"""
from __future__ import annotations

import sys
from pathlib import Path

from radon.complexity import cc_rank, cc_visit
from radon.metrics import mi_visit

from tests.architecture.import_graph import PACKAGE_DIR, ROOT, build_graph, find_cycles
from tests.architecture.metrics import compute, markdown_table

FOCUS = (
    "core/rule_engine/hand_evaluator.py",
    "core/rule_engine/regla_clasica.py",
    "core/rule_engine/regla_apuntado.py",
    "core/rule_engine/round_scoring.py",
)


def _blocks():
    for path in sorted(PACKAGE_DIR.rglob("*.py")):
        rel = path.relative_to(PACKAGE_DIR).as_posix()
        for block in cc_visit(path.read_text(encoding="utf-8")):
            yield rel, block


def cc_section() -> list[str]:
    blocks = list(_blocks())
    values = [b.complexity for _, b in blocks]
    lines = [
        "## Complejidad ciclomática (Radon)",
        "",
        f"- Bloques analizados: **{len(values)}**",
        f"- CC promedio: **{sum(values) / len(values):.2f}**",
        f"- CC máxima: **{max(values)}** (umbral de la fitness function: 10; deseable < 5)",
        f"- Bloques con CC >= 5: **{sum(v >= 5 for v in values)}**",
        "",
        "### Métodos de evaluación de ternas/cuartas y liquidación",
        "",
        "| Archivo | Bloque | CC | Rango |",
        "|---|---|---:|:---:|",
    ]
    for rel, block in blocks:
        if rel in FOCUS:
            name = f"{block.classname}.{block.name}" if getattr(block, "classname", None) else block.name
            lines.append(f"| `{rel}` | `{name}` | {block.complexity} | {cc_rank(block.complexity)} |")
    return lines


def mi_section() -> list[str]:
    lines = ["## Índice de mantenibilidad (Radon MI)", "", "| Módulo | MI |", "|---|---:|"]
    for path in sorted(PACKAGE_DIR.rglob("*.py")):
        score = mi_visit(path.read_text(encoding="utf-8"), multi=True)
        lines.append(f"| `{path.relative_to(ROOT).as_posix()}` | {score:.1f} |")
    return lines


def coupling_section() -> list[str]:
    graph = build_graph()
    cycles = find_cycles(graph.edges())
    return [
        "## Acoplamiento y distancia a la secuencia principal",
        "",
        "Ca = aferente, Ce = eferente, I = Ce/(Ca+Ce), A = abstractas/total, D = |A+I-1|.",
        "Se excluyen el composition root (`app.bootstrap`, `app.main`) y `app.core.errors`.",
        "",
        markdown_table(compute(graph)),
        "",
        f"Dependencias cíclicas detectadas: **{len(cycles)}**",
    ]


def build_report() -> str:
    sections = [["# Reporte de métricas estructurales — Apuntado Digital (MVP)"], cc_section(),
                coupling_section(), mi_section()]
    return "\n\n".join("\n".join(s) for s in sections) + "\n"


if __name__ == "__main__":
    report = build_report()
    if len(sys.argv) > 1:
        Path(sys.argv[1]).parent.mkdir(parents=True, exist_ok=True)
        Path(sys.argv[1]).write_text(report, encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdout.write(report)
