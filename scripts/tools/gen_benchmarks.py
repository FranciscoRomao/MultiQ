import os
from qiskit import QuantumCircuit
from qiskit.qasm2 import dumps
from mqt.bench import get_benchmark, BenchmarkLevel
from qiskit import transpile
from qiskit.circuit import QuantumCircuit
from qiskit.circuit.library import standard_gates
from qiskit.quantum_info.operators.symplectic.clifford_circuits import _BASIS_1Q, _BASIS_2Q

_BASIS_1Q = [
    (standard_gates.IGate, 1, 0),
    (standard_gates.SXGate, 1, 0),
    (standard_gates.XGate, 1, 0),
    (standard_gates.RZGate, 1, 1),
    (standard_gates.RGate, 1, 2),
    (standard_gates.HGate, 1, 0),
    (standard_gates.PhaseGate, 1, 1),
    (standard_gates.RXGate, 1, 1),
    (standard_gates.RYGate, 1, 1),
    (standard_gates.SGate, 1, 0),
    (standard_gates.SdgGate, 1, 0),
    (standard_gates.SXdgGate, 1, 0),
    (standard_gates.TGate, 1, 0),
    (standard_gates.TdgGate, 1, 0),
    (standard_gates.UGate, 1, 3),
    (standard_gates.U1Gate, 1, 1),
    (standard_gates.U2Gate, 1, 2),
    (standard_gates.U3Gate, 1, 3),
    (standard_gates.YGate, 1, 0),
    (standard_gates.ZGate, 1, 0)]

_BASIS_2Q = [
    (standard_gates.CXGate, 2, 0),
    (standard_gates.DCXGate, 2, 0),
    (standard_gates.CHGate, 2, 0),
    (standard_gates.CPhaseGate, 2, 1),
    (standard_gates.CRXGate, 2, 1),
    (standard_gates.CRYGate, 2, 1),
    (standard_gates.CRZGate, 2, 1),
    (standard_gates.CSXGate, 2, 0),
    (standard_gates.CUGate, 2, 4),
    (standard_gates.CU1Gate, 2, 1),
    (standard_gates.CU3Gate, 2, 3),
    (standard_gates.CYGate, 2, 0),
    (standard_gates.CZGate, 2, 0),
    (standard_gates.RXXGate, 2, 1),
    (standard_gates.RYYGate, 2, 1),
    (standard_gates.RZZGate, 2, 1),
    (standard_gates.RZXGate, 2, 1),
    (standard_gates.XXMinusYYGate, 2, 2),
    (standard_gates.XXPlusYYGate, 2, 2),
    (standard_gates.ECRGate, 2, 0),
    (standard_gates.CSGate, 2, 0),
    (standard_gates.CSdgGate, 2, 0),
    (standard_gates.SwapGate, 2, 0),
    (standard_gates.iSwapGate, 2, 0)]

_BASIS_3Q = [
    (standard_gates.CCXGate, 3, 0),
    (standard_gates.CSwapGate, 3, 0),
    (standard_gates.CCZGate, 3, 0),
    (standard_gates.RCCXGate, 3, 0)]
    
_BASIS_4Q = [
    (standard_gates.C3SXGate, 4, 0),
    (standard_gates.RC3XGate, 4, 0)]

def save_circuit(circuit, filename):
    qasm_str = dumps(circuit)

    with open(filename, "w") as f:
        f.write(qasm_str)


def merge_circuits(circuits: list[QuantumCircuit]) -> QuantumCircuit:
    assert len(circuits) >= 1, "At least one circuit is required to merge."

    if len(circuits) == 1:
        return circuits[0]

    new_circuit: QuantumCircuit = circuits[0].copy()

    for i in range(1, len(circuits)):
        circuit2 = circuits[i]
        new_circuit_copy = new_circuit.copy()
        
        total_qubits = new_circuit.num_qubits + circuit2.num_qubits
        total_clbits = new_circuit.num_clbits + circuit2.num_clbits

        new_circuit = QuantumCircuit(total_qubits, total_clbits)

        new_circuit.compose(
            new_circuit_copy,
            qubits=range(new_circuit_copy.num_qubits),
            clbits=range(new_circuit_copy.num_clbits),
            inplace=True
        )

        new_circuit.compose(
            circuit2,
            qubits=range(new_circuit_copy.num_qubits, total_qubits),
            clbits=range(new_circuit_copy.num_clbits, total_clbits),
            inplace=True
        )
    
    return new_circuit


def gen_benchmarks_from_list(list_file, regen=False):
    """Generate the benchmark files listed in list_file that are missing from data/benchmarks/single/."""
    benchmarks_set = []
    with open(list_file) as f:
        entries = [line.strip() for line in f if line.strip()]

    for entry in entries:
        path = os.path.join("data/benchmarks", entry)
        if os.path.exists(path) and not regen:
            benchmarks_set.append(path)
            continue

        stem = os.path.splitext(os.path.basename(entry))[0]
        name, _, size = stem.rpartition("_n")
        if not name or not size.isdigit():
            raise ValueError(f"can't infer benchmark/size from {entry!r} (expected <name>_n<qubits>.qasm)")

        tmp = get_benchmark(benchmark=name, level=BenchmarkLevel.INDEP, circuit_size=int(size))
        tmp = transpile(tmp, basis_gates=["cz", "id", "u2", "u1", "u3"], optimization_level=3, seed_transpiler=0)

        os.makedirs(os.path.dirname(path), exist_ok=True)
        save_circuit(tmp, path)
        benchmarks_set.append(path)

    return benchmarks_set

def gen_single_benchmarks(circuit_sizes, benchmarks, regen=False):

    benchmarks_set = []

    for i in benchmarks:
        for j in circuit_sizes:
            if os.path.exists(f"data/benchmarks/single/{i}-{j}.qasm") and not regen:
                benchmarks_set.append(f"data/benchmarks/single/{i}-{j}.qasm")
                continue
            tmp = get_benchmark(benchmark=i, level=BenchmarkLevel.INDEP, circuit_size=int(j))
            tmp = transpile(tmp, basis_gates=["cz", "id", "u2", "u1", "u3"], optimization_level=3, seed_transpiler=0)

            benchmarks_set.append(f"data/benchmarks/single/{i}-{j}.qasm")
            save_circuit(tmp, f"data/benchmarks/single/{i}-{j}.qasm")
            
    return benchmarks_set


