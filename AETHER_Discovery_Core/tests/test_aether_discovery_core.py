import unittest

from aether_discovery_core import AetherDiscoveryCore, enumerate_programs


class DiscoveryCoreTests(unittest.TestCase):
    def test_enumerates_bounded_program_space(self):
        programs, complete = enumerate_programs(max_nodes=4)
        self.assertTrue(complete)
        self.assertIn(("add", ("const", 3), ("square", ("x",))), programs)

    def test_invents_program_from_active_oracle_queries(self):
        learner = AetherDiscoveryCore(max_nodes=5)
        oracle = lambda x: x * x + 3
        while True:
            x = learner.next_query()
            if x is None:
                break
            learner.observe(x, oracle(x))
        report = learner.verify([(9, 84), (-10, 103), (11, 124)])
        self.assertTrue(report["verified"])
        self.assertEqual(report["status"], "verified_equivalence_set")
        self.assertEqual(report["representative_program"], "(3 + (x ** 2))")
        self.assertEqual(report["passed"], 3)

    def test_rejects_duplicate_support_input(self):
        learner = AetherDiscoveryCore(max_nodes=4)
        x = learner.next_query()
        learner.observe(x, x * x + 1)
        with self.assertRaises(ValueError):
            learner.observe(x, x * x + 1)

    def test_rejects_support_test_overlap(self):
        learner = AetherDiscoveryCore(max_nodes=4)
        x = learner.next_query()
        learner.observe(x, x * x + 1)
        while learner.status == "collecting":
            q = learner.next_query()
            if q is None:
                break
            learner.observe(q, q * q + 1)
        with self.assertRaises(ValueError):
            learner.verify([(x, x * x + 1)])

    def test_reports_no_solution_outside_grammar(self):
        learner = AetherDiscoveryCore(max_nodes=3, constants=(-1, 0, 1))
        x = learner.next_query()
        learner.observe(x, 1000000)
        self.assertEqual(learner.status, "no_consistent_program")
        self.assertFalse(learner.verify([(x + 1, 1000001)])["verified"])

    def test_candidate_budget_is_explicit(self):
        programs, complete = enumerate_programs(max_nodes=5, max_candidates=10)
        self.assertEqual(len(programs), 10)
        self.assertFalse(complete)

    def test_query_budget_is_enforced(self):
        learner = AetherDiscoveryCore(max_nodes=5, max_queries=1)
        x = learner.next_query()
        learner.observe(x, x * x + 3)
        if learner.status == "collecting":
            self.assertIsNone(learner.next_query())
            self.assertEqual(learner.status, "query_budget_exhausted")


if __name__ == "__main__":
    unittest.main()
