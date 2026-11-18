"""Run AETHER transfer tests against a bounded enumerative-search baseline."""
import json
from aether_evolution import AetherEvolutionEngine

FAMILIES = {
    "square_plus_constant": {
        "source_tasks": {
            "square_plus_one": "(1 + (x ** 2))",
            "square_plus_two": "(2 + (x ** 2))",
            "square_plus_five": "(5 + (x ** 2))",
        },
        "target": "(9 + (x ** 2))",
    },
    "absolute_plus_constant": {
        "source_tasks": {
            "absolute_plus_one": "(1 + abs(x))",
            "absolute_plus_two": "(2 + abs(x))",
            "absolute_plus_five": "(5 + abs(x))",
        },
        "target": "(9 + abs(x))",
    },
    "linear_plus_constant": {
        "source_tasks": {
            "linear_plus_one": "(1 + (2 * x))",
            "linear_plus_two": "(2 + (2 * x))",
            "linear_plus_five": "(5 + (2 * x))",
        },
        "target": "(9 + (2 * x))",
    },
}

if __name__ == "__main__":
    engine = AetherEvolutionEngine()
    report = engine.benchmark_transfer(
        FAMILIES, probes=(-5, -2, 0, 3, 7),
        include_symbolic_baseline=True, baseline_candidate_limit=100000)
    print(json.dumps(report, indent=2))
