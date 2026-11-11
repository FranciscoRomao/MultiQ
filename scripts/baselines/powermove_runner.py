import os
import sys
import time

import pandas as pd
from qiskit import QuantumCircuit, transpile
from qiskit.qasm2 import dumps

from status import warn

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
    compile_start = time.perf_counter()

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

    compilation_time = time.perf_counter() - compile_start

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
        "compilation_time": compilation_time,
    }


def run_powermove_single_benchmarks(benchmark_file: str, arch_spec_path: str, output_file: str):
    """Compile a single QASM circuit with PowerMove against a target derived from a ZAC-style spec."""
    arch = load_general_arch(arch_spec_path)
    target = general_arch_to_powermove_target(arch)

    filename = os.path.join("data/benchmarks", benchmark_file)
    benchmark = benchmark_file.split("/")[-1]


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
            "compilation_time",
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
        metrics["compilation_time"],
    ]

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    if not os.path.isfile(output_file):
        data.to_csv(output_file, index=False)
    else:
        data.to_csv(output_file, mode="a", header=False, index=False)


def merge_circuits(circuits: list[QuantumCircuit]) -> QuantumCircuit:
    """Concatenate circuits onto disjoint qubit and clbit ranges."""
    assert len(circuits) >= 1, "At least one circuit is required to merge."

    if len(circuits) == 1:
        return circuits[0]

    merged = circuits[0].copy()
    for circuit in circuits[1:]:
        merged_copy = merged.copy()
        total_qubits = merged.num_qubits + circuit.num_qubits
        total_clbits = merged.num_clbits + circuit.num_clbits

        merged = QuantumCircuit(total_qubits, total_clbits)
        merged.compose(
            merged_copy,
            qubits=range(merged_copy.num_qubits),
            clbits=range(merged_copy.num_clbits),
            inplace=True,
        )
        merged.compose(
            circuit,
            qubits=range(merged_copy.num_qubits, total_qubits),
            clbits=range(merged_copy.num_clbits, total_clbits),
            inplace=True,
        )

    return merged


def run_powermove_merge_benchmarks(benchmark_set: list[str], arch_spec_path: str, output_file: str):
    """Merge a benchmark set into one circuit and compile it with PowerMove as a single program."""
    arch = load_general_arch(arch_spec_path)
    target = general_arch_to_powermove_target(arch)

    benchmark_paths = [os.path.join("data/benchmarks", bench) for bench in benchmark_set]
    circuits = [QuantumCircuit.from_qasm_file(bench) for bench in benchmark_paths]
    merged_circuit = merge_circuits(circuits)

    bench = "-".join([os.path.basename(b).split(".")[0] for b in benchmark_paths])
    merged_dir = "data/benchmarks/merged"
    os.makedirs(merged_dir, exist_ok=True)
    merged_path = os.path.join(merged_dir, f"{bench}.qasm")
    with open(merged_path, "w") as f:
        f.write(dumps(merged_circuit))


    try:
        metrics = _compile_one(merged_path, target)
    except Exception as e:
        # PowerMove's grid only covers the entanglement zone, so large merged sets may not fit.
        warn("PowerMove", f"could not compile merged set of size {len(benchmark_set)} ({e}), skipping")
        return

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
            "n_bench",
            "execution_time",
        ]
    )

    data.loc[len(data)] = [
        bench,
        metrics["nqubits"],
        metrics["total_fidelity"],
        metrics["total_coherence_fidelity"],
        metrics["total_transfer_fidelity"],
        metrics["total_2q_on_idle"],
        metrics["total_2q_gate_fidelity"],
        metrics["total_1q_gate_fidelity"],
        len(benchmark_set),
        metrics["cir_duration"] / 1000,
    ]

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    if not os.path.isfile(output_file):
        data.to_csv(output_file, index=False)
    else:
        data.to_csv(output_file, mode="a", header=False, index=False)
