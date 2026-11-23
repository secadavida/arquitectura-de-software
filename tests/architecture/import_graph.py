"""Grafo de importaciones estáticas del paquete ``app`` (vía AST).

Se usa para las fitness functions de ciclos y para las métricas Ca/Ce/I/A/D.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = "app"
PACKAGE_DIR = ROOT / PACKAGE


def module_name(path: Path) -> str:
    parts = path.relative_to(ROOT).with_suffix("").parts
    return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)


def _imports(tree: ast.AST) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            found.add(node.module)
    return {name for name in found if name == PACKAGE or name.startswith(PACKAGE + ".")}


@dataclass
class ModuleInfo:
    name: str
    imports: set[str]
    classes: int = 0
    abstract_classes: int = 0


@dataclass
class ImportGraph:
    modules: dict[str, ModuleInfo] = field(default_factory=dict)

    def edges(self) -> dict[str, set[str]]:
        return {
            m: {i for i in info.imports if i in self.modules and i != m}  # sin auto-referencias
            for m, info in self.modules.items()
        }


def _is_abstract(node: ast.ClassDef) -> bool:
    bases = {getattr(b, "id", getattr(b, "attr", "")) for b in node.bases}
    return bool(bases & {"ABC", "Protocol"})


def build_graph() -> ImportGraph:
    graph = ImportGraph()
    for path in sorted(PACKAGE_DIR.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        graph.modules[module_name(path)] = ModuleInfo(
            name=module_name(path),
            imports=_imports(tree),
            classes=len(classes),
            abstract_classes=sum(_is_abstract(c) for c in classes),
        )
    return graph


def find_cycles(edges: dict[str, set[str]]) -> list[list[str]]:
    """Ciclos detectados con DFS (colores blanco/gris/negro)."""
    color: dict[str, int] = {node: 0 for node in edges}
    cycles: list[list[str]] = []

    def visit(node: str, stack: list[str]) -> None:
        color[node] = 1
        stack.append(node)
        for nxt in sorted(edges.get(node, ())):
            if color.get(nxt) == 1:
                cycles.append(stack[stack.index(nxt):] + [nxt])
            elif color.get(nxt) == 0:
                visit(nxt, stack)
        stack.pop()
        color[node] = 2

    for node in sorted(edges):
        if color[node] == 0:
            visit(node, [])
    return cycles


def component_of(module: str, depth: int = 2) -> str:
    """``apuntaditos.plugins.clasica`` -> ``apuntaditos.plugins`` (depth=2)."""
    return ".".join(module.split(".")[:depth])
