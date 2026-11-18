"""AETHER advanced hierarchical discovery: parameterized macros, verification and persistence.

This remains a bounded symbolic research prototype. It uses the arithmetic DSL
from aether_primitive_discovery and never evaluates generated Python source.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from pathlib import Path
from typing import Iterable, Sequence
import json

from aether_primitive_discovery import _parse_expr, evaluate, render, size


def _children(node):
    return [child for child in node[1:] if isinstance(child, tuple)]


def _walk(node):
    yield node
    for child in _children(node):
        yield from _walk(child)


def _skeleton(node):
    """Tree shape with every integer literal represented by the same marker."""
    kind = node[0]
    if kind == "const":
        return ("const",)
    if kind == "x":
        return ("x",)
    return (kind, *(_skeleton(child) for child in _children(node)))


def _parameterize_group(nodes):
    """Anti-unify same-shaped trees; equal value-vectors share one parameter."""
    if len(nodes) < 2 or any(_skeleton(n) != _skeleton(nodes[0]) for n in nodes[1:]):
        raise ValueError("Trees must have identical operator structure.")
    vectors_to_slot = {}
    source_values = [dict() for _ in nodes]

    def walk(parts, path=()):
        first = parts[0]
        kind = first[0]
        if kind == "const":
            vector = tuple(n[1] for n in parts)
            if len(set(vector)) == 1:
                return ("const", vector[0])
            if vector not in vectors_to_slot:
                vectors_to_slot[vector] = len(vectors_to_slot)
            slot = vectors_to_slot[vector]
            for source_index, value in enumerate(vector):
                source_values[source_index][slot] = value
            return ("param", slot)
        if kind == "x":
            return ("x",)
        child_count = len(_children(first))
        rebuilt = [walk([_children(n)[i] for n in parts], path + (i,))
                   for i in range(child_count)]
        return (kind, *rebuilt)

    template = walk(list(nodes))
    if not vectors_to_slot:
        return template, tuple(() for _ in nodes)
    params = tuple(tuple(values[i] for i in range(len(vectors_to_slot)))
                   for values in source_values)
    return template, params


def _render_template(node):
    kind = node[0]
    if kind == "x": return "x"
    if kind == "const": return str(node[1])
    if kind == "param": return f"$p{node[1] + 1}"
    if kind == "neg": return f"(-{_render_template(node[1])})"
    if kind == "abs": return f"abs({_render_template(node[1])})"
    if kind == "square": return f"({_render_template(node[1])} ** 2)"
    op = {"add": "+", "sub": "-", "mul": "*"}[kind]
    return f"({_render_template(node[1])} {op} {_render_template(node[2])})"


def _match_template(template, concrete, captures):
    """Match a generalized macro against a concrete DSL subtree."""
    kind = template[0]
    if kind == "param":
        if concrete[0] != "const":
            return False
        slot, value = template[1], concrete[1]
        if slot in captures and captures[slot] != value:
            return False
        captures[slot] = value
        return True
    if kind != concrete[0]:
        return False
    if kind in ("x", "const"):
        return template == concrete
    tc, cc = _children(template), _children(concrete)
    return len(tc) == len(cc) and all(
        _match_template(a, b, captures) for a, b in zip(tc, cc)
    )


def _replace_at_matches(node, macros):
    """Replace the largest matching macro at each node, then recurse otherwise."""
    for macro in macros:
        captures = {}
        if _match_template(macro.tree, node, captures):
            values = tuple(captures[i] for i in range(macro.parameter_count))
            return ("macro_call", macro.name, values)
    kind = node[0]
    if kind in ("x", "const"):
        return node
    if kind in ("neg", "abs", "square"):
        return (kind, _replace_at_matches(node[1], macros))
    return (kind, _replace_at_matches(node[1], macros),
            _replace_at_matches(node[2], macros))


@dataclass(frozen=True)
class ParameterizedMacro:
    name: str
    tree: tuple
    discovered_in: tuple[str, ...]
    source_parameter_values: tuple[tuple[int, ...], ...]

    @property
    def parameter_count(self):
        def count(n):
            if n[0] == "param": return n[1] + 1
            return max((count(c) for c in _children(n)), default=0)
        return count(self.tree)

    @property
    def template(self):
        return _render_template(self.tree)

    def execute(self, x: int, parameters: Sequence[int] = ()) -> int:
        params = tuple(parameters)
        if len(params) != self.parameter_count:
            raise ValueError(f"{self.name} expects {self.parameter_count} parameters.")
        return _eval(self.tree, x, params, {})

    def to_dict(self):
        return {"name": self.name, "template": self.template,
                "parameter_count": self.parameter_count,
                "discovered_in": list(self.discovered_in),
                "source_parameter_values": [list(v) for v in self.source_parameter_values]}


def _eval(node, x, params, macros):
    kind = node[0]
    if kind == "x": return x
    if kind == "const": return node[1]
    if kind == "param": return params[node[1]]
    if kind == "macro_call":
        macro = macros[node[1]]
        return _eval(macro.tree, x, node[2], macros)
    if kind == "neg": return -_eval(node[1], x, params, macros)
    if kind == "abs": return abs(_eval(node[1], x, params, macros))
    if kind == "square":
        value = _eval(node[1], x, params, macros)
        return value * value
    a = _eval(node[1], x, params, macros)
    b = _eval(node[2], x, params, macros)
    if kind == "add": return a + b
    if kind == "sub": return a - b
    if kind == "mul": return a * b
    raise ValueError(f"Unsupported node: {kind}")


class AdvancedPrimitiveLibrary:
    """Bounded discovery and safe execution of reusable parameterized subtrees."""
    FORMAT_VERSION = 1

    def __init__(self):
        self.task_expressions: dict[str, str] = {}
        self.macros: dict[str, ParameterizedMacro] = {}
        self.search_stats = {"candidate_combinations": 0, "unique_templates": 0}
        self.counterexamples: list[dict] = []

    def add_task(self, task_name: str, expression: str):
        if not task_name or not task_name.strip():
            raise ValueError("task_name cannot be empty")
        _parse_expr(expression)  # validate before mutating state
        self.task_expressions[task_name] = expression

    def discover(self, min_tasks: int = 2, min_subtree_size: int = 2,
                 max_candidate_combinations: int = 50000):
        if min_tasks < 2:
            raise ValueError("min_tasks must be at least 2")
        if max_candidate_combinations < 1:
            raise ValueError("search budget must be positive")
        by_shape: dict[tuple, dict[str, list[tuple]]] = {}
        for task, expression in self.task_expressions.items():
            tree = _parse_expr(expression)
            for subtree in set(n for n in _walk(tree) if size(n) >= min_subtree_size):
                by_shape.setdefault(_skeleton(subtree), {}).setdefault(task, []).append(subtree)

        candidates = {}
        examined = 0
        for _, task_map in sorted(by_shape.items(), key=lambda item: repr(item[0])):
            task_names = sorted(task_map)
            if len(task_names) < min_tasks:
                continue
            # Enumerate bounded cross-task combinations. One subtree per task.
            for selected_tasks in _task_combinations(task_names, min_tasks):
                pools = [task_map[t] for t in selected_tasks]
                for trees in product(*pools):
                    examined += 1
                    if examined > max_candidate_combinations:
                        break
                    try:
                        template, source_params = _parameterize_group(trees)
                    except ValueError:
                        continue
                    key = repr(template)
                    if key not in candidates:
                        candidates[key] = {"tree": template, "tasks": set(), "params": []}
                    candidates[key]["tasks"].update(selected_tasks)
                    candidates[key]["params"].extend(source_params)
                if examined > max_candidate_combinations:
                    break
            if examined > max_candidate_combinations:
                break

        # Prefer larger abstractions, then more independent source tasks.
        ordered = sorted(candidates.values(),
                         key=lambda c: (-size(c["tree"]), -len(c["tasks"]), repr(c["tree"])))
        discovered = {}
        for index, item in enumerate(ordered, 1):
            name = f"macro_{index:03d}"
            unique_params = tuple(dict.fromkeys(item["params"]))
            discovered[name] = ParameterizedMacro(
                name, item["tree"], tuple(sorted(item["tasks"])), unique_params
            )
        self.macros = discovered
        self.search_stats = {"candidate_combinations": min(examined, max_candidate_combinations),
                              "unique_templates": len(candidates),
                              "budget_exhausted": examined > max_candidate_combinations}
        return list(self.macros.values())

    def compose(self, expression: str):
        tree = _parse_expr(expression)
        macros = sorted(self.macros.values(), key=lambda m: size(m.tree), reverse=True)
        return _replace_at_matches(tree, macros)

    def execute_composed(self, expression: str, x: int) -> int:
        return _eval(self.compose(expression), x, (), self.macros)

    def verify_composition(self, expression: str, probes: Iterable[int]):
        tree = _parse_expr(expression)
        composed = self.compose(expression)
        results = []
        for x in probes:
            expected = evaluate(tree, x)
            predicted = _eval(composed, x, (), self.macros)
            results.append({"x": x, "expected": expected, "predicted": predicted,
                            "passed": expected == predicted})
            if expected != predicted:
                self.counterexamples.append({"expression": expression, **results[-1]})
        return {"verified": bool(results) and all(r["passed"] for r in results),
                "results": results, "counterexample_count": sum(not r["passed"] for r in results)}

    def explain(self):
        return {"task_count": len(self.task_expressions),
                "macro_count": len(self.macros),
                "macros": [m.to_dict() for m in self.macros.values()],
                "search_stats": dict(self.search_stats),
                "counterexample_count": len(self.counterexamples)}

    def save(self, path: str | Path):
        payload = {"format_version": self.FORMAT_VERSION,
                   "task_expressions": self.task_expressions,
                   "macros": [{"name": m.name, "tree": _tree_to_json(m.tree),
                               "discovered_in": list(m.discovered_in),
                               "source_parameter_values": [list(v) for v in m.source_parameter_values]}
                              for m in self.macros.values()],
                   "search_stats": self.search_stats,
                   "counterexamples": self.counterexamples}
        Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path):
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if payload.get("format_version") != cls.FORMAT_VERSION:
            raise ValueError("Unsupported AETHER library format version.")
        library = cls()
        library.task_expressions = dict(payload["task_expressions"])
        library.macros = {
            item["name"]: ParameterizedMacro(
                item["name"], _tree_from_json(item["tree"]),
                tuple(item["discovered_in"]),
                tuple(tuple(v) for v in item["source_parameter_values"])
            ) for item in payload["macros"]
        }
        library.search_stats = dict(payload.get("search_stats", {}))
        library.counterexamples = list(payload.get("counterexamples", []))
        return library


def _task_combinations(task_names, minimum):
    """Yield all sizes from minimum through all tasks, preferring small groups."""
    from itertools import combinations
    for count in range(minimum, len(task_names) + 1):
        yield from combinations(task_names, count)


def _tree_to_json(node):
    return [node[0], *(_tree_to_json(v) if isinstance(v, tuple) else v for v in node[1:])]


def _tree_from_json(value):
    return tuple(_tree_from_json(v) if isinstance(v, list) else v for v in value)


def run_advanced_demo():
    library = AdvancedPrimitiveLibrary()
    library.add_task("square_plus_one", "(1 + (x ** 2))")
    library.add_task("square_plus_two", "(2 + (x ** 2))")
    library.add_task("square_plus_five", "(5 + (x ** 2))")
    macros = library.discover()
    target = "(9 + (x ** 2))"
    verification = library.verify_composition(target, [-9, -2, 0, 3, 11])
    return {"library": library.explain(), "target_expression": target,
            "composed_execution": [library.execute_composed(target, x) for x in [-9, -2, 0, 3, 11]],
            "verification": verification}


if __name__ == "__main__":
    print(json.dumps(run_advanced_demo(), indent=2))
