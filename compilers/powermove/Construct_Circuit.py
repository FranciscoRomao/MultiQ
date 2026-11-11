import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import Operator
from qiskit.converters import circuit_to_dag
from qiskit.dagcircuit import DAGOutNode

def to_op_type(op):
    if op.name == 'cz':
        return 'CZ'
    else:
        return 'SG'

def get_scheduled_blocks(circuit):
    """
    Partition the circuit's DAG into alternating concurrent layers of same-type
    gates ('CZ' or 'SG', single-qubit), in original circuit order. Returns the
    full, unfiltered layer sequence - see get_cz_blocks/get_sg_blocks for the
    filtered views used elsewhere.
    """
    dag = circuit_to_dag(circuit)
    front_ops = set(dag.front_layer())
    gate_blocks = []
    block_types = []
    while dag.size():
        if len(block_types):
            cur_type = block_types[-1]
        else:
            cur_type = to_op_type(list(front_ops)[0])
            block_types.append(cur_type)
            gate_blocks.append(set())

        add_idx = 0
        for op in front_ops.copy():
            op_type = to_op_type(op)
            q_args = [q._index for q in op.qargs]
            if op_type == cur_type:
                if cur_type != 'CZ':
                    if q_args[0] in gate_blocks[-1]:
                        continue
                add_idx += 1
                if len(q_args) > 1:
                    gate_blocks[-1].add(tuple(q_args))
                else:
                    gate_blocks[-1].add(q_args[0])

                added_front_ops = list(dag.successors(op))
                dag.remove_op_node(op)
                front_ops.remove(op)
                for sop in added_front_ops:
                    if len(list(dag.op_predecessors(sop))) == 0:
                        if not isinstance(sop, DAGOutNode):
                            front_ops.add(sop)



        if not add_idx:
            cur_type = to_op_type(list(front_ops)[0])
            block_types.append(cur_type)
            gate_blocks.append(set())

    return gate_blocks, block_types

def get_cz_blocks(circuit):
    gate_blocks, block_types = get_scheduled_blocks(circuit)
    return [b for b, t in zip(gate_blocks, block_types) if t == 'CZ']

def get_sg_blocks(circuit):
    """Concurrent single-qubit-gate layers, in circuit order, each a set of qubit indices."""
    gate_blocks, block_types = get_scheduled_blocks(circuit)
    return [b for b, t in zip(gate_blocks, block_types) if t == 'SG']

def pauli_strings_to_qiskit_circuit(pauli_strings, keep_length=None):
    if keep_length is not None:
        pauli_strings = pauli_strings[:keep_length]
    circ = QuantumCircuit(len(pauli_strings[0]))
    for paulis in pauli_strings:
        plist = []
        for i in range(len(paulis)):
            if paulis[i] == "X":
                circ.h(i)
                plist.append(i)
            elif paulis[i] == "Y":
                circ.h(i)
                circ.sdg(i)
                plist.append(i)
            elif paulis[i] == "Z":
                plist.append(i)
        if len(plist) > 1:
            for i in plist[1:]:
                circ.cx(i, plist[0])
            circ.rz(np.pi / 8, plist[0])  # change to an rather arbitrary angle
            for i in plist[1:]:
                circ.cx(i, plist[0])
        elif len(plist) == 1:
            circ.rz(np.pi / 8, plist[0])
        for i in range(len(paulis)):
            if paulis[i] == "X":
                circ.h(i)
            elif paulis[i] == "Y":
                circ.s(i)
                circ.h(i)
            elif paulis[i] == "Z":
                pass
    circ = transpile(circ, basis_gates=["u3", "id", "cz"], optimization_level = 2)
    return circ

class QsimRandBenchmark():
    def __init__(self, n_qubits, keep_length, p, i):
        super().__init__()
        self.n_qubits = n_qubits
        self.keep_length = keep_length
        self.p = p
        self.i = i
        self.path = f"qsim/rand/q{n_qubits}_{keep_length}_p{p}/i{i}.txt"
        print(self.path)

        with open(self.path, "r") as fid:
            self.pauli_strings = eval(fid.read())[0:keep_length]

        self.circ = pauli_strings_to_qiskit_circuit(
            self.pauli_strings, keep_length=self.keep_length
        )

def QFT(n):
    circ = QuantumCircuit(n)
    
    # Apply the QFT algorithm using CZ and single-qubit gates
    for j in range(n):
        circ.h(j)
        for k in range(j + 1, n):
            angle = np.pi / (2 ** (k - j))
            circ.rz(angle, k)
            circ.cz(j, k)
        circ.rz(np.pi / 2, j)  # Extra phase for alignment

    # Decompose the SWAP gates using CZ and H
    for j in range(n // 2):
        circ.h(j)
        circ.cz(j, n - j - 1)
        circ.h(j)
        circ.h(n - j - 1)
        circ.cz(n - j - 1, j)
        circ.h(n - j - 1)
        circ.h(j)
        circ.cz(j, n - j - 1)
        circ.h(j)
    return circ
