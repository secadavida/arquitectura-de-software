"""Métricas de modularidad de Richards & Ford (cap. 3) por componente.

* Ca (acoplamiento aferente): componentes que dependen de éste.
* Ce (acoplamiento eferente): componentes de los que éste depende.
* I  (inestabilidad) = Ce / (Ca + Ce).
* A  (abstracción)   = clases abstractas (ABC/Protocol) / clases totales.
* D  (distancia a la secuencia principal) = |A + I - 1|.

Cada estrategia de reglas se mide como componente propio; los módulos del
game_engine (app.core.*) por subpaquete y el resto por paquete.
"""
from __future__ import annotations

from dataclasses import dataclass

from tests.architecture.import_graph import ImportGraph, component_of

#: Composition root (conecta todo por diseño), paquetes contenedores y el núcleo
#: compartido de errores: se excluyen de Ca/Ce.
EXCLUDED = {"app", "app.main", "app.bootstrap", "app.core", "app.core.errors"}
STRATEGIES = ("app.core.rule_engine.regla_clasica", "app.core.rule_engine.regla_apuntado")


@dataclass(frozen=True)
class ComponentMetrics:
    name: str
    ca: int
    ce: int
    abstract: int
    classes: int

    @property
    def instability(self) -> float:
        total = self.ca + self.ce
        return self.ce / total if total else 0.0

    @property
    def abstractness(self) -> float:
        return self.abstract / self.classes if self.classes else 0.0

    @property
    def distance(self) -> float:
        return abs(self.abstractness + self.instability - 1)

    @property
    def zone(self) -> str:
        if self.ca == self.ce == 0:
            return "aislado (solo lo conecta el composition root)"
        if self.distance <= 0.5:
            return "secuencia principal"
        return "zona de dolor" if self.abstractness + self.instability < 1 else "zona de inutilidad"


def component(module: str) -> str:
    if module in STRATEGIES:
        return module
    if module.startswith("app.core."):
        return component_of(module, 3)
    return component_of(module, 2)


def compute(graph: ImportGraph) -> list[ComponentMetrics]:
    deps: dict[str, set[str]] = {}
    totals: dict[str, list[int]] = {}
    for name, info in graph.modules.items():
        if name in EXCLUDED:
            continue
        comp = component(name)
        totals.setdefault(comp, [0, 0])
        totals[comp][0] += info.abstract_classes
        totals[comp][1] += info.classes
        targets = {component(i) for i in info.imports if i not in EXCLUDED}
        deps.setdefault(comp, set()).update(t for t in targets if t != comp)
    deps = {c: {t for t in ts if t in totals} for c, ts in deps.items()}
    return [
        ComponentMetrics(
            name=comp,
            ca=sum(1 for other, ts in deps.items() if comp in ts),
            ce=len(deps.get(comp, ())),
            abstract=totals[comp][0],
            classes=totals[comp][1],
        )
        for comp in sorted(totals)
    ]


def markdown_table(rows: list[ComponentMetrics]) -> str:
    lines = [
        "| Componente | Ca | Ce | I | A | D | Zona |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for r in rows:
        lines.append(
            f"| `{r.name}` | {r.ca} | {r.ce} | {r.instability:.2f} | {r.abstractness:.2f} "
            f"| {r.distance:.2f} | {r.zone} |"
        )
    return "\n".join(lines)
