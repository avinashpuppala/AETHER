from __future__ import annotations
from dataclasses import dataclass
from collections import Counter
from typing import Sequence
import json

from aether_primitive_discovery import _parse_expr, evaluate, render, size

def _subtrees(node):
    yield node
    for child in node[1:]:
        if isinstance(child, tuple):
            yield from _subtrees(child)

def _replace(node, target, macro_name):
    if node == target:
        return ("macro", macro_name)
    if node[0] in ("x", "const"):
        return node
    if node[0] in ("neg", "abs", "square"):
        return (node[0], _replace(node[1], target, macro_name))
    return (node[0], _replace(node[1], target, macro_name),
            _replace(node[2], target, macro_name))

def _render_hierarchical(node):
    k = node[0]
    if k == "macro": return f"{node[1]}(x)"
    if k == "x": return "x"
    if k == "const": return str(node[1])
    if k == "neg": return f"(-{_render_hierarchical(node[1])})"
    if k == "abs": return f"abs({_render_hierarchical(node[1])})"
    if k == "square": return f"({_render_hierarchical(node[1])} ** 2)"
    op = {"add":"+","sub":"-","mul":"*"}[k]
    return f"({_render_hierarchical(node[1])} {op} {_render_hierarchical(node[2])})"

@dataclass(frozen=True)
class Macro:
    name: str
    tree: tuple
    discovered_in: tuple[str, ...]
    def execute(self, x):
        return evaluate(self.tree, x)

class HierarchicalPrimitiveLibrary:
    """Mines repeated expression subtrees and reuses them in larger programs."""
    def __init__(self):
        self.macros: dict[str, Macro] = {}
        self.task_expressions: dict[str, str] = {}

    def add_task(self, task_name: str, expression: str):
        if not task_name.strip():
            raise ValueError("task_name cannot be empty")
        tree = _parse_expr(expression)
        self.task_expressions[task_name] = expression
        return tree

    def mine_macros(self, min_tasks=2, min_subtree_size=2):
        occurrences = {}
        for task, expression in self.task_expressions.items():
            tree = _parse_expr(expression)
            unique = set(n for n in _subtrees(tree) if size(n) >= min_subtree_size)
            for subtree in unique:
                occurrences.setdefault(subtree, set()).add(task)
        found = []
        for i, (tree, tasks) in enumerate(
            sorted(occurrences.items(), key=lambda item: (-size(item[0]), repr(item[0]))), 1
        ):
            if len(tasks) >= min_tasks:
                name = f"macro_{i}"
                macro = Macro(name, tree, tuple(sorted(tasks)))
                self.macros[name] = macro
                found.append(macro)
        return found

    def compose(self, expression: str):
        """Rewrite a new expression to use the largest known reusable macros."""
        tree = _parse_expr(expression)
        # Prefer the largest macros; avoid rewriting inside an already replaced macro.
        for macro in sorted(self.macros.values(), key=lambda m: size(m.tree), reverse=True):
            tree = _replace(tree, macro.tree, macro.name)
        return tree

    def execute_composed(self, expression: str, x: int):
        tree = self.compose(expression)
        return self._execute(tree, x)

    def _execute(self, node, x):
        if node[0] == "macro":
            return self.macros[node[1]].execute(x)
        if node[0] in ("x", "const"):
            return evaluate(node, x)
        if node[0] in ("neg", "abs", "square"):
            value = self._execute(node[1], x)
            if node[0] == "neg": return -value
            if node[0] == "abs": return abs(value)
            return value * value
        a, b = self._execute(node[1], x), self._execute(node[2], x)
        if node[0] == "add": return a+b
        if node[0] == "sub": return a-b
        if node[0] == "mul": return a*b
        raise ValueError(f"Unsupported node: {node[0]}")

    def explain(self):
        return {
            "task_count": len(self.task_expressions),
            "macro_count": len(self.macros),
            "macros": [
                {"name":m.name, "expression":render(m.tree),
                 "discovered_in":list(m.discovered_in)}
                for m in self.macros.values()
            ]
        }

def run_hierarchical_demo():
    library = HierarchicalPrimitiveLibrary()
    library.add_task("square_plus_one", "(1 + (x ** 2))")
    library.add_task("square_plus_two", "(2 + (x ** 2))")
    macros = library.mine_macros(min_tasks=2)
    expression = "(3 + (x ** 2))"
    probes = [-5, 0, 4]
    return {
        "library": library.explain(),
        "new_expression": expression,
        "composed_structure": _render_hierarchical(library.compose(expression)),
        "probe_results": [
            {"x":x, "predicted":library.execute_composed(expression,x),
             "expected":x*x+3}
            for x in probes
        ],
        "all_probes_verified": all(
            library.execute_composed(expression,x)==x*x+3 for x in probes
        )
    }

if __name__ == "__main__":
    print(json.dumps(run_hierarchical_demo(), indent=2))
