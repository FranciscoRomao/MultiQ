from mqt import qcec
from qiskit import QuantumCircuit
from typing import Dict
from multiq.configuration import MultiQConfig
import logging

logger = logging.getLogger("multiq.checker")

class Checker:
    """Translates ZAIR instructions back into a Qiskit circuit and checks equivalence with the original."""

    def __init__(self, config: MultiQConfig):
        self.config: MultiQConfig = config 


    def translate_ZAIR_to_circuit(self, instructions:Dict, nqubits:int) -> QuantumCircuit:
        """Translate ZAIR instructions to a Qiskit circuit."""
        circuit = QuantumCircuit(nqubits)

        qubit_locs = [[] for _ in range(nqubits)]

        for instruction in instructions:
            op = instruction['type']

            if op == 'init':
                for i in range(nqubits):
                    qubit_locs[i] = instruction['init_locs'][i][1:]  # skip the atom ID
                
            elif op == 'row1qGate':  # treated as a u3 gate
                for idx, loc in enumerate(instruction['locs']):
                    qubit_idx = loc[0]
                    params = instruction['params'][idx]
                    
                    if len(params) != 3:
                        logger.error(f"Invalid number of parameters for u3 gate: {params}")
                        raise ValueError(f"Invalid number of parameters for u3 gate, 3 parameters expected, got {len(params)}.")
                    
                    circuit.u(params[0], params[1], params[2], qubit_idx)

            elif op == 'rearrangeJob':
                for locs in instruction['end_locs']:
                    qubit_locs[locs[0]] = locs[1:]

            elif op == 'rydberg':
                for pair in instruction['pairs']:
                    q0, q1 = pair
                    circuit.cz(q0, q1)

            else:
                logger.error(f"Unknown instruction type: {op}")
                raise ValueError(f"Unknown instruction type: {op}")

        return circuit

    def check_equivalence(self, circuit0: QuantumCircuit, circuit1: QuantumCircuit) -> bool:
        """Check equivalence of two circuits with QCEC."""
        result = qcec.verify(circuit0, circuit1,
                             run_alternating_checker=True,
                             run_zx_checker=True,
                             numerical_tolerance=2e-13)
        
        return result.considered_equivalent()