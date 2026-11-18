from __future__ import annotations
from dataclasses import dataclass
from itertools import product
from typing import Sequence, Iterable
import ast
import json
import re

@dataclass(frozen=True)
class Example:
    x: int
    y: int

@dataclass(frozen=True)
class Candidate:
    expression: str
    complexity: int
    predictions: tuple[int, ...]

@dataclass(frozen=True)
class Primitive:
    name: str
    template: str
    support_tasks: tuple[str, ...]
    description: str

def evaluate(node, x):
    k = node[0]
    if k == "x": return x
    if k == "const": return node[1]
    if k == "neg": return -evaluate(node[1], x)
    if k == "abs": return abs(evaluate(node[1], x))
    if k == "square":
        v = evaluate(node[1], x); return v * v
    a, b = evaluate(node[1], x), evaluate(node[2], x)
    if k == "add": return a + b
    if k == "sub": return a - b
    if k == "mul": return a * b
    raise ValueError(k)

def render(n):
    k = n[0]
    if k == "x": return "x"
    if k == "const": return str(n[1])
    if k == "neg": return f"(-{render(n[1])})"
    if k == "abs": return f"abs({render(n[1])})"
    if k == "square": return f"({render(n[1])} ** 2)"
    op = {"add":"+","sub":"-","mul":"*"}[k]
    return f"({render(n[1])} {op} {render(n[2])})"

def size(n):
    return 1 if n[0] in ("x","const") else 1 + sum(size(c) for c in n[1:] if isinstance(c, tuple))

def enumerate_nodes(max_depth=2, constants=(-2,-1,0,1,2), limit=100000):
    base = [("x",)] + [("const", c) for c in constants]
    seen = {repr(n) for n in base}
    yield from base
    prev = base
    emitted = len(base)
    for _ in range(max_depth):
        cur = []
        for a in prev:
            cur.extend([("neg",a),("abs",a),("square",a)])
        pool = base + prev
        for a,b in product(pool, repeat=2):
            cur.extend([("add",a,b),("sub",a,b),("mul",a,b)])
        fresh = []
        for n in cur:
            key = repr(n)
            if key not in seen and size(n) <= 9:
                seen.add(key); fresh.append(n)
                emitted += 1
                if emitted >= limit: break
        yield from fresh
        prev = fresh
        if emitted >= limit: break

class BoundedProgramSynthesizer:
    def __init__(self, max_depth=2, constants=(-2,-1,0,1,2), max_candidates=100000):
        self.max_depth, self.constants, self.max_candidates = max_depth, tuple(constants), max_candidates
    def solve(self, examples: Sequence[Example]):
        if len(examples) < 2: raise ValueError("At least two examples are required.")
        if len({e.x for e in examples}) != len(examples): raise ValueError("Inputs must be unique.")
        target = tuple(e.y for e in examples)
        matches = {}
        for i,n in enumerate(enumerate_nodes(self.max_depth,self.constants,self.max_candidates)):
            if i >= self.max_candidates: break
            try: out = tuple(evaluate(n,e.x) for e in examples)
            except (OverflowError, ValueError): continue
            if any(abs(v)>10**9 for v in out): continue
            if out == target:
                c = Candidate(render(n),size(n),out)
                if out not in matches or c.complexity < matches[out].complexity: matches[out]=c
        return sorted(matches.values(), key=lambda c:(c.complexity,len(c.expression),c.expression))

def _parse_expr(expr: str):
    """Parse only the arithmetic DSL emitted by this module."""
    tree = ast.parse(expr, mode="eval")
    def convert(n):
        if isinstance(n, ast.Expression): return convert(n.body)
        if isinstance(n, ast.Name) and n.id == "x": return ("x",)
        if isinstance(n, ast.Constant) and isinstance(n.value, int) and not isinstance(n.value, bool):
            return ("const", n.value)
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.USub): return ("neg", convert(n.operand))
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "abs" and len(n.args)==1:
            return ("abs", convert(n.args[0]))
        if isinstance(n, ast.BinOp):
            if isinstance(n.op, ast.Pow) and isinstance(n.right, ast.Constant) and n.right.value == 2:
                return ("square", convert(n.left))
            ops = {ast.Add:"add", ast.Sub:"sub", ast.Mult:"mul"}
            for typ, name in ops.items():
                if isinstance(n.op, typ): return (name, convert(n.left), convert(n.right))
        raise ValueError("Expression contains an unsupported operation.")
    return convert(tree)

def _template_and_values(node):
    """Turn numeric constants into parameter slots, except the fixed square exponent."""
    values = []
    def walk(n):
        if n[0] == "const":
            slot = len(values)
            values.append(n[1])
            return ("param", slot)
        if n[0] in ("x",): return n
        if n[0] in ("neg","abs","square"): return (n[0], walk(n[1]))
        return (n[0], walk(n[1]), walk(n[2]))
    return walk(node), tuple(values)

def _render_template(n):
    if n[0] == "param": return f"$p{n[1]+1}"
    if n[0] == "x": return "x"
    if n[0] == "neg": return f"(-{_render_template(n[1])})"
    if n[0] == "abs": return f"abs({_render_template(n[1])})"
    if n[0] == "square": return f"({_render_template(n[1])} ** 2)"
    op={"add":"+","sub":"-","mul":"*"}[n[0]]
    return f"({_render_template(n[1])} {op} {_render_template(n[2])})"

def _eval_template(n, x, params):
    k=n[0]
    if k=="x": return x
    if k=="param":
        if n[1] not in params: raise ValueError(f"Missing parameter p{n[1]+1}")
        return params[n[1]]
    if k=="const": return n[1]
    if k=="neg": return -_eval_template(n[1],x,params)
    if k=="abs": return abs(_eval_template(n[1],x,params))
    if k=="square":
        v=_eval_template(n[1],x,params); return v*v
    a,b=_eval_template(n[1],x,params),_eval_template(n[2],x,params)
    return {"add":lambda:a+b,"sub":lambda:a-b,"mul":lambda:a*b}[k]()

@dataclass
class ExecutablePrimitive:
    name: str
    tree: tuple
    parameter_values: tuple[int, ...]
    source_expressions: tuple[str, ...]

    @property
    def template(self): return _render_template(self.tree)
    def execute(self, x: int, parameters: Sequence[int] | None = None) -> int:
        values = tuple(parameters) if parameters is not None else self.parameter_values
        if len(values) != self.parameter_count: raise ValueError("Incorrect parameter count.")
        return _eval_template(self.tree, x, {i:v for i,v in enumerate(values)})
    @property
    def parameter_count(self):
        def count(n):
            if n[0]=="param": return 1
            return sum(count(c) for c in n[1:] if isinstance(c,tuple))
        return count(self.tree)
    def to_dict(self):
        return {"name":self.name,"template":self.template,"parameter_values":self.parameter_values,
                "source_expressions":self.source_expressions}

def invent_parameterized_primitive(expressions: Sequence[str], name="learned_primitive"):
    """Infer a common expression skeleton from expressions with different constants."""
    if len(expressions)<2: raise ValueError("Need at least two expressions to infer varying parameters.")
    parsed=[_parse_expr(e) for e in expressions]
    templates=[]; values=[]
    for node in parsed:
        t,v=_template_and_values(node); templates.append(t); values.append(v)
    if any(t != templates[0] for t in templates[1:]):
        raise ValueError("Expressions do not share the same structural skeleton.")
    if any(len(v)!=len(values[0]) for v in values):
        raise ValueError("Parameter counts differ.")
    # A parameter must vary across source expressions; otherwise this is just a constant template.
    if not any(len({v[i] for v in values})>1 for i in range(len(values[0]))):
        raise ValueError("No varying parameter was inferred.")
    return ExecutablePrimitive(name,templates[0],values[0],tuple(expressions))

def infer_parameters_for_task(primitive: ExecutablePrimitive, support: Sequence[Example]):
    """Find parameter values consistent with all support examples, using bounded brute force."""
    if not support: raise ValueError("At least one support example is required.")
    if primitive.parameter_count != 1:
        raise NotImplementedError("This milestone currently supports one inferred parameter.")
    candidates=set(range(-100,101))
    for ex in support:
        candidates={p for p in candidates if _eval_template(primitive.tree,ex.x,{0:p})==ex.y}
    if len(candidates)!=1:
        raise ValueError(f"Parameter inference is not unique; candidates={sorted(candidates)}")
    return (next(iter(candidates)),)

def verify_primitive(primitive: ExecutablePrimitive, parameters: Sequence[int],
                     held_out: Sequence[Example]):
    if not held_out: raise ValueError("At least one held-out example is required.")
    checks=[primitive.execute(e.x,parameters)==e.y for e in held_out]
    return {"verified":all(checks),"passed":sum(checks),"total":len(checks),
            "predictions":[primitive.execute(e.x,parameters) for e in held_out]}

class PrimitiveLibrary:
    def __init__(self): self.records={}
    def add_verified_task(self, task_name: str, candidates: Iterable[Candidate]):
        if not task_name.strip(): raise ValueError("task_name cannot be empty")
        for c in candidates: self.records.setdefault(c.expression,set()).add(task_name)
    def mine(self,min_tasks=2):
        grouped={}
        for expr,tasks in self.records.items():
            try: template,_=_template_and_values(_parse_expr(expr))
            except (SyntaxError,ValueError): continue
            key=_render_template(template)
            grouped.setdefault(key,set()).update(tasks)
        return [Primitive(f"primitive_{i}",template,tuple(sorted(tasks)),
                          f"Recurring parameterized structure across {len(tasks)} tasks.")
                for i,(template,tasks) in enumerate(sorted(grouped.items()),1) if len(tasks)>=min_tasks]

def run_transfer_demo():
    # Two source tasks reveal x^2 + p. A third task is withheld from primitive invention.
    primitive=invent_parameterized_primitive(["(1 + (x ** 2))","(2 + (x ** 2))"],"square_plus_parameter")
    support=[Example(-3,12),Example(0,3),Example(2,7)]
    held_out=[Example(-5,28),Example(4,19)]
    inferred=infer_parameters_for_task(primitive,support)
    verification=verify_primitive(primitive,inferred,held_out)
    return {"primitive":primitive.to_dict(),"new_task_inferred_parameters":inferred,
            "held_out_verification":verification}

if __name__=="__main__":
    print(json.dumps(run_transfer_demo(),indent=2))
