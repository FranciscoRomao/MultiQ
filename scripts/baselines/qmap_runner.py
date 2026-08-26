import json
import os
import queue
import re
import time
from itertools import chain
from multiprocessing import get_context

import pandas as pd
from mqt.core import load as load_qc
from mqt.qmap.na.zoned import PlacementMethod, RoutingAwareCompiler, RoutingMethod, ZonedNeutralAtomArchitecture
from qiskit import QuantumCircuit, transpile
from qiskit.qasm2 import dumps

from baselines.qmap_arch import general_arch_to_qmap_arch, load_general_arch

# Hardware can only move an AOD row/column as a rigid whole - it cannot pick up or
# drop off a subset of atoms mid-transit by applying per-atom offsets. RoutingMethod
# defaults to RELAXED (which does exactly that) in qmap's C++ Config, so it must be
# overridden here on every compiler instance to keep the comparison fair.
ROUTING_METHOD = RoutingMethod.strict
PLACEMENT_METHOD = PlacementMethod.astar
FALLBACK_PLACEMENT_METHOD = PlacementMethod.ids

# A* can exhaust memory on densely-entangled circuits (its own search-node bookkeeping
# scales with the search space, not just qubit count) and gets SIGKILLed by the OS
# rather than raising a catchable Python exception. Each compile runs in its own
# subprocess so that kill only takes out the child, and we can fall back to IDS.
COMPILE_TIMEOUT = 15 * 60  # seconds

# A*'s own docs note ~120 bytes/node, so the default max_nodes=10_000_000 alone implies
# >1GB just for search-node bookkeeping. Try progressively tighter caps on OOM/timeout
# before giving up on A* altogether and falling back to IDS.
MAX_NODES_CAPS = [2_000_000, 500_000, 100_000, 20_000]

# Movement timing model copied from qmap's own eval/na/zoned/eval_ids_relaxed_routing.py
# so compiled durations are scored against the same physical assumptions qmap's authors
# used (cubic jerk-limited profile up to d_max, linear beyond it).
_T_D_MAX = 200.0  # us, time to traverse d_max
_D_MAX = 110.0  # um, max distance for the cubic profile
_JERK = 32 * _D_MAX / _T_D_MAX**3
_V_MAX = _D_MAX / _T_D_MAX * 2


def _movement_duration(distance: float) -> float:
    if distance <= _D_MAX:
        return 2 * (4 * distance / _JERK) ** (1 / 3)
    return _T_D_MAX + (distance - _D_MAX) / _V_MAX


def _transpile(circuit: QuantumCircuit) -> QuantumCircuit:
    flattened = QuantumCircuit(circuit.num_qubits, circuit.num_clbits)
    flattened.compose(circuit, inplace=True)
    transpiled = transpile(flattened, basis_gates=["cz", "id", "u2", "u1", "u3"], optimization_level=3, seed_transpiler=0)
    stripped = QuantumCircuit(*transpiled.qregs, *transpiled.cregs)
    for instr in transpiled.data:
        if instr.operation.name not in {"measure", "barrier"}:
            stripped.append(instr)
    return stripped


class _NavizEvaluator:
    """
    Parses the .naviz code produced by qmap's zoned compilers into the same
    fidelity/duration metrics used for ZAC, MultiQ and PowerMove: per-gate/transfer
    fidelity multiplied in as it's encountered, and per-atom idle time accumulated
    over a single sequential clock, feeding a final coherence-fidelity term.

    The event parsing (regexes, load/move/store/cz/u/rz handling) is adapted from
    qmap's own eval/na/zoned/eval_ids_relaxed_routing.py Evaluator, extended here to
    also track fidelity (that reference only computes timing/gate-count stats).
    """

    def __init__(self, arch: dict):
        self.arch = arch
        self.fidelity_2q_gate = arch["operation_fidelity"]["rydberg_gate"]
        self.fidelity_1q_gate = arch["operation_fidelity"]["single_qubit_gate"]
        self.fidelity_atom_transfer = arch["operation_fidelity"]["atom_transfer"]
        self.time_rydberg_gate = arch["operation_duration"]["rydberg_gate"]
        self.time_1q_gate = arch["operation_duration"]["single_qubit_gate"]
        self.time_atom_transfer = arch["operation_duration"]["atom_transfer"]
        self.coherence_time = arch["qubit_spec"]["T"]
        self.entanglement_zone_y_min = arch["entanglement_zones"][0]["slms"][0]["location"][1]

        self.atom_locations: dict[str, tuple[int, int]] = {}
        self.total_time = 0.0
        self.qubit_busy_time: dict[str, float] = {}

        self.cir_fidelity_2q_gate = 1.0
        self.cir_fidelity_1q_gate = 1.0
        self.cir_fidelity_atom_transfer = 1.0

    def _advance(self, duration: float, active_atoms) -> None:
        self.total_time += duration
        for atom in active_atoms:
            self.qubit_busy_time[atom] += duration

    def _process_load_or_store(self, line: str, it, keyword: str) -> None:
        atoms = []
        if re.match(rf"@\+ {keyword} \[", line):
            for next_line in it:
                stripped = next_line.strip()
                if stripped == "]":
                    break
                atoms.append(stripped)
        else:
            match = re.match(rf"@\+ {keyword} (\w+)", line)
            if match:
                atoms.append(match.group(1))
        if not atoms:
            return
        self.cir_fidelity_atom_transfer *= pow(self.fidelity_atom_transfer, len(atoms))
        self._advance(self.time_atom_transfer, atoms)

    def _process_move(self, line: str, it) -> None:
        moves = []
        if re.match(r"@\+ move \[", line):
            for next_line in it:
                stripped = next_line.strip()
                if stripped == "]":
                    break
                match = re.match(r"\((-?\d+\.\d+), (-?\d+\.\d+)\) (\w+)", stripped)
                if match:
                    x, y, atom = match.groups()
                    moves.append((atom, (float(x), float(y))))
        else:
            match = re.match(r"@\+ move \((-?\d+\.\d+), (-?\d+\.\d+)\) (\w+)", line)
            if match:
                x, y, atom = match.groups()
                moves.append((atom, (float(x), float(y))))
        if not moves:
            return

        max_distance = 0.0
        for atom, coord in moves:
            old = self.atom_locations[atom]
            distance = ((coord[0] - old[0]) ** 2 + (coord[1] - old[1]) ** 2) ** 0.5
            max_distance = max(max_distance, distance)

        duration = _movement_duration(max_distance)
        self._advance(duration, (atom for atom, _ in moves))
        for atom, coord in moves:
            self.atom_locations[atom] = coord

    def _process_cz(self) -> None:
        atoms = [a for a, (_, y) in self.atom_locations.items() if y >= self.entanglement_zone_y_min]
        if not atoms:
            return
        assert len(atoms) % 2 == 0, f"Expected an even number of atoms in the entanglement zone, got {len(atoms)}"
        self.cir_fidelity_2q_gate *= pow(self.fidelity_2q_gate, len(atoms) // 2)
        self._advance(self.time_rydberg_gate, atoms)

    def _process_1q(self, line: str, it, keyword: str) -> None:
        atoms = []
        pattern = rf"@\+ {keyword}( \d\.\d+){{3}} \[" if keyword == "u" else rf"@\+ {keyword} \d\.\d+ \["
        single_pattern = rf"@\+ {keyword}( \d\.\d+){{3}} (\w+)" if keyword == "u" else rf"@\+ {keyword} \d\.\d+ (\w+)"
        if re.match(pattern, line):
            for next_line in it:
                stripped = next_line.strip()
                if stripped == "]":
                    break
                atoms.append(stripped)
        else:
            match = re.match(single_pattern, line)
            if match:
                candidate = match.group(2) if keyword == "u" else match.group(1)
                if candidate in self.atom_locations:
                    atoms.append(candidate)
                else:
                    # global rotation with no explicit atom list: applies to every atom at once
                    atoms = list(self.atom_locations.keys())
        if not atoms:
            return
        self.cir_fidelity_1q_gate *= pow(self.fidelity_1q_gate, len(atoms))
        self._advance(self.time_1q_gate, atoms)

    def evaluate(self, code: str) -> dict:
        it = iter(code.splitlines())

        for line in it:
            match = re.match(r"atom\s+\((-?\d+\.\d+),\s*(-?\d+\.\d+)\)\s+(\w+)", line)
            if match:
                x, y, atom_name = match.groups()
                self.atom_locations[atom_name] = (float(x), float(y))
                self.qubit_busy_time[atom_name] = 0.0
            else:
                it = chain([line], it)
                break

        for line in it:
            if line.startswith("@+ load"):
                self._process_load_or_store(line, it, "load")
            elif line.startswith("@+ move"):
                self._process_move(line, it)
            elif line.startswith("@+ store"):
                self._process_load_or_store(line, it, "store")
            elif line.startswith("@+ cz"):
                self._process_cz()
            elif line.startswith("@+ u"):
                self._process_1q(line, it, "u")
            elif line.startswith("@+ rz"):
                self._process_1q(line, it, "rz")
            else:
                raise ValueError(f"Unrecognized operation: {line}")

        cir_fidelity_coherence = 1.0
        for atom, busy in self.qubit_busy_time.items():
            idle_t = self.total_time - busy
            cir_fidelity_coherence *= 1 - idle_t / self.coherence_time

        cir_fidelity = (
            self.cir_fidelity_1q_gate
            * self.cir_fidelity_2q_gate
            * self.cir_fidelity_atom_transfer
            * cir_fidelity_coherence
        )

        return {
            "total_fidelity": cir_fidelity,
            "total_coherence_fidelity": cir_fidelity_coherence,
            "total_transfer_fidelity": self.cir_fidelity_atom_transfer,
            "total_2q_gate_fidelity": self.cir_fidelity_2q_gate,
            "total_1q_gate_fidelity": self.cir_fidelity_1q_gate,
            "cir_duration": self.total_time,
        }


def _compile_worker(q, benchmark_path: str, arch_json_str: str, placement_method, routing_method, max_nodes: int) -> None:
    try:
        arch_dict = json.loads(arch_json_str)
        arch = ZonedNeutralAtomArchitecture.from_json_string(arch_json_str)
        circuit = QuantumCircuit.from_qasm_file(benchmark_path)
        n = circuit.num_qubits
        compile_start = time.perf_counter()

        qc = load_qc(_transpile(circuit))

        compiler = RoutingAwareCompiler(
            arch,
            log_level="error",
            max_filling_factor=0.9,
            use_window=True,
            placement_method=placement_method,
            max_nodes=max_nodes,
            routing_method=routing_method,
            warn_unsupported_gates=False,
        )
        code = compiler.compile(qc)

        compilation_time = time.perf_counter() - compile_start

        metrics = _NavizEvaluator(arch_dict).evaluate(code)
        metrics["nqubits"] = n
        metrics["compilation_time"] = compilation_time
        q.put(("ok", metrics))
    except Exception as e:  # noqa: BLE001 - reported to the parent, not raised here
        q.put(("err", repr(e)))


def _compile_in_subprocess(benchmark_path: str, arch_json_str: str, placement_method, routing_method, max_nodes: int) -> dict:
    """Run one compile+evaluate in a child process so an OOM SIGKILL only takes out the child."""
    ctx = get_context("fork")
    q = ctx.Queue()
    p = ctx.Process(
        target=_compile_worker,
        args=(q, benchmark_path, arch_json_str, placement_method, routing_method, max_nodes),
    )
    p.start()
    p.join(COMPILE_TIMEOUT)

    if p.is_alive():
        p.terminate()
        p.join(2)
        if p.is_alive():
            p.kill()
            p.join()
        raise TimeoutError(f"qmap compile timed out after {COMPILE_TIMEOUT}s (placement={placement_method}, max_nodes={max_nodes})")

    if p.exitcode != 0:
        raise RuntimeError(
            f"qmap compile subprocess died with exit code {p.exitcode} (placement={placement_method}, max_nodes={max_nodes})"
        )

    try:
        status, payload = q.get_nowait()
    except queue.Empty as e:
        raise RuntimeError(
            f"qmap compile subprocess exited cleanly but produced no result (placement={placement_method}, max_nodes={max_nodes})"
        ) from e

    if status == "err":
        raise RuntimeError(payload)
    return payload


def _compile_one(benchmark_path: str, arch_json_str: str) -> dict:
    if PLACEMENT_METHOD == PlacementMethod.astar:
        last_error = None
        for cap in MAX_NODES_CAPS:
            try:
                metrics = _compile_in_subprocess(benchmark_path, arch_json_str, PLACEMENT_METHOD, ROUTING_METHOD, cap)
                metrics["placement_method_used"] = f"{PLACEMENT_METHOD} (max_nodes={cap})"
                return metrics
            except (RuntimeError, TimeoutError) as e:
                last_error = e
                print(f"[WARN] {PLACEMENT_METHOD} with max_nodes={cap} failed on {benchmark_path} ({e}); trying a lower cap")

        print(f"[WARN] {PLACEMENT_METHOD} failed on {benchmark_path} at every max_nodes cap ({last_error}); falling back to {FALLBACK_PLACEMENT_METHOD}")
        metrics = _compile_in_subprocess(benchmark_path, arch_json_str, FALLBACK_PLACEMENT_METHOD, ROUTING_METHOD, MAX_NODES_CAPS[-1])
        metrics["placement_method_used"] = f"{FALLBACK_PLACEMENT_METHOD} (fallback from {PLACEMENT_METHOD})"
        return metrics

    metrics = _compile_in_subprocess(benchmark_path, arch_json_str, PLACEMENT_METHOD, ROUTING_METHOD, MAX_NODES_CAPS[0])
    metrics["placement_method_used"] = str(PLACEMENT_METHOD)
    return metrics


def run_qmap_single_benchmarks(benchmark_file: str, arch_spec_path: str, output_file: str):
    """
    Compile a single QASM circuit with qmap's routing-aware zoned neutral atom
    compiler against a fixed target derived from `arch_spec_path` (a ZAC-style
    general_arch.json). Mirrors run_zac_single_benchmarks / run_powermove_single_benchmarks
    so results/qmap/e2e_results.csv lines up row-for-row with the other baselines.
    """
    arch_json_str = json.dumps(general_arch_to_qmap_arch(load_general_arch(arch_spec_path)))

    filename = os.path.join("data/benchmarks", benchmark_file)
    benchmark = benchmark_file.split("/")[-1]

    print("==============================================")
    print(f"Compile circuit {benchmark_file} with qmap (routing={ROUTING_METHOD}, placement={PLACEMENT_METHOD})")

    metrics = _compile_one(filename, arch_json_str)

    data = pd.DataFrame(
        columns=[
            "benchmark",
            "nqubits",
            "total_fidelity",
            "total_coherence_fidelity",
            "total_transfer_fidelity",
            "total_2q_gate_fidelity",
            "total_1q_gate_fidelity",
            "cir_duration",
            "placement_method_used",
            "compilation_time",
        ]
    )

    data.loc[len(data)] = [
        benchmark.split(".")[0],
        metrics["nqubits"],
        metrics["total_fidelity"],
        metrics["total_coherence_fidelity"],
        metrics["total_transfer_fidelity"],
        metrics["total_2q_gate_fidelity"],
        metrics["total_1q_gate_fidelity"],
        metrics["cir_duration"],
        metrics["placement_method_used"],
        metrics["compilation_time"],
    ]

    if not os.path.isfile(output_file):
        data.to_csv(output_file, index=False)
    else:
        data.to_csv(output_file, mode="a", header=False, index=False)


def merge_circuits(circuits: list[QuantumCircuit]) -> QuantumCircuit:
    """
    Concatenate circuits onto disjoint qubit/clbit ranges, mirroring
    zac_runner.merge_circuits so the controller (no-multiprogramming) eval compiles
    the same merged program across every baseline.
    """
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


def run_qmap_merge_benchmarks(benchmark_set: list[str], arch_spec_path: str, output_file: str):
    """
    Merge a benchmark set into a single circuit and compile it with qmap as one
    program, simulating a controller with no multiprogramming support. Mirrors
    run_zac_merge_benchmarks so results/qmap/controller_results.csv lines up
    row-for-row with results/zac/controller_results.csv.
    """
    arch_json_str = json.dumps(general_arch_to_qmap_arch(load_general_arch(arch_spec_path)))

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
    print(f"Compile merged benchmark set {bench} with qmap (routing={ROUTING_METHOD}, placement={PLACEMENT_METHOD})")

    metrics = _compile_one(merged_path, arch_json_str)

    data = pd.DataFrame(
        columns=[
            "benchmark",
            "nqubits",
            "total_fidelity",
            "total_coherence_fidelity",
            "total_transfer_fidelity",
            "total_2q_gate_fidelity",
            "total_1q_gate_fidelity",
            "n_bench",
            "execution_time",
            "placement_method_used",
        ]
    )

    data.loc[len(data)] = [
        bench,
        metrics["nqubits"],
        metrics["total_fidelity"],
        metrics["total_coherence_fidelity"],
        metrics["total_transfer_fidelity"],
        metrics["total_2q_gate_fidelity"],
        metrics["total_1q_gate_fidelity"],
        len(benchmark_set),
        metrics["cir_duration"] / 1000,
        metrics["placement_method_used"],
    ]

    if not os.path.isfile(output_file):
        data.to_csv(output_file, index=False)
    else:
        data.to_csv(output_file, mode="a", header=False, index=False)
