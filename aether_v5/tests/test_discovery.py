import unittest
from aether_primitive_discovery import (
    Example, Candidate, BoundedProgramSynthesizer, PrimitiveLibrary,
    invent_parameterized_primitive, infer_parameters_for_task, verify_primitive
)

class DiscoveryTests(unittest.TestCase):
    def test_finds_square_plus_one(self):
        s=BoundedProgramSynthesizer(max_depth=2,max_candidates=100000)
        ex=[Example(-2,5),Example(-1,2),Example(1,2),Example(2,5)]
        found=s.solve(ex)
        self.assertTrue(found)
        self.assertTrue(any("** 2" in c.expression for c in found))
    def test_requires_multiple_examples(self):
        with self.assertRaises(ValueError):
            BoundedProgramSynthesizer().solve([Example(1,2)])
    def test_invents_executable_parameterized_primitive(self):
        p=invent_parameterized_primitive(["(1 + (x ** 2))","(2 + (x ** 2))"])
        self.assertEqual(p.template, "($p1 + (x ** 2))")
        self.assertEqual(p.execute(3),10)
        self.assertEqual(p.execute(3,[7]),16)
    def test_inferrs_parameter_and_checks_heldout(self):
        p=invent_parameterized_primitive(["(1 + (x ** 2))","(2 + (x ** 2))"])
        support=[Example(-3,12),Example(0,3),Example(2,7)]
        held=[Example(-5,28),Example(4,19)]
        params=infer_parameters_for_task(p,support)
        self.assertEqual(params,(3,))
        result=verify_primitive(p,params,held)
        self.assertTrue(result["verified"])
        self.assertEqual(result["passed"],2)
    def test_rejects_inconsistent_heldout(self):
        p=invent_parameterized_primitive(["(1 + (x ** 2))","(2 + (x ** 2))"])
        result=verify_primitive(p,[3],[Example(4,20)])
        self.assertFalse(result["verified"])
    def test_rejects_different_skeletons(self):
        with self.assertRaises(ValueError):
            invent_parameterized_primitive(["(x + 1)","(x ** 2 + 2)"])

if __name__=="__main__": unittest.main()
