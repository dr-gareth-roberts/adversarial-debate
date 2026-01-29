#!/usr/bin/env python3
"""Detect internal import cycles in the adversarial_debate package.

This script parses Python files under `src/adversarial_debate/` and builds a
best-effort import graph from `import` / `from ... import ...` statements.
It then reports any strongly-connected components (cycles).

Why not rely on runtime imports?
- Import cycles can be masked by conditional imports, `TYPE_CHECKING`, or other
  dynamic behavior.
- This is a fast, deterministic check suitable for CI.

Limitations:
- This is a static analysis of import statements only. It does not attempt to
  resolve dynamic imports.
"""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Module:
    name: str
    path: Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _src_root() -> Path:
    return _repo_root() / "src"


def _pkg_root() -> Path:
    return _src_root() / "adversarial_debate"


def _module_name_for(path: Path) -> str:
    rel = path.relative_to(_src_root())
    parts = list(rel.parts)
    if parts[-1] == "__init__.py":
        parts = parts[:-1]
    else:
        parts[-1] = parts[-1].removesuffix(".py")
    return ".".join(parts)


def _resolve_relative_import(
    *,
    current_module: str,
    level: int,
    module: str | None,
) -> str | None:
    if level <= 0:
        return module

    current_parts = current_module.split(".")
    # Determine the containing package for the current file.
    current_path = _pkg_root() / Path(*current_parts[1:])
    is_init = current_path.is_dir()
    base_parts = current_parts if is_init else current_parts[:-1]

    up = level - 1
    if up > len(base_parts):
        return None

    resolved = base_parts[: len(base_parts) - up]
    if module:
        resolved.extend(module.split("."))
    return ".".join(resolved)


def _iter_modules() -> list[Module]:
    pkg_root = _pkg_root()
    modules: list[Module] = []
    for py in pkg_root.rglob("*.py"):
        if "__pycache__" in py.parts:
            continue
        modules.append(Module(name=_module_name_for(py), path=py))
    return modules


def _build_graph(modules: list[Module]) -> dict[str, set[str]]:
    known = {m.name for m in modules}
    graph: dict[str, set[str]] = {m.name: set() for m in modules}

    for m in modules:
        tree = ast.parse(m.path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name
                    if name in known:
                        graph[m.name].add(name)
                    elif name.startswith("adversarial_debate."):
                        # Collapse deep imports to the nearest known module/package.
                        parts = name.split(".")
                        while parts and ".".join(parts) not in known:
                            parts.pop()
                        if parts:
                            graph[m.name].add(".".join(parts))
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    resolved = _resolve_relative_import(
                        current_module=m.name,
                        level=node.level,
                        module=node.module,
                    )
                    if resolved and resolved in known:
                        graph[m.name].add(resolved)
                    elif resolved and resolved.startswith("adversarial_debate."):
                        parts = resolved.split(".")
                        while parts and ".".join(parts) not in known:
                            parts.pop()
                        if parts:
                            graph[m.name].add(".".join(parts))
                else:
                    if not node.module:
                        continue
                    name = node.module
                    if name in known:
                        graph[m.name].add(name)
                    elif name.startswith("adversarial_debate."):
                        parts = name.split(".")
                        while parts and ".".join(parts) not in known:
                            parts.pop()
                        if parts:
                            graph[m.name].add(".".join(parts))

    return graph


def _strongly_connected_components(graph: dict[str, set[str]]) -> list[list[str]]:
    index = 0
    stack: list[str] = []
    on_stack: set[str] = set()
    indices: dict[str, int] = {}
    lowlinks: dict[str, int] = {}
    out: list[list[str]] = []

    def visit(v: str) -> None:
        nonlocal index
        indices[v] = index
        lowlinks[v] = index
        index += 1
        stack.append(v)
        on_stack.add(v)

        for w in graph.get(v, set()):
            if w not in indices:
                visit(w)
                lowlinks[v] = min(lowlinks[v], lowlinks[w])
            elif w in on_stack:
                lowlinks[v] = min(lowlinks[v], indices[w])

        if lowlinks[v] == indices[v]:
            component: list[str] = []
            while True:
                w = stack.pop()
                on_stack.remove(w)
                component.append(w)
                if w == v:
                    break
            out.append(component)

    for v in graph:
        if v not in indices:
            visit(v)

    return out


def main(argv: list[str]) -> int:
    pkg_root = _pkg_root()
    if not pkg_root.exists():
        print(f"ERROR: package root not found: {pkg_root}", file=sys.stderr)
        return 2

    modules = _iter_modules()
    graph = _build_graph(modules)

    sccs = _strongly_connected_components(graph)
    cycles: list[list[str]] = []
    for comp in sccs:
        if len(comp) > 1:
            cycles.append(sorted(comp))
            continue
        node = comp[0]
        if node in graph.get(node, set()):
            cycles.append([node])

    if not cycles:
        print(f"OK: no import cycles detected in {pkg_root.relative_to(_repo_root())}/")
        return 0

    print("ERROR: import cycles detected:", file=sys.stderr)
    for i, comp in enumerate(cycles, start=1):
        if len(comp) == 1:
            print(f"  {i}) {comp[0]} -> {comp[0]}", file=sys.stderr)
        else:
            print(f"  {i}) {' -> '.join(comp + [comp[0]])}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
