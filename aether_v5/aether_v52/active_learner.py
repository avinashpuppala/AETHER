"""Active query selection for example-only transfer in a bounded arithmetic DSL.

The learner receives a frozen parameterized AST, chooses informative input
queries, and accepts observed outputs from an external task/oracle. It never
reads the target expression or target AST.
"""
from __future__ import annotations

from itertools import product
from typing import Iterable, Sequence

from aether_v51.validator import evaluate_template


class ActiveTransferLearner:
    """Identify a frozen template's integer parameters using adaptive examples.

    At each step, choose the input x that minimizes the expected number of
    remaining parameter hypotheses after observing the output. Ties are
    deterministic: prefer smaller absolute x, then smaller x.
    """

    def __init__(
        self,
        candidate: dict,
        parameter_min: int = -32,
        parameter_max: int = 32,
        input_min: int = -16,
        input_max: int = 16,
        max_queries: int = 20,
    ):
        if parameter_min > parameter_max:
            raise ValueError("parameter_min must be <= parameter_max")
        if input_min > input_max:
            raise ValueError("input_min must be <= input_max")
        if max_queries < 1:
            raise ValueError("max_queries must be positive")
        self.tree = candidate["tree"]
        self.candidate_name = candidate.get("name", "unnamed")
        self.parameter_count = int(candidate["parameter_count"])
        if self.parameter_count < 1:
            raise ValueError("Candidate must contain at least one parameter")
        self.parameter_min = parameter_min
        self.parameter_max = parameter_max
        self.input_min = input_min
        self.input_max = input_max
        self.max_queries = max_queries
        values = range(parameter_min, parameter_max + 1)
        self.hypotheses = list(product(values, repeat=self.parameter_count))
        self.observations: list[tuple[int, int]] = []
        self._seen_inputs: set[int] = set()
        self.status = "collecting"

    def _predict(self, x: int, params: Sequence[int]) -> int:
        return evaluate_template(self.tree, x, params)

    def next_query(self) -> int | None:
        """Return the most discriminative unqueried x, or None when stopped."""
        if self.status != "collecting" or len(self.observations) >= self.max_queries:
            return None
        if len(self.hypotheses) <= 1:
            self.status = "identified"
            return None

        choices = []
        for x in range(self.input_min, self.input_max + 1):
            if x in self._seen_inputs:
                continue
            buckets: dict[int, int] = {}
            for params in self.hypotheses:
                try:
                    y = self._predict(x, params)
                except (ArithmeticError, IndexError, TypeError, ValueError):
                    continue
                buckets[y] = buckets.get(y, 0) + 1
            if not buckets:
                continue
            # Expected surviving hypotheses after a uniformly selected
            # remaining hypothesis emits its deterministic output.
            expected_remaining = sum(n * n for n in buckets.values()) / sum(buckets.values())
            choices.append((expected_remaining, abs(x), x))
        if not choices:
            self.status = "no_informative_query"
            return None
        return min(choices)[2]

    def observe(self, x: int, y: int) -> dict:
        """Incorporate one oracle observation and eliminate inconsistent models."""
        x, y = int(x), int(y)
        if not self.input_min <= x <= self.input_max:
            raise ValueError("Observed input is outside the configured query range")
        if x in self._seen_inputs:
            raise ValueError("Each support input must be queried only once")
        if self.status != "collecting":
            raise RuntimeError(f"Cannot observe while learner status is {self.status}.")
        if len(self.observations) >= self.max_queries:
            self.status = "query_budget_exhausted"
            raise RuntimeError("Query budget exhausted")
        self._seen_inputs.add(x)
        self.observations.append((x, y))
        self.hypotheses = [
            params for params in self.hypotheses
            if self._safe_predict(x, params) == y
        ]
        if not self.hypotheses:
            self.status = "no_parameter_solution"
        elif len(self.hypotheses) == 1:
            self.status = "identified"
        elif len(self.observations) >= self.max_queries:
            self.status = "query_budget_exhausted"
        return {
            "input": x,
            "observed_output": y,
            "remaining_hypotheses": len(self.hypotheses),
            "status": self.status,
        }

    def _safe_predict(self, x, params):
        try:
            return self._predict(x, params)
        except (ArithmeticError, IndexError, TypeError, ValueError):
            return object()

    def verify(self, test_examples: Iterable[tuple[int, int]]) -> dict:
        """Score disjoint test examples only after unique parameter identification."""
        tests = tuple((int(x), int(y)) for x, y in test_examples)
        if not tests:
            raise ValueError("At least one independent test example is required")
        if self.status != "identified" or len(self.hypotheses) != 1:
            return {
                "candidate": self.candidate_name,
                "status": self.status,
                "verified": False,
                "reason": "parameters_not_uniquely_identified",
                "remaining_hypotheses": len(self.hypotheses),
            }
        overlap = self._seen_inputs.intersection(x for x, _ in tests)
        if overlap:
            raise ValueError(f"Test inputs must be disjoint from support inputs: {sorted(overlap)}")
        params = self.hypotheses[0]
        results = []
        for x, expected in tests:
            try:
                predicted = self._predict(x, params)
                passed = predicted == expected
                results.append({"x": x, "expected": expected,
                                "predicted": predicted, "passed": passed})
            except (ArithmeticError, IndexError, TypeError, ValueError) as exc:
                results.append({"x": x, "expected": expected,
                                "error": type(exc).__name__, "passed": False})
        verified = all(r["passed"] for r in results)
        return {
            "candidate": self.candidate_name,
            "status": "verified" if verified else "test_failure",
            "verified": verified,
            "inferred_parameters": list(params),
            "support_query_count": len(self.observations),
            "hypotheses_initial": (self.parameter_max - self.parameter_min + 1) ** self.parameter_count,
            "hypotheses_remaining": len(self.hypotheses),
            "passed": sum(r["passed"] for r in results),
            "total": len(results),
            "results": results,
            "method": "adaptive_min_expected_hypothesis_query_selection",
            "target_expression_accessed": False,
        }

    def report(self) -> dict:
        return {
            "candidate": self.candidate_name,
            "status": self.status,
            "support_observations": [
                {"x": x, "y": y} for x, y in self.observations
            ],
            "remaining_hypotheses": len(self.hypotheses),
            "inferred_parameters": list(self.hypotheses[0])
                if len(self.hypotheses) == 1 else None,
            "query_budget": self.max_queries,
            "queries_used": len(self.observations),
        }
