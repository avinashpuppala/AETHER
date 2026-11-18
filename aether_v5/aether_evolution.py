"""AETHER evolutionary abstraction layer.

Adds nested macro compilation, counterexample-driven quarantine/refinement,
versioned persistent research state, and held-out benchmark helpers on top of
the bounded arithmetic DSL. No Python eval/exec is used.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence
import json
import tempfile
import time

from aether_primitive_discovery import BoundedProgramSynthesizer, Example

from aether_advanced import AdvancedPrimitiveLibrary, ParameterizedMacro, _children
from aether_primitive_discovery import _parse_expr, evaluate, size

FORMAT_VERSION = 1


def _match_symbolic(template, concrete, captures):
    """Match a macro template to a concrete or parameterized subtree.

    Template parameters bind to arbitrary subtrees. Repeated occurrences of a
    parameter must bind to structurally identical subtrees.
    """
    kind = template[0]
    if kind == "param":
        slot = template[1]
        if slot in captures and captures[slot] != concrete:
            return False
        captures[slot] = concrete
        return True
    if kind != concrete[0]:
        return False
    if kind in ("x", "const"):
        return template == concrete
    tc, cc = _children(template), _children(concrete)
    return len(tc) == len(cc) and all(
        _match_symbolic(a, b, captures) for a, b in zip(tc, cc)
    )


def _replace_with_macros(node, macros):
    """Replace maximal macro matches; captures remain ASTs for nested calls."""
    for macro in macros:
        captures = {}
        if _match_symbolic(macro.tree, node, captures):
            args = tuple(captures[i] for i in range(macro.parameter_count))
            return ("macro_call", macro.name, args)
    kind = node[0]
    if kind in ("x", "const", "param"):
        return node
    if kind in ("neg", "abs", "square"):
        return (kind, _replace_with_macros(node[1], macros))
    return (kind, _replace_with_macros(node[1], macros),
            _replace_with_macros(node[2], macros))


def _macro_calls(node):
    if not isinstance(node, tuple):
        return
    if node and node[0] == "macro_call":
        yield node[1]
        for arg in node[2]:
            yield from _macro_calls(arg)
        return
    for child in _children(node):
        yield from _macro_calls(child)


def _eval_tree(node, x, params, compiled, depth=0):
    if depth > 100:
        raise RecursionError("Macro expansion exceeded the safety depth.")
    kind = node[0]
    if kind == "x": return x
    if kind == "const": return node[1]
    if kind == "param": return params[node[1]]
    if kind == "macro_call":
        name, arg_nodes = node[1], node[2]
        arg_values = tuple(_eval_tree(a, x, params, compiled, depth + 1)
                           if isinstance(a, tuple) else a for a in arg_nodes)
        return _eval_tree(compiled[name], x, arg_values, compiled, depth + 1)
    if kind == "neg": return -_eval_tree(node[1], x, params, compiled, depth + 1)
    if kind == "abs": return abs(_eval_tree(node[1], x, params, compiled, depth + 1))
    if kind == "square":
        v = _eval_tree(node[1], x, params, compiled, depth + 1)
        return v * v
    a = _eval_tree(node[1], x, params, compiled, depth + 1)
    b = _eval_tree(node[2], x, params, compiled, depth + 1)
    if kind == "add": return a + b
    if kind == "sub": return a - b
    if kind == "mul": return a * b
    raise ValueError(f"Unsupported evolved node: {kind}")


class AetherEvolutionEngine:
    """Evolves a verified macro library into nested, persistent abstractions."""

    def __init__(self, library: AdvancedPrimitiveLibrary | None = None):
        self.library = library or AdvancedPrimitiveLibrary()
        self.compiled_trees: dict[str, tuple] = {}
        self.macro_dependencies: dict[str, list[str]] = {}
        self.quarantined_macros: set[str] = set()
        self.history: list[dict] = []
        self.refinement_log: list[dict] = []

    def add_task(self, task_name: str, expression: str):
        self.library.add_task(task_name, expression)

    def discover(self, **kwargs):
        macros = self.library.discover(**kwargs)
        self.compile_hierarchy()
        self.history.append({"event": "discover", "task_count": len(self.library.task_expressions),
                             "macro_count": len(macros)})
        return macros

    def compile_hierarchy(self):
        """Compile smaller verified macros into larger macro definitions.

        This creates real nested calls. A parent macro can call a child macro
        with arguments that are expressions over the parent's parameters.
        """
        self.compiled_trees = {}
        self.macro_dependencies = {}
        ordered = sorted(self.library.macros.values(), key=lambda m: (size(m.tree), m.name))
        for parent in ordered:
            smaller = [m for m in ordered
                       if size(m.tree) < size(parent.tree)
                       and m.name not in self.quarantined_macros]
            smaller.sort(key=lambda m: (-size(m.tree), m.name))
            compiled = _replace_with_macros(parent.tree, smaller)
            deps = sorted(set(_macro_calls(compiled)))
            self.compiled_trees[parent.name] = compiled
            self.macro_dependencies[parent.name] = deps
        return {k: list(v) for k, v in self.macro_dependencies.items()}

    def compose(self, expression: str):
        if not self.compiled_trees:
            self.compile_hierarchy()
        active = [m for m in self.library.macros.values()
                  if m.name not in self.quarantined_macros]
        active.sort(key=lambda m: (-size(m.tree), m.name))
        return _replace_with_macros(_parse_expr(expression), active)

    def execute_composed(self, expression: str, x: int):
        tree = self.compose(expression)
        return _eval_tree(tree, x, (), self.compiled_trees)

    def verify_composition(self, expression: str, probes: Iterable[int], candidate_tree=None):
        source = _parse_expr(expression)
        composed = candidate_tree if candidate_tree is not None else self.compose(expression)
        results = []
        for x in probes:
            expected = evaluate(source, x)
            predicted = _eval_tree(composed, x, (), self.compiled_trees)
            passed = expected == predicted
            results.append({"x": x, "expected": expected, "predicted": predicted,
                            "passed": passed})
            if not passed:
                self.library.counterexamples.append({
                    "expression": expression, **results[-1],
                    "macro_names": sorted(set(_macro_calls(composed)))
                })
        return {"verified": bool(results) and all(r["passed"] for r in results),
                "results": results,
                "counterexample_count": sum(not r["passed"] for r in results),
                "macro_calls": sorted(set(_macro_calls(composed)))}

    def refine_from_counterexamples(self, counterexamples: Sequence[dict] | None = None):
        """Quarantine abstractions implicated in observed failures.

        Quarantined macros remain in the knowledge store for auditability but
        are excluded from future composition. This is a conservative first
        refinement policy; it avoids silently deleting learned knowledge.
        """
        records = list(counterexamples if counterexamples is not None
                       else self.library.counterexamples)
        implicated = set()
        for record in records:
            implicated.update(record.get("macro_names", []))
        newly_quarantined = sorted(implicated - self.quarantined_macros)
        self.quarantined_macros.update(newly_quarantined)
        self.compile_hierarchy()
        entry = {"event": "counterexample_refinement",
                 "observed_counterexamples": len(records),
                 "quarantined": newly_quarantined}
        self.refinement_log.append(entry)
        self.history.append(entry)
        return {"quarantined": newly_quarantined,
                "active_macro_count": len(self.library.macros) - len(self.quarantined_macros),
                "retained_knowledge_count": len(self.library.macros)}

    def repair_from_counterexamples(self, counterexamples: Sequence[dict] | None = None,
                                    probes: Sequence[int] = (-7, -2, 0, 3, 8),
                                    max_candidate_combinations: int = 50000):
        """Rebuild and validate a fresh abstraction library after failures.

        This is a conservative, bounded repair loop: it regenerates macros only
        from the original source tasks, evaluates each candidate library against
        recorded counterexamples and source-task probes, and swaps state only
        when every check passes. It does not learn arbitrary new operators.
        """
        records = list(counterexamples if counterexamples is not None
                       else self.library.counterexamples)
        if not self.library.task_expressions:
            return {"repaired": False, "reason": "no_source_tasks",
                    "candidate_libraries_tested": 0}
        if not records:
            return {"repaired": False, "reason": "no_counterexamples",
                    "candidate_libraries_tested": 0}

        # Try a small, explicit set of bounded discovery configurations.
        configurations = (2, 3, 4)
        candidates = []
        for min_size in configurations:
            fresh_library = AdvancedPrimitiveLibrary()
            for task_name, expression in self.library.task_expressions.items():
                fresh_library.add_task(task_name, expression)
            candidate = AetherEvolutionEngine(fresh_library)
            candidate.discover(min_subtree_size=min_size,
                               max_candidate_combinations=max_candidate_combinations)

            checks = []
            for record in records:
                expression = record.get("expression")
                x = record.get("x")
                if expression is None or x is None:
                    continue
                try:
                    expected = evaluate(_parse_expr(expression), x)
                    predicted = candidate.execute_composed(expression, x)
                    checks.append(expected == predicted)
                except (ValueError, KeyError, RecursionError, IndexError):
                    checks.append(False)

            # Guard against a repair that fixes only the observed failure while
            # damaging the original training tasks.
            for expression in self.library.task_expressions.values():
                for x in probes:
                    try:
                        expected = evaluate(_parse_expr(expression), x)
                        predicted = candidate.execute_composed(expression, x)
                        checks.append(expected == predicted)
                    except (ValueError, KeyError, RecursionError, IndexError):
                        checks.append(False)

            all_passed = bool(checks) and all(checks)
            candidates.append({"min_subtree_size": min_size,
                               "verified": all_passed,
                               "passed_checks": sum(checks),
                               "total_checks": len(checks),
                               "candidate": candidate})

        valid = [item for item in candidates if item["verified"]]
        if not valid:
            result = {"repaired": False, "reason": "no_candidate_passed_all_checks",
                      "candidate_libraries_tested": len(candidates),
                      "candidate_results": [{k: v for k, v in item.items() if k != "candidate"}
                                             for item in candidates]}
            self.history.append({"event": "automatic_repair_rejected",
                                 **{k: v for k, v in result.items() if k != "candidate_results"}})
            return result

        # Prefer the candidate with the strongest verification count, then the
        # least restrictive discovery setting for deterministic tie-breaking.
        chosen = max(valid, key=lambda item: (item["passed_checks"], -item["min_subtree_size"]))
        repaired = chosen["candidate"]
        self.library = repaired.library
        self.quarantined_macros.clear()
        self.compiled_trees = repaired.compiled_trees
        self.macro_dependencies = repaired.macro_dependencies
        self.history.append({"event": "automatic_repair_accepted",
                             "min_subtree_size": chosen["min_subtree_size"],
                             "passed_checks": chosen["passed_checks"],
                             "total_checks": chosen["total_checks"],
                             "macro_count": len(self.library.macros)})
        return {"repaired": True,
                "selected_min_subtree_size": chosen["min_subtree_size"],
                "passed_checks": chosen["passed_checks"],
                "total_checks": chosen["total_checks"],
                "macro_count": len(self.library.macros),
                "candidate_libraries_tested": len(candidates),
                "candidate_results": [{k: v for k, v in item.items() if k != "candidate"}
                                       for item in candidates]}

    def benchmark_transfer(self, families: dict[str, dict], probes: Sequence[int] = (-5, -2, 0, 3, 7),
                           include_symbolic_baseline: bool = False,
                           baseline_candidate_limit: int = 100000):
        """Evaluate parameter transfer on held-out constants across DSL families.

        Each family maps to source task expressions and one held-out target.
        The target is never added to the discovery library.
        """
        rows = []
        for family, spec in families.items():
            local = AetherEvolutionEngine()
            for name, expr in spec["source_tasks"].items():
                local.add_task(name, expr)
            local.discover()
            target = spec["target"]
            check = local.verify_composition(target, probes)
            row = {"family": family, "source_task_count": len(spec["source_tasks"]),
                   "target_held_out": True, "verified": check["verified"],
                   "passed": sum(r["passed"] for r in check["results"]),
                   "total": len(check["results"]),
                   "macro_count": len(local.library.macros),
                   "search_stats": dict(local.library.search_stats)}
            if include_symbolic_baseline:
                target_tree = _parse_expr(target)
                support_x = tuple(probes[:min(3, len(probes))])
                support = [Example(x, evaluate(target_tree, x)) for x in support_x]
                baseline = BoundedProgramSynthesizer(
                    max_depth=2, constants=tuple(range(-10, 11)),
                    max_candidates=baseline_candidate_limit)
                started = time.perf_counter()
                candidates = baseline.solve(support)
                elapsed = time.perf_counter() - started
                best = candidates[0] if candidates else None
                heldout_x = tuple(probes[len(support_x):]) or tuple(probes)
                baseline_checks = []
                if best:
                    candidate_tree = _parse_expr(best.expression)
                    baseline_checks = [evaluate(candidate_tree, x) == evaluate(target_tree, x)
                                       for x in heldout_x]
                row["symbolic_baseline"] = {
                    "support_examples": len(support),
                    "candidate_budget": baseline_candidate_limit,
                    "candidate_found": best is not None,
                    "best_expression": best.expression if best else None,
                    "held_out_passed": sum(baseline_checks),
                    "held_out_total": len(baseline_checks),
                    "held_out_verified": bool(baseline_checks) and all(baseline_checks),
                    "elapsed_seconds": round(elapsed, 4)}
            rows.append(row)
        report = {"families_tested": len(rows),
                  "verified_families": sum(r["verified"] for r in rows),
                  "probe_accuracy": (sum(r["passed"] for r in rows) /
                                     max(1, sum(r["total"] for r in rows))),
                  "results": rows}
        if include_symbolic_baseline:
            baseline_rows = [r["symbolic_baseline"] for r in rows]
            report["symbolic_baseline_summary"] = {
                "verified_families": sum(r["held_out_verified"] for r in baseline_rows),
                "families_tested": len(baseline_rows),
                "total_held_out_passed": sum(r["held_out_passed"] for r in baseline_rows),
                "total_held_out": sum(r["held_out_total"] for r in baseline_rows),
                "total_elapsed_seconds": round(sum(r["elapsed_seconds"] for r in baseline_rows), 4)}
        return report

    def explain(self):
        return {"task_count": len(self.library.task_expressions),
                "macro_count": len(self.library.macros),
                "nested_dependency_graph": self.macro_dependencies,
                "quarantined_macros": sorted(self.quarantined_macros),
                "counterexample_count": len(self.library.counterexamples),
                "history_events": len(self.history)}

    def save(self, path: str | Path):
        with tempfile.TemporaryDirectory() as tmp:
            library_path = Path(tmp) / "library.json"
            self.library.save(library_path)
            payload = {"format_version": FORMAT_VERSION,
                       "library": json.loads(library_path.read_text(encoding="utf-8")),
                       "quarantined_macros": sorted(self.quarantined_macros),
                       "history": self.history,
                       "refinement_log": self.refinement_log}
        Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path):
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if payload.get("format_version") != FORMAT_VERSION:
            raise ValueError("Unsupported AETHER evolution state format.")
        with tempfile.TemporaryDirectory() as tmp:
            library_path = Path(tmp) / "library.json"
            library_path.write_text(json.dumps(payload["library"]), encoding="utf-8")
            library = AdvancedPrimitiveLibrary.load(library_path)
        engine = cls(library)
        engine.quarantined_macros = set(payload.get("quarantined_macros", []))
        engine.history = list(payload.get("history", []))
        engine.refinement_log = list(payload.get("refinement_log", []))
        engine.compile_hierarchy()
        return engine


def run_evolution_demo():
    engine = AetherEvolutionEngine()
    engine.add_task("square_plus_one", "(1 + (x ** 2))")
    engine.add_task("square_plus_two", "(2 + (x ** 2))")
    engine.add_task("square_plus_five", "(5 + (x ** 2))")
    engine.discover()
    target = "(9 + (x ** 2))"
    verification = engine.verify_composition(target, [-9, -2, 0, 3, 11])
    return {"engine": engine.explain(), "target": target,
            "nested_composition": str(engine.compose(target)),
            "predictions": [engine.execute_composed(target, x) for x in [-9, -2, 0, 3, 11]],
            "verification": verification}


if __name__ == "__main__":
    print(json.dumps(run_evolution_demo(), indent=2))
