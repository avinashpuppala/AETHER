# AETHER — Executable Parameterized Primitive Discovery

This research extension builds on the earlier standalone primitive-discovery
package. It is not merged into the original `aether_research_engine` source tree,
which has not been uploaded for inspection.

## Run on Windows 11
```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m unittest discover -s tests -v
python aether_primitive_discovery.py
```
Python 3.10+, standard library only, CPU-only.

## New capability
- Infers a shared expression skeleton from multiple discovered expressions.
- Converts differing constants into parameter slots.
- Executes the parameterized primitive using a safe AST interpreter (no `eval`).
- Infers one task parameter from support examples.
- Checks predictions on separate held-out examples.
- Rejects inconsistent held-out behavior.

## Demonstration
Source discoveries: `x² + 1` and `x² + 2`.
The system infers the template `x² + p`.
A separate task's support examples imply `p = 3`.
Held-out examples then test whether that inferred primitive transfers.

## Limitations
- Current parameter inference supports one parameter only.
- Primitive invention requires at least two source expressions with the same
  arithmetic structure.
- The DSL is bounded to integer arithmetic, `abs`, negation, addition,
  subtraction, multiplication, and square.
- This is not general intelligence and does not establish broad cross-domain
  transfer. It is a controlled experiment for reusable executable primitives.


## Next milestone: hierarchical primitive reuse
New module `aether_hierarchy.py`:
- mines repeated nontrivial subtrees from multiple solved expressions;
- stores them as reusable named macros;
- rewrites later expressions to call those macros;
- executes the composed expression and checks independent probes.

Run:
```powershell
python -m unittest discover -s tests -v
python aether_hierarchy.py
```

This is bounded symbolic macro discovery and reuse, not unrestricted autonomous
reasoning. Current macro matching is exact-subtree matching; parameterized
macro-pattern matching is a future research step.

## Advanced milestone: parameterized hierarchical discovery
Module `aether_advanced.py` extends the hierarchy with:
- anti-unification of same-shaped subtrees across independent tasks;
- parameter slots for differing constants, including tied/repeated parameters;
- safe matching and execution of discovered parameterized macros;
- independent semantic checks against the original expression, recording counterexamples;
- bounded candidate-combination search and JSON save/load of the learned library.

Run the complete suite and demo:
```powershell
python -m unittest discover -s tests -v
python aether_advanced.py
```

This is still a bounded arithmetic-DSL research system. The counterexample check
validates macro substitution against the original expression; it does not yet
implement an unbounded learner that changes its grammar from counterexamples.

## Evolution milestone: nested abstraction and counterexample refinement
New module `aether_evolution.py` adds:
- nested macro compilation, where a larger learned macro can call smaller learned macros;
- an explicit macro dependency graph;
- counterexample-driven conservative refinement by quarantining implicated macros while retaining them for audit;
- persistent evolution history and quarantine state;
- held-out transfer evaluation across separate arithmetic task families;
- an optional bounded enumerative-search baseline for comparative evaluation.

Run all tests:
```powershell
python -m unittest discover -s tests -v
```

Run the nested-abstraction demonstration:
```powershell
python aether_evolution.py
```

Run the transfer benchmark against the bounded symbolic-search baseline:
```powershell
python run_evolution_benchmark.py
```

Research boundary: this is still a controlled integer-arithmetic DSL. Counterexample refinement currently quarantines implicated macros; it does not yet synthesize a replacement grammar or prove optimality. The symbolic baseline is bounded enumerative search, not a universal theorem prover. Benchmark conclusions apply only to the listed held-out families and budgets.


## Self-repair milestone
`AetherEvolutionEngine.repair_from_counterexamples()` adds a bounded repair loop.
It rebuilds candidate macro libraries from the original source tasks under three
discovery settings, checks recorded counterexamples plus source-task probes,
and accepts a replacement only if every check passes. Failed candidates are
rejected without replacing the current library. This is evidence-gated library
reconstruction, not unrestricted self-modifying intelligence or new-operator
discovery.

Run the tests and demo as above; call `repair_from_counterexamples()` after a
failed `verify_composition()` to attempt a conservative repair.


## AETHER 5.0 — scored invention and adversarial validation

The `aether_v5/` package is an incremental research layer over the existing
AETHER code. It does not overwrite the earlier discovery, hierarchy, advanced,
or evolution engines.

New modules:
- `task_analyzer.py`: validates and inventories tasks in the existing safe arithmetic DSL.
- `primitive_inventor.py`: bounded anti-unification over subtrees from multiple tasks,
  with a transparent compression-oriented score and an explicit search budget.
- `counterexample_generator.py`: deterministic adversarial input probes.
- `heldout_validator.py`: checks whether a frozen invented template transfers to
  a held-out task without refitting it.
- `failure_analyzer.py`: reports candidate acceptance and rejection outcomes.
- `engine.py`: orchestrates the above components.

Run:
```powershell
python -m unittest discover -s tests -v
python aether_v5.py
```

Important research boundary:
AETHER 5.0 still operates only on the existing integer arithmetic DSL
(`x`, integer constants, negation, `abs`, square, addition, subtraction,
multiplication). It invents parameterized structural abstractions within that
grammar; it does not invent new operators, learn arbitrary algorithms, or
establish cross-domain intelligence. The held-out checks are finite tests,
not formal proofs. The scoring function is a transparent heuristic and must
be evaluated against stronger baselines before making performance claims.


## AETHER 5.1 — example-only transfer validation

AETHER 5.1 adds `aether_v51/validator.py` and `aether_v51.py`. It addresses an
evaluation weakness in the 5.0 held-out validator: the 5.0 validator reads the
held-out expression tree and captures the unknown constants directly from that
tree. Therefore, its 7/7 result is structural consistency checking, not blind
parameter prediction.

The 5.1 validator receives only:
- a frozen candidate template discovered from training tasks;
- support input/output examples for the target task;
- disjoint test input/output examples.

It searches a finite integer parameter range using support examples only,
requires a unique parameter solution, and then scores the disjoint test set.
It never receives the target expression or AST.

Run:
```powershell
python -m unittest discover -s tests -v
python aether_v51.py
```

Research boundary: this is still bounded parameter inference over the integer
arithmetic DSL. A unique solution is unique only within the configured search
range. Passing finite test examples is not a proof of correctness for all
inputs, and the demo uses a deliberately controlled synthetic task family.


## AETHER 5.2 — active example-only transfer

AETHER 5.2 adds an adaptive query-selection layer in `aether_v52/active_learner.py`.
Instead of receiving a fixed support set, the learner maintains a finite set of
possible integer parameter assignments for a frozen candidate template. It
chooses the next input by minimizing the expected number of hypotheses left
after the output is observed. An external task/oracle supplies the output;
the learner does not receive the target expression or AST.

New behavior:
- selects informative support inputs adaptively;
- eliminates parameter hypotheses using observed input/output pairs;
- stops when the parameter assignment is unique, impossible, or the query
  budget is exhausted;
- requires independent test inputs that do not overlap support inputs;
- reports the finite search bounds, query count, inferred parameters, and
  held-out test outcomes.

Run:
```powershell
python -m unittest discover -s tests -v
python aether_v52.py
```

Research boundary: this is active identification of parameters for a frozen
template in the existing bounded integer arithmetic DSL. It does not invent
new operators or arbitrary algorithms. The demonstration uses a synthetic
oracle. A one-parameter example can be identified with one query because the
chosen template makes the parameter directly observable at `x = 0`; this is
not evidence that all tasks need one query. Results are finite-range,
finite-example evidence, not a proof of general correctness or unrestricted
autonomous intelligence.
