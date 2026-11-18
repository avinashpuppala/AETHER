# AETHER Discovery Core

This is a new research core added alongside the supplied AETHER 5.2 project.
The original project is preserved unchanged under `aether_v5/`. This is not
presented as a new numbered release.

## What this core adds

The supplied AETHER 5.2 learner receives a frozen parameterized expression
and actively chooses inputs to identify its unknown parameters.

This core takes a step beyond that setup: it enumerates complete candidate
programs from a bounded grammar, chooses informative oracle queries to
eliminate candidate programs, and checks the surviving candidates on disjoint
test inputs.

### Current grammar

- Variable: `x`
- Integer constants: configurable (default `-2, -1, 0, 1, 2, 3`)
- Unary operators: negation, absolute value, square
- Binary operators: addition, subtraction, multiplication

The search is bounded by expression node count and a candidate budget.
Execution uses a small explicit AST interpreter; it does not use `eval` or
`exec`.

## Run on Windows 11

From this folder:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m unittest discover -s tests -v
python demo.py
```

Python 3.10+; standard library only; CPU-only.

## Demonstration

The demo uses a synthetic external oracle for `x² + 3`. The learner does not
receive the target expression. It selects an informative input, filters the
finite program hypothesis set, and checks disjoint test inputs.

Multiple syntactically different programs may be observationally equivalent
on the available tests. The report therefore distinguishes a verified
equivalence set from a uniquely identified program.

## Research boundaries

This is a bounded program-synthesis baseline, not an autonomous general
intelligence system. A successful run means only that at least one program in
the configured grammar matches the supplied finite observations and tests.
It does not prove correctness for all inputs, discover arbitrary operators,
or establish superiority over existing AI systems.

The next research gates are:
1. Add dynamic grammar/operator invention rather than a fixed operator set.
2. Integrate reusable abstractions from the supplied macro/evolution engine.
3. Add sandboxed execution, time/memory limits and provenance for generated code.
4. Evaluate on independent benchmarks such as CodeARC and compare with strong
   synthesis baselines under matched query and compute budgets.
5. Run ablations to establish whether active query selection and abstraction
   reuse contribute measurable gains.

## Related research to compare against

- Program Synthesis via Test-Time Transduction, NeurIPS 2025:
  https://proceedings.neurips.cc/paper_files/paper/2025/hash/35678513540026a9e3bf0d49d7e6f624-Abstract-Conference.html
- CodeARC, COLM 2025:
  https://arxiv.org/abs/2503.23145
- AlphaEvolve, 2025:
  https://arxiv.org/abs/2506.13131

These are related prior work, not evidence that this implementation is novel.


## Next research layer: cross-task abstraction mining

`abstraction_miner.py` mines parameterized reusable subprograms that occur
across multiple solved task programs. It replaces numeric constants with
parameter slots, requires support from multiple distinct tasks, and registers
an executable operator. `abstraction_demo.py` demonstrates mining
`abs(x) + p` from three source programs and applying it to another program.

Run:
```powershell
python -m unittest discover -s tests -v
python abstraction_demo.py
```

Research boundary: this is abstraction mining inside the existing fixed
arithmetic DSL. In the transfer demo, the target expression tree is used to
bind the unknown constant, so it is not black-box target discovery. The next
harder milestone is to combine black-box synthesis with abstraction mining
without exposing target programs, and to compare against matched baselines.
