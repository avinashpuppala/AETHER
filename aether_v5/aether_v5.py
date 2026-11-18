"""Run the AETHER 5.0 autonomous abstraction-invention research prototype."""
import json
from aether_v5 import AetherV5

def run_demo():
    engine = AetherV5(search_budget=20000, min_support=2)
    # Training set: three source tasks; target task is deliberately withheld.
    engine.add_task("square_plus_one", "(1 + (x ** 2))", "polynomial")
    engine.add_task("square_plus_two", "(2 + (x ** 2))", "polynomial")
    engine.add_task("square_plus_five", "(5 + (x ** 2))", "polynomial")
    engine.add_task("heldout_square_plus_nine", "(9 + (x ** 2))", "polynomial", split="heldout")
    engine.add_task("absolute_plus_three", "(3 + abs(x))", "absolute-value")
    candidates = engine.invent()
    selected = next((i for i,c in enumerate(candidates)
                     if c["parameter_count"] == 1 and "x ** 2" in c["template"]), 0)
    return {
        "invention": engine.report(),
        "heldout_validation": engine.validate(selected, ["heldout_square_plus_nine"]),
        "falsification": engine.falsify(selected, "square_plus_one"),
        "failure_analysis": engine.failures.analyze([engine.falsify(selected, "square_plus_one")]),
    }

if __name__ == "__main__":
    print(json.dumps(run_demo(), indent=2))
