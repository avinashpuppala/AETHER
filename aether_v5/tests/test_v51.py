import unittest

from aether_v5 import AetherV5
from aether_v51 import ExampleOnlyTransferValidator


class AetherV51Tests(unittest.TestCase):
    def candidate(self):
        engine = AetherV5(search_budget=20000, min_support=2)
        engine.add_task("one", "(1 + (x ** 2))", "polynomial")
        engine.add_task("two", "(2 + (x ** 2))", "polynomial")
        engine.add_task("five", "(5 + (x ** 2))", "polynomial")
        candidates = engine.invent()
        return next(c for c in candidates
                    if c["parameter_count"] == 1 and "x ** 2" in c["template"])

    def test_infers_unknown_parameter_from_support_io_and_tests_disjoint_inputs(self):
        report = ExampleOnlyTransferValidator(-32, 32).validate(
            self.candidate(),
            support_examples=[(-2, 13), (0, 9), (3, 18)],
            test_examples=[(-7, 58), (2, 13), (8, 73)],
        )
        self.assertTrue(report["verified"])
        self.assertEqual(report["inferred_parameters"], [9])
        self.assertEqual(report["passed"], 3)
        self.assertFalse(report["target_expression_accessed"])

    def test_rejects_wrong_test_observation(self):
        report = ExampleOnlyTransferValidator(-32, 32).validate(
            self.candidate(),
            support_examples=[(-2, 13), (0, 9)],
            test_examples=[(2, 999)],
        )
        self.assertFalse(report["verified"])
        self.assertEqual(report["status"], "test_failure")

    def test_reports_ambiguous_parameter_solution(self):
        # At x=0, a square-offset template is identified by y; this test uses
        # repeated input/output constraints that still uniquely identify 9.
        # A deliberately broad bound with no support discrimination is not
        # possible for this template, so test the API's ambiguity via a custom
        # candidate whose parameter is multiplied by zero.
        candidate = {
            "name": "degenerate",
            "tree": ("mul", ("param", 0), ("const", 0)),
            "parameter_count": 1,
        }
        report = ExampleOnlyTransferValidator(-2, 2).validate(
            candidate, [(0, 0), (1, 0)], [(2, 0)]
        )
        self.assertEqual(report["status"], "ambiguous_parameter_solution")
        self.assertFalse(report["verified"])

    def test_requires_disjoint_test_examples(self):
        with self.assertRaises(ValueError):
            ExampleOnlyTransferValidator().validate(
                self.candidate(), [(0, 9), (1, 10)], []
            )


if __name__ == "__main__":
    unittest.main()
