"""AETHER 5.2 demo: adaptive example-only transfer.

The target function below acts as an external oracle in this synthetic demo.
The learner receives only queried (x, y) observations, never its expression.
"""
import json

from aether_v5 import AetherV5
from aether_v52 import ActiveTransferLearner


def run_demo():
    engine = AetherV5(search_budget=20000, min_support=2)
    engine.add_task("square_plus_one", "(1 + (x ** 2))", "polynomial")
    engine.add_task("square_plus_two", "(2 + (x ** 2))", "polynomial")
    engine.add_task("square_plus_five", "(5 + (x ** 2))", "polynomial")
    candidates = engine.invent()
    candidate = next(c for c in candidates
                     if c["parameter_count"] == 1 and "x ** 2" in c["template"])

    # The oracle is used only by this demo harness. The learner never receives
    # this expression, source code, or AST.
    def external_oracle(x):
        return x * x + 9

    learner = ActiveTransferLearner(
        candidate, parameter_min=-32, parameter_max=32,
        input_min=-8, input_max=8, max_queries=8,
    )
    query_log = []
    while True:
        x = learner.next_query()
        if x is None:
            break
        y = external_oracle(x)
        query_log.append(learner.observe(x, y))
        if learner.status != "collecting":
            break

    independent_tests = [(-7, 58), (2, 13), (8, 73)]
    return {
        "engine_version": "5.2.0",
        "capability": "active_example_only_transfer",
        "source_candidate": candidate["template"],
        "initial_parameter_hypotheses": 65,
        "query_strategy": "choose input minimizing expected remaining hypotheses",
        "adaptive_support_query_log": query_log,
        "learner_report": learner.report(),
        "independent_test_validation": learner.verify(independent_tests),
        "research_boundary": (
            "The learner selects informative inputs and infers parameters only "
            "within a finite configured range and frozen arithmetic template. "
            "The demo oracle is synthetic; finite tests do not prove general "
            "correctness or establish unrestricted autonomous discovery."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run_demo(), indent=2))
