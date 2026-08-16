import os
import sys

import pandas as pd
from qiskit import QuantumCircuit, transpile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../compilers/zap"))

from zap.scheduler.scheduler import Scheduler
from zap.router import router as zap_router_module
from zap.router.router import Router
from zap.simulator.simulator import Simulator

from baselines.zap_arch import general_arch_to_zap_arch, load_general_arch

# Movement timing model copied from qmap's own eval/na/zoned/eval_ids_relaxed_routing.py
# (see qmap_runner.py's identical constants/derivation) so all baselines score compiled
# durations against the same physical movement-timing assumptions. ZAP's own
# Router.movement_duration hardcodes the same unbounded sqrt law PowerMove used
# (200*sqrt(d/110), no velocity cap) regardless of the "routing.movement" knobs it
# reads at __init__ time - so we monkeypatch the method itself rather than the config.
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

# Single AOD in general_arch.json's "aods" list - ZAP has no discrete-AOD concept to
# plumb through (see zap_arch.py), so there's nothing to vary here.
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
    """
    Transpile to CZ + single-qubit-rotation basis and flatten into ZAP's flat
    ``g_q`` gate list (``(q0, q1)`` pairs, ``q0 == q1`` for 1-qubit gates).

    Physically, an arbitrary single-qubit rotation is implemented as a Z-X-Z
    (XZX) sequence: a global or per-qubit Z phase, one physical X-axis Raman
    pulse, then another Z phase. Both Z rotations are virtual - a classical
    frame-of-reference update, whether applied to every qubit at once (global)
    or to one qubit alone (local) - so they cost neither time nor fidelity.
    Qiskit's u1/u2/u3 basis already separates these: u1 (and id) are pure Z
    rotations with no physical pulse at all, while u2/u3 always carry a
    nonzero X-axis component and cost exactly one physical 1-qubit gate.
    Counting u1/id as full-cost gates (as a naive flatten would) double-counts
    virtual phase bookkeeping as if it were physical hardware time.
    """
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
                # Zero-angle u3 is a disguised pure Z rotation - free, same as u1.
                continue
            n_1q_gate += 1
            q = inst.qubits[0]._index
            g_q.append((q, q))
        else:
            raise ValueError(f"Unexpected gate in transpiled circuit: {name}")

    return g_q, n_1q_gate, n_2q_gate, transpiled.num_qubits


def _compile_one(benchmark_path: str, architecture: dict) -> dict:
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
    }


def run_zap_single_benchmarks(benchmark_file: str, arch_spec_path: str, output_file: str):
    """
    Compile a single QASM circuit with ZAP against a fixed target derived from
    `arch_spec_path` (a ZAC-style general_arch.json). Mirrors
    run_zac_single_benchmarks/run_powermove_single_benchmarks/run_qmap_single_benchmarks
    so results/zap/e2e_results.csv lines up row-for-row with the other baselines.
    """
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
    ]

    if not os.path.isfile(output_file):
        data.to_csv(output_file, index=False)
    else:
        data.to_csv(output_file, mode="a", header=False, index=False)
