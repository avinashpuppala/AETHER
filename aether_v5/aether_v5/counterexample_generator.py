"""Deterministic adversarial probe generation and mutation-based falsification."""
from aether_primitive_discovery import evaluate

class CounterexampleGenerator:
    def __init__(self, bound=64):
        if bound < 1:
            raise ValueError("bound must be positive")
        self.bound = bound

    def probes(self):
        # Dense small values catch local mistakes; boundaries and large values
        # catch overflow/constant-offset mistakes. All probes are deterministic.
        values = set(range(-self.bound, self.bound + 1))
        values.update({-(self.bound ** 2), self.bound ** 2, -1000, -127, 127, 1000})
        return tuple(sorted(values))

    def compare(self, source_tree, candidate_tree):
        failures = []
        for x in self.probes():
            try:
                expected = evaluate(source_tree, x)
                predicted = evaluate(candidate_tree, x)
                if expected != predicted:
                    failures.append({
                        "x": x, "expected": expected, "predicted": predicted,
                        "kind": "semantic_mismatch",
                    })
            except (ArithmeticError, ValueError, TypeError) as exc:
                failures.append({"x": x, "error": type(exc).__name__,
                                 "kind": "execution_error"})
        return {"verified": not failures, "probes": len(self.probes()),
                "counterexamples": failures}
