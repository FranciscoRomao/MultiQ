import numpy as np
import os
import pandas as pd
from qiskit import transpile, QuantumCircuit
from qiskit.qasm2 import dumps

# PachinQo's package is named "framework".
from framework.grid import Grid

def save_circuit(circuit, filename):
    qasm_str = dumps(circuit)
    os.makedirs(os.path.dirname(filename) or ".", exist_ok=True)

    with open(filename, "w") as f:
        f.write(qasm_str)

def compute_fidelity(returned_values,cir_qubits):
    layers  = returned_values[0]
    total_move_distance = returned_values[1]
    nsequential_transfers = returned_values[2]
    total_trap_changes = nsequential_transfers * cir_qubits

    gate_1q_fidelity = 0.9991
    gate_2q_fidelity = 0.995
    gate_1q_time = 52 #us
    gate_2q_time = 0.36 #us
    decoherence_T2 = 1.5e6 #us
    transfer_time = 15 #us
    transfer_fid = 0.999
    move_speed = 0.55 #um/us

    total_transfer_fidelity = transfer_fid**total_trap_changes
    total_transfer_time = transfer_time*nsequential_transfers
    total_shuttling_time = total_move_distance/move_speed

    total_u3_gates = 0
    total_cz_gates = 0

    for layer in layers:
        total_u3_gates += len(layer[2])
        total_cz_gates += len(layer[0])

    gate_1q_fidelity = gate_1q_fidelity**total_u3_gates
    gate_2q_fidelity = gate_2q_fidelity**total_cz_gates
    total_1q_time = gate_1q_time*total_u3_gates
    total_2q_time = gate_2q_time*total_cz_gates
    
    total_busy_time = total_transfer_time + total_1q_time + total_2q_time

    total_execution_time = total_transfer_time + total_move_distance/move_speed + total_1q_time + total_2q_time

    total_idling_time = total_execution_time*cir_qubits - total_busy_time
    
    total_decoherence_fidelity = np.exp(-total_idling_time/decoherence_T2)

    total_fidelity = gate_1q_fidelity*gate_2q_fidelity*total_transfer_fidelity*total_decoherence_fidelity

    return total_fidelity, total_transfer_fidelity, total_decoherence_fidelity, gate_1q_fidelity, gate_2q_fidelity, total_shuttling_time, total_execution_time, total_transfer_fidelity


def transpile_single_benchmark(benchmark) -> str:
    dir = "data/benchmarks/"
    
    file_path = os.path.join(os.path.dirname(__file__), "../../data/benchmarks/", benchmark)
    name = os.path.join(os.path.dirname(__file__), "../../data/benchmarks/transpiled/", benchmark.split('/')[-1].split('.')[0] + "_transpiled.qasm")

    if not os.path.exists(name):
        transpiled_circuit = QuantumCircuit.from_qasm_file(file_path)
        transpiled_circuit = transpile(transpiled_circuit, optimization_level=3, basis_gates=['u3', 'cz'])
        transpiled_circuit.remove_final_measurements()
        print(f"Saving {name}...")
        save_circuit(transpiled_circuit, name)

    return name

def run_pachiqo_single_benchmark(benchmark, settings_file, output_file="results/pachinqo_results.csv", transpiled_dir="data/benchmarks/transpiled/"):
    
    data = pd.DataFrame(columns=['benchmark',
                                 'nqubits',
                                 'total_fidelity',
                                 'compilation_time',
                                 'total_1q_fidelity',
                                 'total_2q_fidelity',
                                 'total_coherence_fidelity',
                                 'total_transfer_fidelity',
                                 'cir_shuttling_time',
                                 'execution_time'])
    
    transpiled_benchmark = transpile_single_benchmark(benchmark)
    

    zone_specs = [
            {'type': 'StorageZone', 'bottom_left_x': 0, 'bottom_left_y': 0, 'width': 230, 'height': 100},
            {'type': 'EntanglementZone', 'bottom_left_x': 65, 'bottom_left_y': 110, 'width': 100, 'height': 40, 'col_size': 10},
            {'type': 'ReadoutZone', 'bottom_left_x': 0, 'bottom_left_y': 110, 'width': 55, 'height': 40},
            {'type': 'ReadoutZone', 'bottom_left_x': 175, 'bottom_left_y': 110, 'width': 55, 'height':40}
    ]

    print(f"Running {transpiled_benchmark}...")
        
    grid = Grid(zone_specs, 0, transpiled_benchmark, num_atoms=150)


    ret_vals = grid.return_vals()

    circ = QuantumCircuit.from_qasm_file(transpiled_benchmark)
    
    nqubits = len(circ.qubits)

    total_fidelity, total_transfer_fidelity, total_coherence_fidelity, total_1q_fidelity, total_2q_fidelity, cir_shuttling_time, execution_time, total_transfer_fidelity = compute_fidelity(ret_vals, nqubits)

    data.loc[len(data)] = [benchmark.split('/')[-1].split('.')[0],
                           nqubits,
                           total_fidelity,
                           ret_vals[3],
                           total_1q_fidelity,
                           total_2q_fidelity,
                           total_coherence_fidelity,
                           total_transfer_fidelity,
                           cir_shuttling_time,
                           execution_time]

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    if not os.path.isfile(output_file):
        data.to_csv(output_file, index=False)
    else:
        data.to_csv(output_file, mode='a', header=False, index=False)

