"""Task ingestion and structural analysis for the bounded AETHER arithmetic DSL."""
from dataclasses import dataclass
from aether_primitive_discovery import _parse_expr, size
from aether_advanced import _walk, _skeleton

@dataclass(frozen=True)
class Task:
    name: str
    domain: str
    expression: str
    tree: tuple
    split: str = "train"

class TaskAnalyzer:
    def __init__(self):
        self.tasks = {}

    def add(self, name: str, expression: str, domain: str = "arithmetic", split: str = "train"):
        if not name or not name.strip():
            raise ValueError("Task name cannot be empty.")
        if split not in ("train", "heldout"):
            raise ValueError("split must be train or heldout")
        if name in self.tasks:
            raise ValueError(f"Duplicate task name: {name}")
        tree = _parse_expr(expression)
        self.tasks[name] = Task(name, domain, expression, tree, split)
        return self.tasks[name]

    def inventory(self, min_subtree_size=2):
        rows = []
        for task in self.tasks.values():
            shapes = {}
            for node in _walk(task.tree):
                if size(node) >= min_subtree_size:
                    key = repr(_skeleton(node))
                    shapes[key] = shapes.get(key, 0) + 1
            rows.append({
                "task": task.name,
                "domain": task.domain,
                "split": task.split,
                "expression_size": size(task.tree),
                "eligible_subtree_shapes": len(shapes),
            })
        return rows
