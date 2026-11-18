# AETHER next research layer: results and limits

## Implemented
- Added `abstraction_miner.py`, which mines parameterized subprogram patterns
  shared by multiple solved task programs.
- Learned abstractions are executable and can bind parameters from a matching
  concrete expression tree.
- Added `abstraction_demo.py` and seven focused regression tests.
- Preserved the supplied AETHER 5.2 project in `aether_v5/`.

## Results
- New discovery-core test suite: 14/14 passed.
- Original AETHER 5.2 test suite: 41/41 passed (see package run record if present).
- Demo: mined `(abs(x) + $p1)` from three source programs; bound p1=7 in a
  separate target expression; four held-out input checks passed.

## Critical boundary
This layer mines reusable parameterized patterns from already available
program ASTs. It does not infer the target expression from black-box examples,
invent primitive semantics outside the existing arithmetic grammar, or prove
cross-domain intelligence. The target expression tree is used to bind the
parameter in the demo. The next research step is to connect black-box whole-
program synthesis to macro discovery while preventing target-program leakage.
