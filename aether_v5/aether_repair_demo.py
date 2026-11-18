"""Demonstrate AETHER's bounded, evidence-gated macro-library repair."""
import json
from aether_evolution import AetherEvolutionEngine


def run_demo():
    engine = AetherEvolutionEngine()
    engine.add_task("square_plus_one", "(1 + (x ** 2))")
    engine.add_task("square_plus_two", "(2 + (x ** 2))")
    engine.add_task("square_plus_five", "(5 + (x ** 2))")
    engine.discover()

    target = "(9 + (x ** 2))"
    macro_name = next(iter(engine.library.macros))
    deliberately_bad = ("macro_call", macro_name, (("const", 999),))
    before = engine.verify_composition(target, [0], candidate_tree=deliberately_bad)
    repair = engine.repair_from_counterexamples()
    after = engine.verify_composition(target, [-7, -2, 0, 3, 8])
    return {"failure_detected": not before["verified"],
            "repair": repair,
            "post_repair_verification": after,
            "engine": engine.explain()}


if __name__ == "__main__":
    print(json.dumps(run_demo(), indent=2))
