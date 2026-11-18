"""Cross-task abstraction mining and executable macro transfer.

This layer discovers parameterized reusable subprograms from independently
synthesized task programs. It is bounded to AETHER's existing arithmetic AST.
It does not invent primitive semantics outside that grammar.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable
import ast

from aether_discovery_core import _node_count


def parse_expression(expression: str):
    """Parse only the arithmetic operators supported by the discovery core."""
    tree = ast.parse(expression, mode="eval")
    def visit(node):
        if isinstance(node, ast.Expression):
            return visit(node.body)
        if isinstance(node, ast.Name) and node.id == "x":
            return ("x",)
        if isinstance(node, ast.Constant) and isinstance(node.value, int) and not isinstance(node.value, bool):
            return ("const", node.value)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return ("neg", visit(node.operand))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "abs" and len(node.args) == 1:
            return ("abs", visit(node.args[0]))
        if isinstance(node, ast.BinOp):
            if isinstance(node.op, ast.Pow) and isinstance(node.right, ast.Constant) and node.right.value == 2:
                return ("square", visit(node.left))
            ops = {ast.Add: "add", ast.Sub: "sub", ast.Mult: "mul"}
            for typ, name in ops.items():
                if isinstance(node.op, typ):
                    return (name, visit(node.left), visit(node.right))
        raise ValueError("Expression uses an unsupported operation")
    return visit(tree)


def _pattern_size(node):
    if node[0] in ("x", "const", "param"):
        return 1
    return 1 + sum(_pattern_size(child) for child in _children(node))


def _children(node):
    if node[0] in ("neg", "abs", "square"):
        return (node[1],)
    if node[0] in ("add", "sub", "mul"):
        return (node[1], node[2])
    return ()


def _walk(node):
    yield node
    for child in _children(node):
        yield from _walk(child)


def _skeleton(node):
    if node[0] == "const":
        return ("constant",)
    if node[0] == "x":
        return ("x",)
    return (node[0],) + tuple(_skeleton(c) for c in _children(node))


def _abstract_constants(node, slots):
    if node[0] == "const":
        value = node[1]
        if value not in slots:
            slots[value] = len(slots)
        return ("param", slots[value])
    if node[0] in ("x",):
        return node
    if node[0] in ("neg", "abs", "square"):
        return (node[0], _abstract_constants(node[1], slots))
    return (node[0], _abstract_constants(node[1], slots),
            _abstract_constants(node[2], slots))


def _render_pattern(node):
    kind = node[0]
    if kind == "param":
        return f"$p{node[1] + 1}"
    if kind == "x":
        return "x"
    if kind == "neg":
        return f"(-{_render_pattern(node[1])})"
    if kind == "abs":
        return f"abs({_render_pattern(node[1])})"
    if kind == "square":
        return f"({_render_pattern(node[1])} ** 2)"
    op = {"add": "+", "sub": "-", "mul": "*"}[kind]
    return f"({_render_pattern(node[1])} {op} {_render_pattern(node[2])})"


def _eval_pattern(node, x, params):
    kind = node[0]
    if kind == "x":
        return x
    if kind == "param":
        return params[node[1]]
    if kind == "const":
        return node[1]
    if kind == "neg":
        return -_eval_pattern(node[1], x, params)
    if kind == "abs":
        return abs(_eval_pattern(node[1], x, params))
    if kind == "square":
        v = _eval_pattern(node[1], x, params)
        return v * v
    a = _eval_pattern(node[1], x, params)
    b = _eval_pattern(node[2], x, params)
    return {"add": a + b, "sub": a - b, "mul": a * b}[kind]


def _match_pattern(pattern, concrete, params):
    if pattern[0] == "param":
        if concrete[0] != "const":
            return False
        slot, value = pattern[1], concrete[1]
        if slot in params and params[slot] != value:
            return False
        params[slot] = value
        return True
    if pattern[0] != concrete[0]:
        return False
    if pattern[0] in ("x", "const"):
        return pattern == concrete
    return all(_match_pattern(a, b, params)
               for a, b in zip(_children(pattern), _children(concrete)))


@dataclass(frozen=True)
class LearnedOperator:
    name: str
    pattern: tuple
    parameter_count: int
    source_tasks: tuple[str, ...]
    expression: str

    def execute(self, x: int, parameters: Iterable[int]) -> int:
        values = tuple(int(v) for v in parameters)
        if len(values) != self.parameter_count:
            raise ValueError(f"{self.name} requires {self.parameter_count} parameters")
        return _eval_pattern(self.pattern, int(x), values)

    def bind(self, concrete_expression_tree):
        captured = {}
        if not _match_pattern(self.pattern, concrete_expression_tree, captured):
            raise ValueError("Expression does not match this learned operator")
        if set(captured) != set(range(self.parameter_count)):
            raise ValueError("Could not bind every operator parameter")
        return tuple(captured[i] for i in range(self.parameter_count))


class AbstractionMiner:
    """Mine parameterized abstractions shared by multiple task programs."""
    def __init__(self, min_tasks=2, min_nodes=2, max_patterns=5000):
        if min_tasks < 2 or min_nodes < 2 or max_patterns < 1:
            raise ValueError("Invalid mining limits")
        self.min_tasks = min_tasks
        self.min_nodes = min_nodes
        self.max_patterns = max_patterns
        self.operators = []
        self.stats = {}

    def discover(self, task_programs):
        # task_programs: iterable of (task_name, AST). Each task contributes
        # at most one instance per structural skeleton to prevent duplicates.
        buckets = {}
        task_domains = {}
        for task_name, tree in task_programs:
            task_domains[task_name] = tree
            seen = set()
            for subtree in _walk(tree):
                if _node_count(subtree) < self.min_nodes:
                    continue
                shape = _skeleton(subtree)
                if shape in seen:
                    continue
                seen.add(shape)
                slots = {}
                pattern = _abstract_constants(subtree, slots)
                if not slots:
                    continue
                key = repr(pattern)
                buckets.setdefault(key, {"pattern": pattern, "tasks": set(),
                                         "parameter_values": set()})
                buckets[key]["tasks"].add(task_name)
                # Preserve parameter values by matching the candidate pattern.
                values = {}
                if _match_pattern(pattern, subtree, values):
                    buckets[key]["parameter_values"].add(tuple(values[i] for i in range(len(values))))

        candidates = []
        for item in buckets.values():
            if len(item["tasks"]) < self.min_tasks:
                continue
            pattern = item["pattern"]
            param_count = max((n[1] + 1 for n in _walk(pattern) if n[0] == "param"), default=0)
            # Require at least one slot to vary across source tasks. This avoids
            # simply renaming a fixed expression as a learned operator.
            rows = list(item["parameter_values"])
            varies = any(len({row[i] for row in rows}) > 1 for i in range(param_count))
            if not varies:
                continue
            node_count = _pattern_size(pattern)
            score = (len(item["tasks"]) - 1) * max(1, node_count - param_count)
            candidates.append((score, pattern, tuple(sorted(item["tasks"]),), param_count))

        candidates.sort(key=lambda x: (-x[0], -_pattern_size(x[1]), repr(x[1])))
        self.operators = [
            LearnedOperator(
                name=f"learned_op_{i:03d}",
                pattern=pattern,
                parameter_count=param_count,
                source_tasks=tasks,
                expression=_render_pattern(pattern),
            )
            for i, (_, pattern, tasks, param_count) in enumerate(candidates[:self.max_patterns], 1)
        ]
        self.stats = {
            "source_task_count": len(task_domains),
            "candidate_pattern_count": len(buckets),
            "learned_operator_count": len(self.operators),
            "min_support_tasks": self.min_tasks,
        }
        return list(self.operators)

    def apply(self, operator_name, concrete_expression_tree, x):
        operator = next((op for op in self.operators if op.name == operator_name), None)
        if operator is None:
            raise KeyError(operator_name)
        params = operator.bind(concrete_expression_tree)
        return operator.execute(x, params)

    def manifest(self):
        return [{
            "name": op.name,
            "expression": op.expression,
            "parameter_count": op.parameter_count,
            "source_tasks": list(op.source_tasks),
        } for op in self.operators]
