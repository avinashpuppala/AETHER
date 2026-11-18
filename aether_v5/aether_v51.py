"""AETHER 5.1 example-only transfer demonstration.

The validator receives only support/test input-output pairs for the target.
It is never given the target expression or target AST.
"""
import json

from aether_v5 import AetherV5
from aether_v51 import ExampleOnlyTransferValidator


def run_demo():
    engine = AetherV5(search_budget=20000, min_support=2)
    engine.add_task("square_plus_one", "(1 + (x ** 2))", "polynomial")
    engine.add_task("square_plus_two", "(2 + (x ** 2))", "polynomial")
    engine.add_task("square_plus_five", "(5 + (x ** 2))", "polynomial")
    candidates = engine.invent()
    candidate = next(c for c in candidates
                     if c["parameter_count"] == 1 and "x ** 2" in c["template"])

    # Target is represented only by observations. Its expression is not passed
    # to AETHER 5.1's validator.
    support = [(-2, 13), (0, 9), (3, 18)]
    test = [(-7, 58), (2, 13), (8, 73)]
    report = ExampleOnlyTransferValidator(-32, 32).validate(
        candidate, support, test
    )
    return {
        "engine_version": "5.1.0",
        "candidate": candidate["template"],
        "support_examples": support,
        "independent_test_examples": test,
        "transfer_validation": report,
        "research_boundary": (
            "This is bounded parameter inference for a frozen template in the "
            "integer arithmetic DSL; it is not proof of general correctness."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run_demo(), indent=2))
