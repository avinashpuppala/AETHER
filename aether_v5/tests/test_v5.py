import unittest
from aether_v5 import AetherV5

class AetherV5Tests(unittest.TestCase):
    def build(self):
        e = AetherV5(search_budget=5000)
        e.add_task("a", "(1 + (x ** 2))", "polynomial")
        e.add_task("b", "(2 + (x ** 2))", "polynomial")
        e.add_task("c", "(5 + (x ** 2))", "polynomial")
        e.add_task("held", "(9 + (x ** 2))", "polynomial", split="heldout")
        return e

    def test_invents_parameterized_abstraction(self):
        e = self.build()
        candidates = e.invent()
        self.assertTrue(candidates)
        self.assertTrue(any(c["parameter_count"] == 1 and "x ** 2" in c["template"] for c in candidates))

    def test_heldout_task_is_not_used_for_invention(self):
        e = self.build()
        e.invent()
        self.assertTrue(all("held" not in c["support_tasks"] for c in e.candidates))
        report = e.validate(0, ["held"])
        self.assertEqual(report["heldout_task_count"], 1)
        self.assertGreater(report["matched_task_count"], 0)
        self.assertEqual(report["verified_matches"], report["matched_task_count"])
        self.assertGreaterEqual(report["matched_task_count"], 0)

    def test_falsifier_runs_bounded_adversarial_probes(self):
        e = self.build()
        e.invent()
        report = e.falsify(0, e.candidates[0]["support_tasks"][0])
        self.assertGreater(report["probe_count"], 100)
        self.assertTrue(report["verified"])

    def test_task_analyzer_rejects_unsupported_expression(self):
        e = AetherV5()
        with self.assertRaises(ValueError):
            e.add_task("bad", "__import__('os').system('whoami')")

    def test_budget_is_bounded(self):
        e = AetherV5(search_budget=1)
        e.add_task("a", "(1 + (x ** 2))")
        e.add_task("b", "(2 + (x ** 2))")
        e.invent()
        self.assertLessEqual(e.inventor.stats["candidate_combinations_examined"], 1)

if __name__ == "__main__":
    unittest.main()
