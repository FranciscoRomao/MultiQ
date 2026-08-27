import json
import argparse
import os
import pdb
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit.qasm2 import dumps
from mqt.bench import get_benchmark, BenchmarkLevel
from qiskit import transpile
#from qiskit.circuit.random import random_circuit
from qiskit.circuit import QuantumCircuit, CircuitInstruction
from qiskit.circuit.library import standard_gates
from qiskit.quantum_info.operators.symplectic.clifford_circuits import _BASIS_1Q, _BASIS_2Q
import numpy as np
from qiskit.converters import circuit_to_dag
from collections import defaultdict

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

def merge_circuits_from_qasm(files: list[str], output_dir='data/benchmarks/random') -> str:
    assert len(files) >= 1, "At least one circuit is required to merge."

    files = [os.path.join(output_dir, file) for file in files if os.path.exists(os.path.join(output_dir, file))]
    
    circuits = [QuantumCircuit.from_qasm_file(circuit) for circuit in files]

    new_circuit: QuantumCircuit = circuits[0].copy()

    circuit_name = ''.join([os.path.basename(file).split('.')[0] + '-' for file in files])[:-1] + "_merged.qasm"

    for i in range(1, len(circuits)):
        circuit2 = circuits[i]
        new_circuit_copy = new_circuit.copy()
        
        # Create a new quantum circuit with enough qubits and classical bits
        total_qubits = new_circuit.num_qubits + circuit2.num_qubits
        total_clbits = new_circuit.num_clbits + circuit2.num_clbits

        new_circuit = QuantumCircuit(total_qubits, total_clbits)

        # Map circuit1's qubits and clbits into the new circuit
        new_circuit.compose(
            new_circuit_copy,
            qubits=range(new_circuit_copy.num_qubits),
            clbits=range(new_circuit_copy.num_clbits),
            inplace=True
        )

        # Map circuit2's qubits and clbits into the new circuit
        new_circuit.compose(
            circuit2,
            qubits=range(new_circuit_copy.num_qubits, total_qubits),
            clbits=range(new_circuit_copy.num_clbits, total_clbits),
            inplace=True
        )

    save_circuit(new_circuit, os.path.join(output_dir, circuit_name))
    
    return os.path.join(output_dir, circuit_name)

def merge_circuits(circuits: list[QuantumCircuit]) -> QuantumCircuit:
    assert len(circuits) >= 1, "At least one circuit is required to merge."

    if len(circuits) == 1:
        return circuits[0]

    new_circuit: QuantumCircuit = circuits[0].copy()

    for i in range(1, len(circuits)):
        circuit2 = circuits[i]
        new_circuit_copy = new_circuit.copy()
        
        # Create a new quantum circuit with enough qubits and classical bits
        total_qubits = new_circuit.num_qubits + circuit2.num_qubits
        total_clbits = new_circuit.num_clbits + circuit2.num_clbits

        new_circuit = QuantumCircuit(total_qubits, total_clbits)

        # Map circuit1's qubits and clbits into the new circuit
        new_circuit.compose(
            new_circuit_copy,
            qubits=range(new_circuit_copy.num_qubits),
            clbits=range(new_circuit_copy.num_clbits),
            inplace=True
        )

        # Map circuit2's qubits and clbits into the new circuit
        new_circuit.compose(
            circuit2,
            qubits=range(new_circuit_copy.num_qubits, total_qubits),
            clbits=range(new_circuit_copy.num_clbits, total_clbits),
            inplace=True
        )
    
    return new_circuit

def cut_circuit_critical_path_limit_NA(circuit: QuantumCircuit, depth: int) -> QuantumCircuit:
    assert circuit.data is not None, "Input circuit is empty."
    
    dag = circuit_to_dag(circuit)

    # Initialize qubit free layers and global type busy trackers for the truncated circuit
    qubit_free_layer = defaultdict(int)
    multi_qubit_busy_until_layer = 0
    single_qubit_busy_until_layer = 0

    # Initialize the new truncated circuit
    truncated_qc = QuantumCircuit(circuit.num_qubits, circuit.num_clbits)

    # Store a list of nodes that have been successfully added
    added_nodes = []

    # Iterate through the DAG layers to respect causal dependencies
    for layer in dag.layers():
        # Check if adding any gate from this layer would exceed the limit
        # We need to compute the *earliest possible start* for this DAG layer's operations
        # under the constraint. If this earliest start already exceeds the limit, we stop.
        
        # Temporarily calculate the 'next' busy layers if we were to process this layer.
        # This is a speculative calculation to check if we exceed the limit.
        temp_next_multi_qubit_busy_until = multi_qubit_busy_until_layer
        temp_next_single_qubit_busy_until = single_qubit_busy_until_layer

        contains_multi_qubit_in_dag_layer = any(len(node.qargs) > 1 for node in layer['graph'].op_nodes())
        contains_single_qubit_in_dag_layer = any(len(node.qargs) == 1 for node in layer['graph'].op_nodes())
        
        # We need to simulate the scheduling of this DAG layer to see where its last gate would finish.
        # Create a temporary copy of qubit_free_layer for speculative calculation
        temp_qubit_free_layer = qubit_free_layer.copy()
        
        speculative_current_layer_max_finish = 0

        # Simulate processing multi-qubit gates in this DAG layer first (if both types are present)
        if contains_multi_qubit_in_dag_layer:
            for node in layer['graph'].op_nodes():
                if len(node.qargs) > 1:
                    physical_qubits = [q._index for q in node.qargs]
                    earliest_start_due_to_qubit_deps = max(temp_qubit_free_layer[q] for q in physical_qubits) if physical_qubits else 0
                    
                    #This gate can only start after all the gate it depends on are finished and after the last single-qubit gate finished (assuming multi-qubit gates can be run in parallel)
                    current_op_start_layer = max(earliest_start_due_to_qubit_deps, temp_next_single_qubit_busy_until)
                    current_op_finish_layer = current_op_start_layer + 1
                    
                    for q in physical_qubits:
                        temp_qubit_free_layer[q] = current_op_finish_layer
                    
                    temp_next_multi_qubit_busy_until = max(temp_next_multi_qubit_busy_until, current_op_finish_layer)
                    speculative_current_layer_max_finish = max(speculative_current_layer_max_finish, current_op_finish_layer)

        # Simulate processing single-qubit gates in this DAG layer (if both types are present)
        if contains_single_qubit_in_dag_layer:
            for node in layer['graph'].op_nodes():
                if len(node.qargs) == 1:
                    physical_qubits = [q._index for q in node.qargs]
                    earliest_start_due_to_qubit_deps = max(temp_qubit_free_layer[q] for q in physical_qubits) if physical_qubits else 0

                    current_op_start_layer = max(earliest_start_due_to_qubit_deps, temp_next_multi_qubit_busy_until)
                    current_op_finish_layer = current_op_start_layer + 1
                    
                    for q in physical_qubits:
                        temp_qubit_free_layer[q] = current_op_finish_layer
                    
                    temp_next_single_qubit_busy_until = max(temp_next_single_qubit_busy_until, current_op_finish_layer)
                    speculative_current_layer_max_finish = max(speculative_current_layer_max_finish, current_op_finish_layer)

        projected_critical_path = max(temp_next_multi_qubit_busy_until, temp_next_single_qubit_busy_until)

        for node in layer['graph'].op_nodes():
            truncated_qc.append(node.op, node.qargs, node.cargs)
            added_nodes.append(node) # Keep track of what was added

        if projected_critical_path >= depth:
            return truncated_qc

        # If we reach here, this DAG layer (or its relevant parts) can be added.
        # Now, actually apply the changes based on the processed speculative results
        qubit_free_layer = temp_qubit_free_layer # Commit the qubit free times
        multi_qubit_busy_until_layer = temp_next_multi_qubit_busy_until
        single_qubit_busy_until_layer = temp_next_single_qubit_busy_until

    return truncated_qc

def random_circuit(
    num_qubits,
    depth,
    max_operands=4,
    seed=None,
    num_operand_distribution: dict = None,
    gates_1q: list = None,
    gates_2q: list = None,
    gates_3q: list = None,
    gates_4q: list = None,
):
    assert num_qubits >= 0, "Number of qubits must be non-negative."
    assert depth > 0, "Depth must be positive to generate a meaningful circuit."
    assert max_operands in [1, 2, 3, 4], "max_operands must be between 1 and 4."

    if seed is None:
        seed = np.random.randint(0, np.iinfo(np.int32).max)
    rng = np.random.default_rng(seed)

    if num_operand_distribution:
        assert min(num_operand_distribution.keys()) >= 1 or max(num_operand_distribution.keys()) <= 4, "'num_operand_distribution' must have keys between 1 and 4"
        assert sum(num_operand_distribution.values()) == 1, "The sum of all values in 'num_operand_distribution' must be 1."
    elif max_operands==1:
        num_operand_distribution = {1: 1.0}
    elif max_operands==2:
        num_operand_distribution = {1: 0.7, 2: 0.3}
    elif max_operands==3:
        num_operand_distribution = {1: 0.5, 2: 0.3, 3: 0.2}
    elif max_operands==4:
        num_operand_distribution = {1: 0.4, 2: 0.3, 3: 0.2, 4: 0.1}

        for key, prob in num_operand_distribution.items():
            assert key <= num_qubits, f"'num_operand_distribution' cannot have {key}-qubit gates \n for circuit with {num_qubits} qubits"
            
        num_operand_distribution = dict(sorted(num_operand_distribution.items()))

    if not num_operand_distribution and max_operands:
        max_operands = max_operands if num_qubits > max_operands else num_qubits
        rand_dist = rng.dirichlet(
            np.ones(max_operands)
        )  # This will create a random distribution that sums to 1
        num_operand_distribution = {i + 1: rand_dist[i] for i in range(max_operands)}
        num_operand_distribution = dict(sorted(num_operand_distribution.items()))

    if gates_1q is None:
        gates_1q = _BASIS_1Q

    if gates_2q is None:
        gates_2q = _BASIS_2Q

    if gates_3q is None:
        gates_3q = _BASIS_3Q

    if gates_4q is None:
        gates_4q = _BASIS_4Q

    gates_1q = np.array(
        gates_1q, dtype=[("class", object), ("num_qubits", np.int64), ("num_params", np.int64)]
    )
    gates_2q = np.array(gates_2q, dtype=gates_1q.dtype)
    gates_3q = np.array(gates_3q, dtype=gates_1q.dtype)
    gates_4q = np.array(gates_4q, dtype=gates_1q.dtype)

    all_gate_lists = [gates_1q, gates_2q, gates_3q, gates_4q]

    # Here we will create a list 'gates_to_consider' that will have a
    # subset of different n-qubit gates and will also create a list for
    # ratio (or probability) for each gates
    gates_to_consider = []
    distribution = []
    for n_qubits, ratio in num_operand_distribution.items():
        gate_list = all_gate_lists[n_qubits - 1]
        gates_to_consider.extend(gate_list)
        distribution.extend([ratio / len(gate_list)] * len(gate_list))

    gates = np.array(gates_to_consider, dtype=gates_1q.dtype)

    qc = QuantumCircuit(num_qubits)

    qubits = np.array(qc.qubits, dtype=object, copy=True)

    # Counter to keep track of number of different gate types
    counter = np.zeros(len(all_gate_lists) + 1, dtype=np.int64)
    total_gates = 0

    # Apply arbitrary random operations in layers across all qubits.
    for layer_number in range(depth):
        # We generate all the randomness for the layer in one go, to avoid many separate calls to
        # the randomization routines, which can be fairly slow.

        # This reliably draws too much randomness, but it's less expensive than looping over more
        # calls to the rng. After, trim it down by finding the point when we've used all the qubits.

        # Due to the stochastic nature of generating a random circuit, the resulting ratios
        # may not precisely match the specified values from `num_operand_distribution`. Expect
        # greater deviations from the target ratios in quantum circuits with fewer qubits and
        # shallower depths, and smaller deviations in larger and deeper quantum circuits.
        # For more information on how the distribution changes with number of qubits and depth
        # refer to the pull request #12483 on Qiskit GitHub.

        gate_specs = rng.choice(gates, size=len(qubits), p=distribution)
        cumulative_qubits = np.cumsum(gate_specs["num_qubits"], dtype=np.int64)

        # Efficiently find the point in the list where the total gates would use as many as
        # possible of, but not more than, the number of qubits in the layer.  If there's slack, fill
        # it with 1q gates.
        max_index = np.searchsorted(cumulative_qubits, num_qubits, side="right")
        gate_specs = gate_specs[:max_index]

        slack = num_qubits - cumulative_qubits[max_index - 1]
        
        # Updating the counter for 1-qubit, 2-qubit, 3-qubit and 4-qubit gates
        gate_qubits = gate_specs["num_qubits"]
        counter += np.bincount(gate_qubits, minlength=len(all_gate_lists) + 1)

        total_gates += len(gate_specs)

        # Slack handling loop, this loop will add gates to fill
        # the slack while respecting the 'num_operand_distribution'
        while slack > 0:
            gate_added_flag = False

            for key, dist in sorted(num_operand_distribution.items(), reverse=True):
                if slack >= key and counter[key] / total_gates < dist:
                    gate_to_add = np.array(
                        all_gate_lists[key - 1][rng.integers(0, len(all_gate_lists[key - 1]))]
                    )
                    gate_specs = np.hstack((gate_specs, gate_to_add))
                    counter[key] += 1
                    total_gates += 1
                    slack -= key
                    gate_added_flag = True
            if not gate_added_flag:
                break

        # For efficiency in the Python loop, this uses Numpy vectorization to pre-calculate the
        # indices into the lists of qubits and parameters for every gate, and then suitably
        # randomizes those lists.
        q_indices = np.empty(len(gate_specs) + 1, dtype=np.int64)
        p_indices = np.empty(len(gate_specs) + 1, dtype=np.int64)
        q_indices[0] = p_indices[0] = 0
        np.cumsum(gate_specs["num_qubits"], out=q_indices[1:])
        np.cumsum(gate_specs["num_params"], out=p_indices[1:])
        parameters = rng.uniform(0, 2 * np.pi, size=p_indices[-1])
        rng.shuffle(qubits)

        if layer_number != 0:

            c_ptr = 0
            for gate, q_start, q_end, p_start, p_end in zip(
                gate_specs["class"],
                q_indices[:-1],
                q_indices[1:],
                p_indices[:-1],
                p_indices[1:],
            ):
                operation = gate(*parameters[p_start:p_end])
                qc._append(CircuitInstruction(operation=operation, qubits=qubits[q_start:q_end]))
        else:
            for gate, q_start, q_end, p_start, p_end in zip(
                gate_specs["class"], q_indices[:-1], q_indices[1:], p_indices[:-1], p_indices[1:]
            ):
                operation = gate(*parameters[p_start:p_end])
                qc._append(CircuitInstruction(operation=operation, qubits=qubits[q_start:q_end]))
    return qc

def gen_single_benchmarks(circuit_sizes, benchmarks, regen=False):

    benchmarks_set = []
    #merged = merge_two_circuits(ghz_circuit1, ghz_circuit2)
    #Individual circuits sizes 50,100,150,200,250

    for i in benchmarks:
        for j in circuit_sizes:
            if os.path.exists(f"data/benchmarks/generated/{i}-{j}.qasm") and not regen:
                benchmarks_set.append(f"data/benchmarks/generated/{i}-{j}.qasm")
                continue
            tmp = get_benchmark(benchmark=i, level=BenchmarkLevel.INDEP, circuit_size=int(j))
            tmp = transpile(tmp, basis_gates=["cz", "id", "u2", "u1", "u3"], optimization_level=3, seed_transpiler=0)

            benchmarks_set.append(f"data/benchmarks/generated/{i}-{j}.qasm")
            save_circuit(tmp, f"data/benchmarks/generated/{i}-{j}.qasm")
            #save_circuit_figure(tmp, f"benchmarks/figures/{i}-{j}.png")
            
    return benchmarks_set

def single_random_NA_circuit(num_qubits, depth, seed=None, max_operands=2):
    #(gate object, num_qubits, num_params)
    basis_1q = [(standard_gates.U3Gate,1,3)]
    basis_2q = [(standard_gates.CZGate,2,0)]
    circuit = random_circuit(num_qubits, depth, seed=seed, max_operands=max_operands, gates_1q=basis_1q, gates_2q=basis_2q)
    cut_circuit = cut_circuit_critical_path_limit_NA(circuit, depth)
    return cut_circuit

def gen_random_NA_circuits(circuit_sizes, depths, regen=False, ncircuits_per_size=10, seed=42, output_folder="./circuits/"):
    circuit_set = []
    
    for index,j in enumerate(circuit_sizes):
        for i in range(ncircuits_per_size):
            if os.path.exists(f"{output_folder}random{i}-{j}.qasm") and not regen:
                circuit_set.append(f"{output_folder}random{i}-{j}.qasm")
                continue
            tmp = single_random_NA_circuit(num_qubits=j, depth=depths[index], max_operands=2, seed=seed+i)
            #tmp.draw(output='mpl', filename=f"benchmarks/random{i}-{j}.png")
            circuit_set.append(f"{output_folder}random{i}-{j}.qasm")
            save_circuit(tmp, f"{output_folder}random{i}-{j}.qasm")
            
    return circuit_set