import os
import sys

import pandas as pd
from qiskit import QuantumCircuit, transpile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../compilers/powermove"))

import mvqc_multi_aod as mm
from Construct_Circuit import get_scheduled_blocks

from baselines.powermove_arch import (
    apply_target,
    general_arch_to_powermove_target,
    load_general_arch,
)

STORAGE_ENABLED = True


def _compile_one(benchmark_path: str, target: dict) -> dict:
    circuit = QuantumCircuit.from_qasm_file(benchmark_path)
    n = circuit.num_qubits

    test_circuit = transpile(circuit, basis_gates=["u1", "u2", "u3", "cz", "id"])
    gate_blocks, block_types = get_scheduled_blocks(test_circuit)
    cz_blocks = [b for b, t in zip(gate_blocks, block_types) if t == "CZ"]
    sg_blocks = [b for b, t in zip(gate_blocks, block_types) if t == "SG"]

    apply_target(target, mm)

    (
        transfer_duration,
        movement_duration,
        cir_fidelity,
        cir_fidelity_1q_gate,
        cir_fidelity_2q_gate,
        cir_fidelity_2q_gate_for_idle,
        cir_fidelity_atom_transfer,
        cir_fidelity_coherence,
        num_movement_stage,
    ) = mm.mvqc(cz_blocks, target["grid_rows"], n, STORAGE_ENABLED, target["num_aods"], sg_blocks=sg_blocks)

    return {
        "nqubits": n,
        "total_fidelity": cir_fidelity,
        "total_coherence_fidelity": cir_fidelity_coherence,
        "total_transfer_fidelity": cir_fidelity_atom_transfer,
        "total_2q_on_idle": cir_fidelity_2q_gate_for_idle,
        "total_2q_gate_fidelity": cir_fidelity_2q_gate,
        "total_1q_gate_fidelity": cir_fidelity_1q_gate,
        "cir_duration": transfer_duration + movement_duration,
        "num_movement_stage": num_movement_stage,
    }


def run_powermove_single_benchmarks(benchmark_file: str, arch_spec_path: str, output_file: str):
    """
    Compile a single QASM circuit with PowerMove against a fixed target derived
    from `arch_spec_path` (a ZAC-style general_arch.json). Mirrors
    run_zac_single_benchmarks so results/powermove/e2e_results.csv lines up
    row-for-row with results/zac/e2e_results.csv.
    """
    arch = load_general_arch(arch_spec_path)
    target = general_arch_to_powermove_target(arch)

    filename = os.path.join("data/benchmarks", benchmark_file)
    benchmark = benchmark_file.split("/")[-1]

    print("==============================================")
    print(
        f"Compile circuit {benchmark_file} with PowerMove "
        f"(grid {target['grid_rows']}x{target['grid_cols']}, {target['num_aods']} AOD(s))"
    )

    metrics = _compile_one(filename, target)

    data = pd.DataFrame(
        columns=[
            "benchmark",
            "nqubits",
            "total_fidelity",
            "total_coherence_fidelity",
            "total_transfer_fidelity",
            "total_2q_on_idle",
            "total_2q_gate_fidelity",
            "total_1q_gate_fidelity",
            "cir_duration",
            "num_movement_stage",
        ]
    )

    data.loc[len(data)] = [
        benchmark.split(".")[0],
        metrics["nqubits"],
        metrics["total_fidelity"],
        metrics["total_coherence_fidelity"],
        metrics["total_transfer_fidelity"],
        metrics["total_2q_on_idle"],
        metrics["total_2q_gate_fidelity"],
        metrics["total_1q_gate_fidelity"],
        metrics["cir_duration"],
        metrics["num_movement_stage"],
    ]

    if not os.path.isfile(output_file):
        data.to_csv(output_file, index=False)
    else:
        data.to_csv(output_file, mode="a", header=False, index=False)
