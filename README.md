# AETHER — Research Preview v0.1

**An experimental, CPU-friendly prototype for bounded program discovery and cross-task abstraction mining.**

AETHER explores how small programs can be synthesized from examples, validated against held-out inputs, and generalized into reusable parameterized operators. This is an early research prototype—not a general-purpose AI system, an AGI system, or a demonstrated replacement for existing models.

## What is included

- `AETHER_Discovery_Core/`: bounded arithmetic program synthesis, query-driven discovery, and cross-task abstraction mining.
- `aether_v5/`: earlier AETHER research prototypes and tests.
- `AETHER_AUDIT_AND_DECISION.md`: scope and audit notes.
- `AETHER_NEXT_LAYER_RESULTS.md`: results and limitations of the abstraction-mining layer.

## Requirements

- Python 3.10 or newer
- No third-party packages required for the included core demos/tests

## Quick start (Windows PowerShell)

```powershell
cd AETHER_Discovery_Core
python -m unittest discover -s tests -v
python demo.py
python abstraction_demo.py
```

Run the earlier prototype tests from the `aether_v5` folder:

```powershell
cd ..\aether_v5
python -m unittest discover -s tests -v
```

Verified in this packaging run: 14/14 discovery-core tests passed and 41/41 earlier prototype tests passed.

## Current demonstrated capabilities

1. Search within a fixed, bounded arithmetic expression grammar.
2. Use example queries to narrow candidate programs.
3. Validate candidate programs on held-out inputs.
4. Mine parameterized macro patterns shared by multiple supplied task programs.

## Important limitations

- The discovery grammar is deliberately small and fixed.
- The abstraction miner operates on solved/source ASTs supplied to it; it does not infer arbitrary hidden programs from raw I/O alone.
- Learned abstractions are parameterized macros over existing operations, not newly discovered mathematical primitives.
- Passing the included tests does not establish superiority over AlphaEvolve, FunSearch, or other research systems.

## Reproducibility

Run the commands above and retain the complete console output with your environment details. Report failures as well as successes. Do not describe the included tests as an independent benchmark.

## Project status

**Research Preview v0.1 — 18 November 2026**

Contributions, bug reports, and independent replication attempts are welcome. Please include Python version, operating system, exact command, and full error output.
