import tempfile
import unittest
from unittest.mock import patch
import aether_advanced
from pathlib import Path

from aether_advanced import AdvancedPrimitiveLibrary


class AdvancedDiscoveryTests(unittest.TestCase):
    def build_library(self):
        lib = AdvancedPrimitiveLibrary()
        lib.add_task("square_plus_one", "(1 + (x ** 2))")
        lib.add_task("square_plus_two", "(2 + (x ** 2))")
        lib.add_task("square_plus_five", "(5 + (x ** 2))")
        return lib

    def test_invents_parameterized_shared_macro(self):
        lib = self.build_library()
        macros = lib.discover()
        macro = next(m for m in macros if m.parameter_count == 1 and "** 2" in m.template)
        self.assertEqual(macro.execute(4, [9]), 25)
        self.assertEqual(macro.parameter_count, 1)

    def test_reuses_parameterized_macro_on_unseen_constant(self):
        lib = self.build_library()
        lib.discover()
        self.assertEqual(lib.execute_composed("(9 + (x ** 2))", -5), 34)
        self.assertEqual(lib.execute_composed("(9 + (x ** 2))", 4), 25)

    def test_counterexample_guided_verification_records_failures(self):
        lib = self.build_library()
        lib.discover()
        result = lib.verify_composition("(9 + (x ** 2))", [0, 2, 7])
        self.assertTrue(result["verified"])
        self.assertEqual(result["counterexample_count"], 0)
        # Simulate an execution-layer defect while leaving the matcher intact.
        original_eval = aether_advanced._eval
        def faulty_eval(node, x, params, macros):
            if node[0] == "macro_call":
                return 999
            return original_eval(node, x, params, macros)
        with patch("aether_advanced._eval", side_effect=faulty_eval):
            failed = lib.verify_composition("(9 + (x ** 2))", [0, 2])
        self.assertFalse(failed["verified"])
        self.assertEqual(failed["counterexample_count"], 2)
        self.assertEqual(len(lib.counterexamples), 2)

    def test_invents_multiple_independent_parameters(self):
        lib = AdvancedPrimitiveLibrary()
        lib.add_task("pair_a", "((x + 1) * (x + 3))")
        lib.add_task("pair_b", "((x + 2) * (x + 5))")
        macros = lib.discover()
        macro = next(m for m in macros if m.parameter_count == 2 and "*" in m.template)
        self.assertEqual(macro.execute(4, [7, 9]), 143)

    def test_repeated_parameter_positions_are_tied(self):
        lib = AdvancedPrimitiveLibrary()
        lib.add_task("a", "((x + 1) * (x + 1))")
        lib.add_task("b", "((x + 2) * (x + 2))")
        macros = lib.discover()
        repeated = next(m for m in macros if m.parameter_count == 1 and "*" in m.template and "$p1" in m.template)
        self.assertEqual(repeated.execute(3, [4]), 49)

    def test_save_and_load_preserve_execution(self):
        lib = self.build_library()
        lib.discover()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "library.json"
            lib.save(path)
            restored = AdvancedPrimitiveLibrary.load(path)
            self.assertEqual(restored.execute_composed("(9 + (x ** 2))", 6), 45)
            self.assertEqual(restored.explain()["macro_count"], lib.explain()["macro_count"])

    def test_requires_multiple_tasks(self):
        lib = AdvancedPrimitiveLibrary()
        lib.add_task("one", "(1 + (x ** 2))")
        self.assertEqual(lib.discover(), [])

    def test_search_budget_is_bounded(self):
        lib = self.build_library()
        lib.discover(max_candidate_combinations=1)
        self.assertLessEqual(lib.search_stats["candidate_combinations"], 1)


if __name__ == "__main__":
    unittest.main()
