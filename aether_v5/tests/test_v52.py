import unittest

from aether_v52 import ActiveTransferLearner


class ActiveTransferTests(unittest.TestCase):
    def square_plus_constant(self):
        return {
            "name": "square_plus_parameter",
            "tree": ("add", ("param", 0), ("square", ("x",))),
            "parameter_count": 1,
        }

    def test_adaptively_identifies_parameter_and_verifies_disjoint_tests(self):
        learner = ActiveTransferLearner(
            self.square_plus_constant(), -10, 10, -5, 5, max_queries=4
        )
        x = learner.next_query()
        self.assertIsNotNone(x)
        learner.observe(x, x * x + 4)
        self.assertEqual(learner.status, "identified")
        report = learner.verify([(-3, 13), (2, 8)])
        self.assertTrue(report["verified"])
        self.assertEqual(report["inferred_parameters"], [4])
        self.assertFalse(report["target_expression_accessed"])

    def test_rejects_reused_support_input(self):
        learner = ActiveTransferLearner(self.square_plus_constant(), -3, 3)
        x = learner.next_query()
        learner.observe(x, x * x + 2)
        with self.assertRaises(ValueError):
            learner.observe(x, x * x + 2)

    def test_rejects_overlap_between_support_and_test(self):
        learner = ActiveTransferLearner(self.square_plus_constant(), -3, 3)
        x = learner.next_query()
        learner.observe(x, x * x + 2)
        with self.assertRaises(ValueError):
            learner.verify([(x, x * x + 2)])

    def test_reports_no_solution_for_inconsistent_observation(self):
        learner = ActiveTransferLearner(self.square_plus_constant(), -3, 3)
        x = learner.next_query()
        learner.observe(x, 999)
        self.assertEqual(learner.status, "no_parameter_solution")
        self.assertFalse(learner.verify([(1, 1000)])["verified"])

    def test_requires_unique_parameter_before_verification(self):
        candidate = {
            "name": "degenerate",
            "tree": ("mul", ("param", 0), ("const", 0)),
            "parameter_count": 1,
        }
        learner = ActiveTransferLearner(candidate, -2, 2, -2, 2)
        x = learner.next_query()
        learner.observe(x, 0)
        report = learner.verify([(1, 0)])
        self.assertFalse(report["verified"])
        self.assertEqual(report["reason"], "parameters_not_uniquely_identified")

    def test_query_budget_is_respected(self):
        learner = ActiveTransferLearner(self.square_plus_constant(), -5, 5,
                                        -2, 2, max_queries=1)
        x = learner.next_query()
        learner.observe(x, x * x + 2)
        self.assertIsNone(learner.next_query())


if __name__ == "__main__":
    unittest.main()
