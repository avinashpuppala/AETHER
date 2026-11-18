# AETHER supplied-project audit and build decision

## Files inspected

The supplied ZIP contains 41 files. It includes the AETHER 5.0, 5.1 and 5.2
research layers, arithmetic primitive discovery, hierarchy, evolution,
counterexample refinement, self-repair demonstrations and unit tests.

The original AETHER 1–4 source tree is not included. The supplied README says
the extension is not merged into that original source tree, so this audit does
not claim to validate the complete historical codebase.

## Reproduced test result

Command:
`python -m unittest discover -s tests -v`

Result:
`Ran 41 tests ... OK`

The 41 passing tests establish that the supplied test suite passes in this
environment. They do not establish general intelligence or benchmark
superiority.

## What AETHER 5.2 actually does

The 5.2 learner receives a frozen parameterized AST, enumerates finite integer
parameter assignments, selects an input that minimizes expected remaining
hypotheses, incorporates an external input/output observation, and verifies
the inferred parameter on disjoint test inputs.

The demo's candidate is `x² + p`; the synthetic oracle returns `x² + 9`.
The selected input is `x = 0`, which directly exposes the parameter. The demo
then passes three independent test examples.

This is active parameter identification inside a fixed arithmetic template.
It is not open-ended program invention.

## New research core added

`AETHER_Discovery_Core/` adds bounded whole-program enumeration over a small
arithmetic grammar. It actively chooses oracle queries to filter complete
program hypotheses rather than only parameter assignments within one frozen
template. It uses a safe AST interpreter, explicit search budgets and
independent tests.

The demonstration target is `x² + 3`, supplied only through a synthetic
oracle. The core finds a representative program and reports multiple
observationally equivalent survivors when the finite evidence cannot
distinguish their syntax.

## Decision

Preserve the existing AETHER code as a baseline. Develop the discovery core
as a separate research track, then integrate the strongest verified
abstractions only after matched benchmark results.

Do not market the current code as AGI, a frontier model, or a proven
breakthrough. The first credible public claim should be a reproducible result
on an independent benchmark against strong baselines.
