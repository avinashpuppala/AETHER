"""AETHER 5.0 orchestration layer over the inspected AETHER 1-4 codebase."""
from dataclasses import asdict
from .task_analyzer import TaskAnalyzer
from .primitive_inventor import PrimitiveInventor
from .counterexample_generator import CounterexampleGenerator
from .heldout_validator import HeldOutValidator
from .failure_analyzer import FailureAnalyzer

class AetherV5:
    VERSION = "5.0.0"

    def __init__(self, search_budget=20000, min_support=2):
        self.analyzer = TaskAnalyzer()
        self.inventor = PrimitiveInventor(search_budget, min_support)
        self.falsifier = CounterexampleGenerator()
        self.validator = HeldOutValidator()
        self.failures = FailureAnalyzer()
        self.candidates = []
        self.invention_report = None

    def add_task(self, name, expression, domain="arithmetic", split="train"):
        return self.analyzer.add(name, expression, domain, split)

    def invent(self):
        training_tasks = [t for t in self.analyzer.tasks.values() if t.split == "train"]
        self.candidates = self.inventor.invent(training_tasks)
        self.invention_report = {
            "engine_version": self.VERSION,
            "task_inventory": self.analyzer.inventory(),
            "search_stats": dict(self.inventor.stats),
            "candidate_count": len(self.candidates),
            "candidates": [
                {k: v for k, v in c.items() if k != "tree"}
                for c in self.candidates
            ],
        }
        return self.candidates

    def validate(self, candidate_index=0, heldout_task_names=()):
        if not self.candidates:
            raise RuntimeError("Run invent() before validate().")
        candidate = self.candidates[candidate_index]
        heldout = [self.analyzer.tasks[n] for n in heldout_task_names]
        report = self.validator.validate_candidate(candidate, heldout)
        report["research_boundary"] = (
            "Finite held-out probes validate only the supplied bounded arithmetic DSL; "
            "they are not a proof of correctness for all inputs."
        )
        return report

    def falsify(self, candidate_index=0, source_task_name=None):
        if not self.candidates:
            raise RuntimeError("Run invent() before falsify().")
        candidate = self.candidates[candidate_index]
        if source_task_name is None:
            source_task_name = candidate["support_tasks"][0]
        task = self.analyzer.tasks[source_task_name]
        # Locate the matching source subtree; compare it with the candidate
        # after binding the source task's constant parameters.
        from .heldout_validator import _capture, _evaluate_template
        from aether_advanced import _walk
        for subtree in _walk(task.tree):
            captures = {}
            if _capture(candidate["tree"], subtree, captures):
                params = tuple(captures[i] for i in range(candidate["parameter_count"]))
                failures = []
                for x in self.falsifier.probes():
                    from aether_primitive_discovery import evaluate
                    expected = evaluate(subtree, x)
                    predicted = _evaluate_template(candidate["tree"], x, params)
                    if expected != predicted:
                        failures.append({"x": x, "expected": expected,
                                         "predicted": predicted,
                                         "kind": "semantic_mismatch"})
                return {"candidate": candidate["name"], "source_task": source_task_name,
                        "verified": not failures, "probe_count": len(self.falsifier.probes()),
                        "counterexamples": failures}
        return {"candidate": candidate["name"], "source_task": source_task_name,
                "verified": False, "probe_count": 0,
                "counterexamples": [{"kind": "no_structural_match"}]}

    def report(self):
        if self.invention_report is None:
            raise RuntimeError("Run invent() before report().")
        return self.invention_report
