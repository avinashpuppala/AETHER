"""AETHER discovery core: bounded program invention with active experiments.

This module searches a small, explicit integer-expression grammar. It is a
research baseline, not a general intelligence system. It deliberately avoids
eval/exec and reports finite-search boundaries.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Iterable, Sequence

ERROR = ("__ERROR__",)


def _canonical(node):
    kind = node[0]
    if kind in ("x", "const"):
        return node
    if kind in ("neg", "abs", "square"):
        return (kind, _canonical(node[1]))
    left, right = _canonical(node[1]), _canonical(node[2])
    if kind in ("add", "mul") and repr(left) > repr(right):
        left, right = right, left
    return (kind, left, right)


def _node_count(node):
    kind = node[0]
    if kind in ("x", "const"):
        return 1
    if kind in ("neg", "abs", "square"):
        return 1 + _node_count(node[1])
    return 1 + _node_count(node[1]) + _node_count(node[2])


def render(node):
    kind = node[0]
    if kind == "x":
        return "x"
    if kind == "const":
        return str(node[1])
    if kind == "neg":
        return f"(-{render(node[1])})"
    if kind == "abs":
        return f"abs({render(node[1])})"
    if kind == "square":
        return f"({render(node[1])} ** 2)"
    symbols = {"add": "+", "sub": "-", "mul": "*"}
    return f"({render(node[1])} {symbols[kind]} {render(node[2])})"


def evaluate(node, x: int, max_abs: int = 10**12) -> int:
    """Evaluate a discovered AST with explicit operators and magnitude guard."""
    kind = node[0]
    if kind == "x":
        value = int(x)
    elif kind == "const":
        value = int(node[1])
    elif kind == "neg":
        value = -evaluate(node[1], x, max_abs)
    elif kind == "abs":
        value = abs(evaluate(node[1], x, max_abs))
    elif kind == "square":
        child = evaluate(node[1], x, max_abs)
        value = child * child
    elif kind in ("add", "sub", "mul"):
        left = evaluate(node[1], x, max_abs)
        right = evaluate(node[2], x, max_abs)
        if kind == "add":
            value = left + right
        elif kind == "sub":
            value = left - right
        else:
            value = left * right
    else:
        raise ValueError(f"Unsupported expression node: {kind}")
    if abs(value) > max_abs:
        raise OverflowError("Expression exceeded configured magnitude limit")
    return value


def enumerate_programs(
    max_nodes: int = 5,
    constants: Sequence[int] = (-2, -1, 0, 1, 2, 3),
    max_candidates: int = 25_000,
):
    """Enumerate canonical ASTs up to max_nodes; returns (programs, complete)."""
    if max_nodes < 1 or max_candidates < 1:
        raise ValueError("max_nodes and max_candidates must be positive")
    constants = tuple(sorted(set(int(c) for c in constants)))

    @lru_cache(maxsize=None)
    def exact_size(n: int):
        found = set()
        if n == 1:
            found.add(("x",))
            found.update(("const", c) for c in constants)
        else:
            for op in ("neg", "abs", "square"):
                for child in exact_size(n - 1):
                    found.add(_canonical((op, child)))
            for left_size in range(1, n - 1):
                right_size = n - 1 - left_size
                for left in exact_size(left_size):
                    for right in exact_size(right_size):
                        for op in ("add", "sub", "mul"):
                            found.add(_canonical((op, left, right)))
        return tuple(sorted(found, key=repr))

    programs = []
    seen = set()
    complete = True
    for n in range(1, max_nodes + 1):
        for node in exact_size(n):
            key = repr(node)
            if key in seen:
                continue
            seen.add(key)
            if len(programs) >= max_candidates:
                complete = False
                return programs, complete
            programs.append(node)
    return programs, complete


class AetherDiscoveryCore:
    """Synthesize candidate programs from examples using active oracle queries.

    The target oracle is external: this class receives only selected (x, y)
    observations. Search is complete only within the configured grammar,
    constants, node limit and candidate budget.
    """

    def __init__(
        self,
        max_nodes: int = 5,
        constants: Sequence[int] = (-2, -1, 0, 1, 2, 3),
        max_candidates: int = 25_000,
        query_min: int = -8,
        query_max: int = 8,
        max_queries: int = 8,
    ):
        if query_min > query_max:
            raise ValueError("query_min must be <= query_max")
        if max_queries < 1:
            raise ValueError("max_queries must be positive")
        self.programs, self.search_complete = enumerate_programs(
            max_nodes=max_nodes, constants=constants,
            max_candidates=max_candidates,
        )
        self.query_min = query_min
        self.query_max = query_max
        self.max_queries = max_queries
        self.observations: list[tuple[int, int]] = []
        self._seen_inputs: set[int] = set()
        self.status = "collecting"
        self._survivors = list(self.programs)
        self.query_log = []

    @staticmethod
    def _safe_predict(program, x):
        try:
            return evaluate(program, x)
        except (ArithmeticError, IndexError, TypeError, ValueError):
            return ERROR

    def next_query(self):
        if self.status != "collecting":
            return None
        if len(self.observations) >= self.max_queries:
            self.status = "query_budget_exhausted"
            return None
        if not self._survivors:
            self.status = "no_consistent_program"
            return None
        if len(self._survivors) == 1:
            self.status = "identified"
            return None

        choices = []
        for x in range(self.query_min, self.query_max + 1):
            if x in self._seen_inputs:
                continue
            buckets = {}
            for program in self._survivors:
                y = self._safe_predict(program, x)
                buckets[y] = buckets.get(y, 0) + 1
            if len(buckets) <= 1:
                continue
            total = sum(buckets.values())
            expected_remaining = sum(count * count for count in buckets.values()) / total
            choices.append((expected_remaining, abs(x), x))

        if not choices:
            self.status = "behaviorally_identified"
            return None
        return min(choices)[2]

    def observe(self, x: int, y: int):
        x, y = int(x), int(y)
        if self.status != "collecting":
            raise RuntimeError(f"Cannot observe while status is {self.status}")
        if not self.query_min <= x <= self.query_max:
            raise ValueError("Support input is outside the configured query range")
        if x in self._seen_inputs:
            raise ValueError("Support inputs must be unique")
        if len(self.observations) >= self.max_queries:
            self.status = "query_budget_exhausted"
            raise RuntimeError("Query budget exhausted")

        before = len(self._survivors)
        self._seen_inputs.add(x)
        self.observations.append((x, y))
        self._survivors = [
            p for p in self._survivors if self._safe_predict(p, x) == y
        ]
        record = {
            "input": x,
            "observed_output": y,
            "hypotheses_before": before,
            "hypotheses_after": len(self._survivors),
        }
        self.query_log.append(record)
        if not self._survivors:
            self.status = "no_consistent_program"
        elif len(self._survivors) == 1:
            self.status = "identified"
        elif len(self.observations) >= self.max_queries:
            self.status = "query_budget_exhausted"
        return {**record, "status": self.status}

    def verify(self, test_examples: Iterable[tuple[int, int]]):
        tests = tuple((int(x), int(y)) for x, y in test_examples)
        if not tests:
            raise ValueError("At least one independent test example is required")
        test_inputs = [x for x, _ in tests]
        if len(set(test_inputs)) != len(test_inputs):
            raise ValueError("Test inputs must be unique")
        overlap = self._seen_inputs.intersection(test_inputs)
        if overlap:
            raise ValueError(f"Test inputs overlap support inputs: {sorted(overlap)}")
        if self.status not in ("identified", "behaviorally_identified", "query_budget_exhausted"):
            return {
                "status": self.status, "verified": False,
                "reason": "no_valid_hypothesis_set",
                "survivor_count": len(self._survivors),
            }

        passing = []
        for program in self._survivors:
            try:
                if all(evaluate(program, x) == expected for x, expected in tests):
                    passing.append(program)
            except (ArithmeticError, IndexError, TypeError, ValueError):
                continue
        self._survivors = passing
        if not passing:
            self.status = "test_failure"
        elif len(passing) == 1:
            self.status = "verified_unique_program"
        else:
            self.status = "verified_equivalence_set"
        return {
            "status": self.status,
            "verified": bool(passing),
            "survivor_count": len(passing),
            "representative_program": render(passing[0]) if passing else None,
            "equivalent_programs": [render(p) for p in passing[:20]],
            "support_query_count": len(self.observations),
            "independent_test_count": len(tests),
            "passed": len(tests) if passing else 0,
            "total": len(tests),
            "search_complete": self.search_complete,
            "research_boundary": (
                "Verification applies only to the finite tests and configured "
                "grammar/search bounds; it is not a proof of general correctness."
            ),
        }

    def report(self):
        return {
            "status": self.status,
            "grammar": {
                "operators": ["add", "sub", "mul", "neg", "abs", "square"],
                "constants": sorted({p[1] for p in self.programs if p[0] == "const"}),
                "max_nodes": max((_node_count(p) for p in self.programs), default=0),
            },
            "programs_initial": len(self.programs),
            "programs_remaining": len(self._survivors),
            "search_complete": self.search_complete,
            "support_observations": [
                {"x": x, "y": y} for x, y in self.observations
            ],
            "query_log": list(self.query_log),
            "query_budget": self.max_queries,
        }
