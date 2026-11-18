import unittest
from aether_hierarchy import HierarchicalPrimitiveLibrary, run_hierarchical_demo

class HierarchicalTests(unittest.TestCase):
    def test_mines_shared_subtree(self):
        lib=HierarchicalPrimitiveLibrary()
        lib.add_task("a","(1 + (x ** 2))")
        lib.add_task("b","(2 + (x ** 2))")
        macros=lib.mine_macros()
        self.assertTrue(any(m.tree == ("square",("x",)) for m in macros))

    def test_reuses_macro_in_new_expression(self):
        lib=HierarchicalPrimitiveLibrary()
        lib.add_task("a","(1 + (x ** 2))")
        lib.add_task("b","(2 + (x ** 2))")
        lib.mine_macros()
        self.assertEqual(lib.execute_composed("(3 + (x ** 2))",-5),28)
        self.assertEqual(lib.execute_composed("(3 + (x ** 2))",4),19)

    def test_does_not_invent_macro_from_single_task(self):
        lib=HierarchicalPrimitiveLibrary()
        lib.add_task("only","(1 + (x ** 2))")
        self.assertEqual(lib.mine_macros(),[])

    def test_demo_verifies_all_probes(self):
        result=run_hierarchical_demo()
        self.assertTrue(result["all_probes_verified"])
        self.assertEqual(len(result["probe_results"]),3)

if __name__=="__main__": unittest.main()
