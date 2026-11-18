"""Reproducible synthetic demonstration of whole-program discovery."""
import json
from aether_discovery_core import AetherDiscoveryCore


def run_demo():
    learner = AetherDiscoveryCore(
        max_nodes=5,
        constants=(-2, -1, 0, 1, 2, 3),
        query_min=-8,
        query_max=8,
        max_queries=8,
    )

    # Synthetic target oracle. The learner receives only queried input/output.
    def external_oracle(x):
        return x * x + 3

    while True:
        x = learner.next_query()
        if x is None:
            break
        learner.observe(x, external_oracle(x))

    report = learner.verify([(9, 84), (-10, 103), (11, 124)])
    return {
        "system": "AETHER Discovery Core",
        "task": "infer an integer program from oracle observations",
        "search": learner.report(),
        "independent_verification": report,
        "boundary": (
            "This is a bounded arithmetic-grammar demonstration using a "
            "synthetic oracle. It does not establish open-ended discovery, "
            "general intelligence, or correctness beyond the finite tests."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run_demo(), indent=2))
