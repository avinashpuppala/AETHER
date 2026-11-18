"""Demonstrate cross-task abstraction mining and transfer."""
import json
from abstraction_miner import AbstractionMiner, parse_expression


def run_demo():
    training = [
        ("absolute_plus_one", parse_expression("(abs(x) + 1)")),
        ("absolute_plus_two", parse_expression("(abs(x) + 2)")),
        ("absolute_plus_five", parse_expression("(abs(x) + 5)")),
    ]
    miner = AbstractionMiner(min_tasks=2, min_nodes=2)
    operators = miner.discover(training)

    target_tree = parse_expression("(abs(x) + 7)")
    selected = next(op for op in operators if op.expression == "(abs(x) + $p1)")
    bound_parameters = selected.bind(target_tree)

    tests = [(-11, 18), (-2, 9), (0, 7), (8, 15)]
    checks = [
        {
            "x": x,
            "expected": expected,
            "predicted": selected.execute(x, bound_parameters),
            "passed": selected.execute(x, bound_parameters) == expected,
        }
        for x, expected in tests
    ]
    return {
        "mining": miner.stats,
        "learned_operators": miner.manifest(),
        "transferred_operator": selected.name,
        "target_parameter_binding": list(bound_parameters),
        "heldout_checks": checks,
        "all_heldout_checks_passed": all(c["passed"] for c in checks),
        "research_boundary": (
            "The operator is a parameterized abstraction mined from programs "
            "already available to the miner. The target program is structurally "
            "matched to bind its parameter; this demo does not infer the target "
            "from black-box observations or invent semantics outside the DSL."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run_demo(), indent=2))
