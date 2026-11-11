# Baseline compilers

This directory contains the baseline compilers used in the evaluation.
They are included as plain copies of the upstream code (no git submodules), so that the artifact is self-contained.
Files that the evaluation does not use (examples, notebooks, upstream benchmarks and results) were removed.

| Compiler | Upstream | Version | License | Modifications |
|---|---|---|---|---|
| ZAC | <placeholder: upstream URL> | <placeholder: commit> | BSD-3-Clause (`zac/LICENSE`) | Added `pyproject.toml` to install it with uv |
| PachinQo | <placeholder: upstream URL> | <placeholder: commit> | <placeholder> | Added `pyproject.toml` to install it with uv |
| PowerMove | <placeholder: upstream URL> | <placeholder: commit> | No license file upstream | See below |
| ZAP | <placeholder: upstream URL> | <placeholder: commit> | MIT (`zap/LICENSE`) | Decoherence term computed with `math.exp` in `zap/zap/simulator.py` |
| Atomique (FPQA-C) | <placeholder: upstream URL> | <placeholder: commit> | <placeholder> | Driver script (`driver.py`) to run it as a subprocess |

QMAP is installed from PyPI (`mqt-qmap==3.8.0`, see `pyproject.toml`).

## PowerMove modifications

The execution time and fidelity model of PowerMove was changed to match the model used for MultiQ and the other baselines:

- Single-qubit gate layers are extracted from the circuit (`get_sg_blocks` in `Construct_Circuit.py`) and included in the execution time and fidelity.
- Decoherence is computed as `exp(-t / T2)` in `mvqc_multi_aod.py`.

<placeholder: other modifications, for example the CZ block changes in `Construct_Circuit.py`>
