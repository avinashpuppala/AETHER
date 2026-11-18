"""Independent held-out validation of invented patterns."""
from aether_advanced import _walk, _skeleton
from aether_primitive_discovery import evaluate, size

class HeldOutValidator:
    def __init__(self, probes=(-17, -5, -1, 0, 2, 9, 23)):
        if not probes:
            raise ValueError("At least one held-out probe is required.")
        self.probes = tuple(probes)

    def validate_candidate(self, candidate, heldout_tasks):
        # Validation asks whether a candidate's structural pattern appears in
        # a task not used for invention, then checks the matched subtree on
        # independent x probes. The template itself is not refit.
        template_shape = _template_skeleton(candidate["tree"])
        matches = []
        for task in heldout_tasks:
            for subtree in _walk(task.tree):
                if _skeleton(subtree) != template_shape:
                    continue
                # Reconstruct candidate with the parameter values captured by
                # matching the invented template against this held-out subtree.
                captures = {}
                if not _capture(candidate["tree"], subtree, captures):
                    continue
                params = tuple(captures[i] for i in range(candidate["parameter_count"]))
                checks = []
                for x in self.probes:
                    expected = evaluate(subtree, x)
                    predicted = _evaluate_template(candidate["tree"], x, params)
                    checks.append(expected == predicted)
                matches.append({
                    "task": task.name, "domain": task.domain,
                    "passed": sum(checks), "total": len(checks),
                    "verified": all(checks),
                    "subtree_size": size(subtree),
                })
                break
        return {
            "candidate": candidate["name"],
            "heldout_task_count": len(heldout_tasks),
            "matched_task_count": len(matches),
            "verified_matches": sum(m["verified"] for m in matches),
            "results": matches,
        }

def _capture(template, concrete, captures):
    if template[0] == "param":
        if concrete[0] != "const":
            return False
        slot, value = template[1], concrete[1]
        if slot in captures and captures[slot] != value:
            return False
        captures[slot] = value
        return True
    if template[0] != concrete[0]:
        return False
    if template[0] in ("x", "const"):
        return template == concrete
    from aether_advanced import _children
    a, b = _children(template), _children(concrete)
    return len(a) == len(b) and all(_capture(x, y, captures) for x, y in zip(a, b))

def _evaluate_template(node, x, params):
    kind = node[0]
    if kind == "x": return x
    if kind == "const": return node[1]
    if kind == "param": return params[node[1]]
    if kind == "neg": return -_evaluate_template(node[1], x, params)
    if kind == "abs": return abs(_evaluate_template(node[1], x, params))
    if kind == "square":
        v = _evaluate_template(node[1], x, params); return v*v
    a = _evaluate_template(node[1], x, params)
    b = _evaluate_template(node[2], x, params)
    return {"add":a+b, "sub":a-b, "mul":a*b}[kind]


def _template_skeleton(node):
    if node[0] == "param":
        return ("const",)
    if node[0] in ("x", "const"):
        return (node[0],)
    from aether_advanced import _children
    return (node[0], *(_template_skeleton(child) for child in _children(node)))
