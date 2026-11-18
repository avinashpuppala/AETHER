"""Bounded anti-unification search that invents scored parameterized primitives."""
from itertools import combinations, product
from aether_advanced import _walk, _skeleton, _parameterize_group, _render_template
from aether_primitive_discovery import size

class PrimitiveInventor:
    def __init__(self, max_combinations=20000, min_support=2, min_size=2):
        if max_combinations < 1 or min_support < 2:
            raise ValueError("Search budget must be positive and min_support >= 2.")
        self.max_combinations = max_combinations
        self.min_support = min_support
        self.min_size = min_size
        self.stats = {}

    def invent(self, tasks):
        # Index eligible subtrees by operator skeleton, retaining at most one
        # occurrence of each structurally distinct subtree per task.
        buckets = {}
        for task in tasks:
            if getattr(task, "split", "train") != "train":
                continue
            per_shape = {}
            for node in _walk(task.tree):
                if size(node) < self.min_size:
                    continue
                per_shape.setdefault(repr(_skeleton(node)), []).append(node)
            for shape, nodes in per_shape.items():
                # Deduplicate exact trees while preserving deterministic order.
                unique = {repr(n): n for n in nodes}
                buckets.setdefault(shape, {})[task.name] = list(unique.values())

        found = {}
        examined = 0
        exhausted = False
        for shape in sorted(buckets):
            task_map = buckets[shape]
            names = sorted(task_map)
            if len(names) < self.min_support:
                continue
            for count in range(self.min_support, len(names) + 1):
                for chosen_names in combinations(names, count):
                    pools = [task_map[n] for n in chosen_names]
                    for nodes in product(*pools):
                        examined += 1
                        if examined > self.max_combinations:
                            exhausted = True
                            break
                        try:
                            template, parameter_rows = _parameterize_group(nodes)
                        except ValueError:
                            continue
                        if not any(v[0] == "param" for v in _walk(template)):
                            continue
                        key = repr(template)
                        item = found.setdefault(key, {
                            "tree": template, "tasks": set(), "domains": set(),
                            "parameter_rows": set(),
                        })
                        item["tasks"].update(chosen_names)
                        item["domains"].update(
                            next(t.domain for t in tasks if t.name == n)
                            for n in chosen_names
                        )
                        item["parameter_rows"].update(tuple(row) for row in parameter_rows)
                    if exhausted: break
                if exhausted: break
            if exhausted: break

        candidates = []
        for index, item in enumerate(found.values(), 1):
            tree = item["tree"]
            support = len(item["tasks"])
            domains = len(item["domains"])
            # Compression proxy: number of repeated AST nodes saved by replacing
            # each occurrence with a call + parameter arguments.
            node_count = size(tree)
            parameter_count = max((n[1] + 1 for n in _walk(tree) if n[0] == "param"), default=0)
            per_use_saving = max(0, node_count - (1 + parameter_count))
            compression_gain = per_use_saving * max(0, support - 1)
            # Prefer useful, compact, multi-task abstractions. Domain diversity
            # is a bonus, not a claim of semantic cross-domain intelligence.
            score = (compression_gain * 2) + support + (domains - 1) * 3 - parameter_count
            candidates.append({
                "name": f"invented_{index:03d}",
                "tree": tree,
                "template": _render_template(tree),
                "parameter_count": parameter_count,
                "support_tasks": sorted(item["tasks"]),
                "domains": sorted(item["domains"]),
                "parameter_rows": [list(v) for v in sorted(item["parameter_rows"])],
                "complexity": node_count,
                "compression_gain": compression_gain,
                "score": score,
            })
        candidates.sort(key=lambda c: (-c["score"], -len(c["support_tasks"]),
                                       c["complexity"], c["template"]))
        self.stats = {
            "candidate_combinations_examined": min(examined, self.max_combinations),
            "unique_candidates": len(candidates),
            "search_budget": self.max_combinations,
            "budget_exhausted": exhausted,
            "min_support": self.min_support,
        }
        return candidates
