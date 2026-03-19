# MultiQ Compiler Backend

MultiQ is an advanced multiprogramming-enabled compiler backend for the **Neutral-Atom Quantum Computing Architecture** (such as dynamic Acousto-Optic Deflector (AOD) tweeser array structures). It ingests multiple quantum circuits, evaluates optimal architecture topologies, lowers them into discrete execution tiles, and coordinates parallel compilation workflows featuring grid allocations, scheduling atom movements, fidelity analysis, and trajectory modeling.

This is the artifact of the paper: [MultiQ: Multi-Programming Neutral Atom Quantum Architectures](https://arxiv.org/abs/2601.08504)

---

## 🚀 Key Features

* **Multi-Circuit Spatial/Temporal Batching:** Merges circuits into dense batch containers to maximize parallel hardware usage efficiency.
* **Neutral Atom Grid Modeling:** Accounts for realistic trapping grid heights, AOD deflector layouts, storage-site and entanglement-site zone dimensions.
* **Full Compilation Pipeline:**
  * **Planner & Placements:** Arranges qubit allocations across static/dynamic sites.
  * **Scheduler:** Coordinates parallel gate lowers and transport layouts (ASAP execution windows).
  * **Orchestrator:** High-level controller orchestrating lowered grid assembly workflows into unified trace files.
* **Simulation & Equivalency Checking:**
  * **MQT-QCEC Enabled Verification:** Re-compiles lowered `ZAIR` trace states back to `Qiskit` circuits for equivalence compliance metrics correctly.
  * **Noise Density Fidelity Simulations:** Profiles gate vectors for atom transfer, 1q/2q state transitions thresholds.
* **Visual Animator Mode:** Creates dynamic visualization/animations to trace physical execution motion cycles correctly.

---

## 🛠️ Installation

MultiQ manages dependencies and virtual environments with [PDM](https://pdm-project.org/).

1. **Install PDM** (if you haven't already):
   ```bash
   pip install pdm
   ```

2. **Install Project Dependencies**:
   ```bash
   # From the project root directory
   pdm install
   ```

---

## 📖 Getting Started

### High-Level Compilation API

You can trigger the MultiQ grid batch solver directly using the `MultiQ` controller class:

```python
from multiq.multiq import MultiQ

# 1. Initialize with an E2E Hardware Arrangement configuration
multiq = MultiQ(config_file="config/multiq/e2e_config.yaml")

# 2. Add source circuits (e.g., .qasm or loaded QuantumCiruits indices)
input_circuits = ["data/benchmarks/example_circ1.qasm", "data/benchmarks/example_circ2.qasm"]

# 3. Trigger batching & Tile orchestrations
output_traces = multiq.set_inputs(input_circuits)

print(f"Lowered profiles generated at: {output_traces}")
```

---

## 📂 Project Architecture

```text
MultiQ/
├── src/multiq/
│   ├── compiler/          # Operations backend (orchestrator, planner, placement, scheduler)
│   ├── animator/          # Interactive execution animations and visualizer lowers
│   ├── checker.py         # ZAIR-to-Circuit builders & equivalence verification (MQT QCEC)
│   ├── simulator.py       # Pulse thresholds and fidelity execution simulators
│   └── types/             # Common models for tiling and transport allocations
├── config/
│   ├── multiq/            # Global/default E2E controller setup (e.g., e2e_config.yaml)
│   └── zac/               # Subsystem architecture weights and JSON bounds
├── scripts/
│   ├── baselines/         # Execution scripts supporting solver comparisons
│   ├── plotting/          # Evaluation report chart generations
│   └── run_evaluation.py  # Main workflow setup for grid evaluators benchmarks
├── data/                  # Source benchmarking circuits
└── figures/               # Layout files and benchmarks outcomes visualizations
```

---

## 🔧 Dev Specifications

Formattings & lint-check styles adhere to Black specifications for clean consistency checks. To maintain code styles:
```bash
pdm run black src/
```

## 📄 License
This package is licensed under the terms of the MIT License, as disclosed inside `pyproject.toml`.
