import unittest
from abstraction_miner import AbstractionMiner, parse_expression


class AbstractionMinerTests(unittest.TestCase):
    def setUp(self):
        self.training = [
            ("a", parse_expression("(abs(x) + 1)")),
            ("b", parse_expression("(abs(x) + 2)")),
            ("c", parse_expression("(abs(x) + 5)")),
        ]

    def test_discovers_parameterized_operator(self):
        miner = AbstractionMiner()
        ops = miner.discover(self.training)
        self.assertTrue(any(op.expression == "(abs(x) + $p1)" for op in ops))

    def test_operator_executes_with_bound_parameter(self):
        miner = AbstractionMiner()
        ops = miner.discover(self.training)
        op = next(op for op in ops if op.expression == "(abs(x) + $p1)")
        self.assertEqual(op.execute(-8, (7,)), 15)

    def test_binds_parameter_from_new_program(self):
        miner = AbstractionMiner()
        ops = miner.discover(self.training)
        op = next(op for op in ops if op.expression == "(abs(x) + $p1)")
        params = op.bind(parse_expression("(abs(x) + 9)"))
        self.assertEqual(params, (9,))

    def test_requires_multiple_source_tasks(self):
        miner = AbstractionMiner(min_tasks=2)
        self.assertEqual(miner.discover(self.training[:1]), [])

    def test_does_not_promote_constant_only_pattern(self):
        miner = AbstractionMiner()
        data = [
            ("a", parse_expression("(x + 3)")),
            ("b", parse_expression("(x + 3)")),
        ]
        self.assertEqual(miner.discover(data), [])

    def test_rejects_nonmatching_target(self):
        miner = AbstractionMiner()
        ops = miner.discover(self.training)
        op = next(op for op in ops if op.expression == "(abs(x) + $p1)")
        with self.assertRaises(ValueError):
            op.bind(parse_expression("(x + 9)"))

    def test_transfer_on_heldout_inputs(self):
        miner = AbstractionMiner()
        ops = miner.discover(self.training)
        op = next(op for op in ops if op.expression == "(abs(x) + $p1)")
        params = op.bind(parse_expression("(abs(x) + 7)"))
        for x, expected in [(-11, 18), (-2, 9), (0, 7), (8, 15)]:
            self.assertEqual(op.execute(x, params), expected)


if __name__ == "__main__":
    unittest.main()
