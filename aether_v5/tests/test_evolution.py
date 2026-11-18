import tempfile
import unittest
from pathlib import Path

from aether_evolution import AetherEvolutionEngine


class EvolutionEngineTests(unittest.TestCase):
    def build(self):
        engine = AetherEvolutionEngine()
        engine.add_task("square_plus_one", "(1 + (x ** 2))")
        engine.add_task("square_plus_two", "(2 + (x ** 2))")
        engine.add_task("square_plus_five", "(5 + (x ** 2))")
        engine.discover()
        return engine

    def test_compiles_nested_macro_dependencies(self):
        engine = self.build()
        self.assertTrue(any(engine.macro_dependencies.values()))
        self.assertEqual(engine.execute_composed("(9 + (x ** 2))", 4), 25)

    def test_nested_composition_verifies_held_out_probes(self):
        engine = self.build()
        result = engine.verify_composition("(9 + (x ** 2))", [-9, -2, 0, 3, 11])
        self.assertTrue(result["verified"])
        self.assertEqual(result["counterexample_count"], 0)

    def test_counterexample_refinement_quarantines_bad_macro(self):
        engine = self.build()
        candidate = ("macro_call", next(iter(engine.library.macros)), (999,))
        failed = engine.verify_composition("(9 + (x ** 2))", [0], candidate_tree=candidate)
        self.assertFalse(failed["verified"])
        refined = engine.refine_from_counterexamples()
        self.assertTrue(refined["quarantined"])
        self.assertEqual(engine.execute_composed("(9 + (x ** 2))", 3), 18)

    def test_quarantine_persists_after_reload(self):
        engine = self.build()
        engine.library.counterexamples.append({"macro_names": [next(iter(engine.library.macros))]})
        engine.refine_from_counterexamples()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "evolution.json"
            engine.save(path)
            restored = AetherEvolutionEngine.load(path)
            self.assertEqual(restored.quarantined_macros, engine.quarantined_macros)
            self.assertEqual(restored.execute_composed("(9 + (x ** 2))", 5), 34)

    def test_automatic_repair_rebuilds_corrupted_macro_library(self):
        engine = self.build()
        expression = "(9 + (x ** 2))"
        macro_name = next(iter(engine.library.macros))
        # Simulate a bad abstraction call while preserving source tasks.
        failed = engine.verify_composition(
            expression, [0], candidate_tree=("macro_call", macro_name, (("const", 999),)))
        self.assertFalse(failed["verified"])
        repaired = engine.repair_from_counterexamples()
        self.assertTrue(repaired["repaired"])
        self.assertTrue(engine.verify_composition(expression, [-7, -2, 0, 3, 8])["verified"])

    def test_automatic_repair_refuses_without_counterexamples(self):
        engine = self.build()
        result = engine.repair_from_counterexamples()
        self.assertFalse(result["repaired"])
        self.assertEqual(result["reason"], "no_counterexamples")

    def test_benchmark_can_compare_bounded_symbolic_baseline(self):
        engine = AetherEvolutionEngine()
        report = engine.benchmark_transfer({
            "square_plus_constant": {
                "source_tasks": {"a": "(1 + (x ** 2))", "b": "(2 + (x ** 2))",
                                 "c": "(5 + (x ** 2))"},
                "target": "(9 + (x ** 2))"}
        }, probes=(-5, -2, 0, 3, 7), include_symbolic_baseline=True,
           baseline_candidate_limit=100000)
        baseline = report["results"][0]["symbolic_baseline"]
        self.assertTrue(baseline["candidate_found"])
        self.assertTrue(baseline["held_out_verified"])
        self.assertEqual(baseline["held_out_total"], 2)

    def test_benchmark_uses_held_out_target_tasks(self):
        engine = AetherEvolutionEngine()
        report = engine.benchmark_transfer({
            "square_plus_constant": {
                "source_tasks": {"a": "(1 + (x ** 2))", "b": "(2 + (x ** 2))",
                                 "c": "(5 + (x ** 2))"},
                "target": "(9 + (x ** 2))"},
            "absolute_plus_constant": {
                "source_tasks": {"a": "(1 + abs(x))", "b": "(2 + abs(x))",
                                 "c": "(5 + abs(x))"},
                "target": "(9 + abs(x))"}
        })
        self.assertEqual(report["families_tested"], 2)
        self.assertEqual(report["verified_families"], 2)


if __name__ == "__main__":
    unittest.main()
