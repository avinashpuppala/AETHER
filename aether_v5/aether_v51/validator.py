"""Example-only transfer validation for AETHER 5.1.

Unlike the AETHER 5.0 structural held-out validator, this module never reads a
held-out task's expression/tree. It infers template parameters only from
caller-supplied support input/output examples, then evaluates disjoint test
examples. Search is finite and reports ambiguity explicitly.
"""
from __future__ import annotations

from itertools import product
from typing import Iterable, Sequence


def evaluate_template(node: tuple, x: int, params: Sequence[int]) -> int:
    """Evaluate the bounded AETHER AST without eval/exec."""
    kind = node[0]
    if kind == "x":
        return x
    if kind == "const":
        return node[1]
    if kind == "param":
        return params[node[1]]
    if kind == "neg":
        return -evaluate_template(node[1], x, params)
    if kind == "abs":
        return abs(evaluate_template(node[1], x, params))
    if kind == "square":
        value = evaluate_template(node[1], x, params)
        return value * value
    if kind in ("add", "sub", "mul"):
        left = evaluate_template(node[1], x, params)
        right = evaluate_template(node[2], x, params)
        if kind == "add":
            return left + right
        if kind == "sub":
            return left - right
        return left * right
    raise ValueError(f"Unsupported AST node: {kind}")


class ExampleOnlyTransferValidator:
    """Infer frozen-template parameters from support examples, test separately."""

    def __init__(self, parameter_min: int = -32, parameter_max: int = 32):
        if parameter_min > parameter_max:
            raise ValueError("parameter_min must be <= parameter_max")
        self.parameter_values = tuple(range(parameter_min, parameter_max + 1))

    def validate(
        self,
        candidate: dict,
        support_examples: Iterable[tuple[int, int]],
        test_examples: Iterable[tuple[int, int]],
    ) -> dict:
        support = tuple((int(x), int(y)) for x, y in support_examples)
        tests = tuple((int(x), int(y)) for x, y in test_examples)
        if len(support) < 2:
            raise ValueError("At least two support examples are required.")
        if not tests:
            raise ValueError("At least one disjoint test example is required.")

        tree = candidate["tree"]
        parameter_count = int(candidate["parameter_count"])
        if parameter_count < 1:
            raise ValueError("Candidate must contain at least one parameter.")

        matches = []
        for params in product(self.parameter_values, repeat=parameter_count):
            try:
                if all(evaluate_template(tree, x, params) == y for x, y in support):
                    matches.append(tuple(params))
            except (ArithmeticError, IndexError, TypeError, ValueError):
                continue

        base = {
            "candidate": candidate.get("name", "unnamed"),
            "support_count": len(support),
            "test_count": len(tests),
            "parameter_search_range": [
                self.parameter_values[0], self.parameter_values[-1]
            ],
            "parameter_solutions": len(matches),
            "target_expression_accessed": False,
            "method": "bounded_parameter_search_from_support_io_only",
        }
        if not matches:
            return {**base, "status": "no_parameter_solution",
                    "inferred_parameters": None, "verified": False, "results": []}
        if len(matches) > 1:
            return {**base, "status": "ambiguous_parameter_solution",
                    "inferred_parameters": None, "verified": False, "results": []}

        params = matches[0]
        results = []
        for x, expected in tests:
            try:
                predicted = evaluate_template(tree, x, params)
                passed = predicted == expected
                results.append({"x": x, "expected": expected,
                                "predicted": predicted, "passed": passed})
            except (ArithmeticError, IndexError, TypeError, ValueError) as exc:
                results.append({"x": x, "expected": expected,
                                "error": type(exc).__name__, "passed": False})

        verified = all(row["passed"] for row in results)
        return {
            **base,
            "status": "verified" if verified else "test_failure",
            "inferred_parameters": list(params),
            "verified": verified,
            "passed": sum(row["passed"] for row in results),
            "total": len(results),
            "results": results,
        }
