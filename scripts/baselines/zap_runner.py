import os
import sys
import time

import pandas as pd
from qiskit import QuantumCircuit, transpile
from qiskit.qasm2 import dumps

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../compilers/zap"))

from zap.scheduler.scheduler import Scheduler
from zap.router import router as zap_router_module
from zap.router.router import Router
from zap.simulator.simulator import Simulator

from baselines.zap_arch import general_arch_to_zap_arch, load_general_arch

# Same movement timing model as qmap_runner.py, patched into ZAP's router to replace its own sqrt law.
_T_D_MAX = 200.0  # us, time to traverse d_max
_D_MAX = 110.0  # um, max distance for the cubic profile
_JERK = 32 * _D_MAX / _T_D_MAX**3
_V_MAX = _D_MAX / _T_D_MAX * 2


def _movement_duration(self, d):
    if d <= 0:
        return 0.0
    if d <= _D_MAX:
        return 2 * (4 * d / _JERK) ** (1 / 3)
    return _T_D_MAX + (d - _D_MAX) / _V_MAX


zap_router_module.Router.movement_duration = _movement_duration

SCHEDULING_STRATEGY = "asap_separate"
PLACEMENT_STRATEGY = "baseline"
ROUTING_STRATEGY = "baseline"


def _get_sites(slm: dict) -> list:
    x, y = slm["location"]
    sep_x, sep_y = slm["site_seperation"]
    return [
        (x + i * sep_x, y + j * sep_y)
        for j in range(slm["r"])
        for i in range(slm["c"])
    ]


def _slm_sites(architecture: dict) -> tuple:
    stg_sites, ent_sites = [], []
    for zone in architecture["storage_zones"]:
        for slm in zone["slms"]:
            stg_sites += _get_sites(slm)
    for zone in architecture["entanglement_zones"]:
        for slm in zone["slms"]:
            ent_sites += _get_sites(slm)
    return list(set(stg_sites)), list(set(ent_sites))


def _build_g_q(circuit: QuantumCircuit) -> tuple:
    """Flatten a transpiled circuit into ZAP's gate list, skipping virtual Z rotations (u1, id) that cost no time."""
    transpiled = transpile(
        circuit, basis_gates=["cz", "id", "u2", "u1", "u3"], optimization_level=3, seed_transpiler=0
    )

    g_q = []
    n_2q_gate = 0
    n_1q_gate = 0
    for inst in transpiled.data:
        name = inst.operation.name
        if inst.operation.num_qubits == 2:
            n_2q_gate += 1
            g_q.append((inst.qubits[0]._index, inst.qubits[1]._index))
        elif name in ("measure", "barrier", "id", "u1"):
            continue
        elif name in ("u2", "u3"):
            if name == "u3" and abs(inst.operation.params[0]) < 1e-9:
                # A u3 with zero theta is a pure Z rotation.
                continue
            n_1q_gate += 1
            q = inst.qubits[0]._index
            g_q.append((q, q))
        else:
            raise ValueError(f"Unexpected gate in transpiled circuit: {name}")

    return g_q, n_1q_gate, n_2q_gate, transpiled.num_qubits


def _compile_one(benchmark_path: str, architecture: dict) -> dict:
    compile_start = time.perf_counter()

    circuit = QuantumCircuit.from_qasm_file(benchmark_path)
    g_q, n_1q_gate, n_2q_gate, n_q = _build_g_q(circuit)

    stg_sites, ent_sites = _slm_sites(architecture)
    if n_q > len(stg_sites):
        raise ValueError(
            f"Circuit needs {n_q} qubits after transpile but this architecture "
            f"defines only {len(stg_sites)} storage traps."
        )

    results_code = {
        "benchmark": os.path.splitext(os.path.basename(benchmark_path))[0],
        "output_dir": "",
        "compilation_time": 0,
        "n_q": n_q,
        "n_1q_gate": n_1q_gate,
        "n_2q_gate": n_2q_gate,
        "stages": {},
        "instructions": [],
    }

    scheduler = Scheduler(g_q=g_q, results_code=results_code)
    if SCHEDULING_STRATEGY == "asap_separate":
        scheduler.asap_separate()
    else:
        scheduler.asap_joint()

    list_gate = [[g_q[i] for i in gates] for gates in scheduler.list_scheduling]

    router = Router(
        slm_sites=[stg_sites, ent_sites],
        results_code=results_code,
        list_full_gates=list_gate,
        qubit_mapping=[],
        architecture=architecture,
        placement_strategy=PLACEMENT_STRATEGY,
        routing_strategy=ROUTING_STRATEGY,
    )
    results_code = router.results_code

    compilation_time = time.perf_counter() - compile_start

    simulator = Simulator(results_code=results_code, architecture=architecture)

    return {
        "nqubits": n_q,
        "total_fidelity": simulator.cir_fidelity,
        "total_coherence_fidelity": simulator.cir_fidelity_coherence,
        "total_transfer_fidelity": simulator.cir_fidelity_atom_transfer,
        "total_2q_on_idle": simulator.cir_fidelity_2q_gate_for_idle,
        "total_2q_gate_fidelity": simulator.cir_fidelity_2q_gate,
        "total_1q_gate_fidelity": simulator.cir_fidelity_1q_gate,
        "cir_duration": simulator.total_duration,
        "compilation_time": compilation_time,
    }


def run_zap_single_benchmarks(benchmark_file: str, arch_spec_path: str, output_file: str):
    """Compile a single QASM circuit with ZAP against a target derived from a ZAC-style spec."""
    architecture = general_arch_to_zap_arch(load_general_arch(arch_spec_path))

    filename = os.path.join("data/benchmarks", benchmark_file)
    benchmark = benchmark_file.split("/")[-1]

    print("==============================================")
    print(f"Compile circuit {benchmark_file} with ZAP")

    metrics = _compile_one(filename, architecture)

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


def run_zap_merge_benchmarks(benchmark_set: list[str], arch_spec_path: str, output_file: str):
    """Merge a benchmark set into one circuit and compile it with ZAP as a single program."""
    architecture = general_arch_to_zap_arch(load_general_arch(arch_spec_path))

    benchmark_paths = [os.path.join("data/benchmarks", bench) for bench in benchmark_set]
    circuits = [QuantumCircuit.from_qasm_file(bench) for bench in benchmark_paths]
    merged_circuit = merge_circuits(circuits)

    bench = "-".join([os.path.basename(b).split(".")[0] for b in benchmark_paths])
    merged_dir = "data/benchmarks/merged"
    os.makedirs(merged_dir, exist_ok=True)
    merged_path = os.path.join(merged_dir, f"{bench}.qasm")
    with open(merged_path, "w") as f:
        f.write(dumps(merged_circuit))

    print("==============================================")
    print(f"Compile merged benchmark set {bench} with ZAP")

    try:
        metrics = _compile_one(merged_path, architecture)
    except Exception as e:
        # ZAP's baseline placer can run out of candidate pairs on the largest merged circuits.
        print(f"[WARN] ZAP could not compile merged benchmark set {bench} ({e}); skipping this set size")
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
