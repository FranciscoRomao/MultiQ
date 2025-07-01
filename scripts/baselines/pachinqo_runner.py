import pdb
import yaml
import numpy as np
import os
import pandas as pd
import csv
from qiskit import transpile, QuantumCircuit
from atomique.compilers.FPQAC.fpqac_generic_compiler import FPQACGenericCompiler
from atomique.benchmarks.benchmark_set import BenchmarkSets
from atomique.hyperparams import HyperParamSets
from atomique.utils import count_1q_2q_gates, get_n2q_interation_stats
from tools.gen_benchmarks import gen_single_benchmarks, gen_joint_benchmarks, save_circuit, gen_random_circuits
from pachinqo.framework.grid import Grid

'''
def compute_fidelity(returned_values,cir_qubits):
    layers  = returned_values[0]
    total_move_distance = returned_values[1]
    nsequential_transfers = returned_values[2]
    total_trap_changes = nsequential_transfers * cir_qubits

    gate_1q_fidelity = 0.999
    gate_2q_fidelity = 0.995
    gate_1q_time = 0.5 #us
    gate_2q_time = 0.2 #us
    decoherence_T2 = 1500000 #us
    transfer_time = 20 #us
    transfer_fid = 0.999
    move_speed = 0.55 #um/us

    total_transfer_fidelity = transfer_fid**total_trap_changes
    total_transfer_time = transfer_time*nsequential_transfers
    total_shuttling_time = total_move_distance/move_speed
    total_idling_time = total_transfer_time + total_move_distance/move_speed
    total_decoherence_fidelity = np.exp(-total_idling_time/decoherence_T2)

    #Compute number of 1q and 2q gates from the layers
    total_u3_gates = 0
    total_cz_gates = 0

    for layer in layers:
        total_u3_gates += len(layer[2])
        total_cz_gates += len(layer[0])

    gate_1q_fidelity = gate_1q_fidelity**total_u3_gates
    gate_2q_fidelity = gate_2q_fidelity**total_cz_gates
    total_1q_time = gate_1q_time*total_u3_gates
    total_2q_time = gate_2q_time*total_cz_gates

    total_execution_time = total_transfer_time + total_move_distance/move_speed + total_1q_time + total_2q_time

    total_fidelity = gate_1q_fidelity*gate_2q_fidelity*total_transfer_fidelity*total_decoherence_fidelity

    return total_fidelity, total_transfer_fidelity, total_decoherence_fidelity, gate_1q_fidelity, gate_2q_fidelity, total_shuttling_time, total_execution_time, total_transfer_fidelity
'''
'''
circuit_sizes = [10, 25, 50, 100, 150, 200, 250]
#circuit_sizes = [8]
#benchmarks = ["ghz", "wstate", "dj", "grover-noancilla"]
#benchmarks = ["ghz", "wstate", "dj"]
circuits_per_size = 10
benchmark_sets = []

print("Generating single benchmarks...")
benchmark_sets = gen_random_circuits(circuit_sizes, regen=False, ncircuits_per_size=circuits_per_size)
#benchmark_sets += gen_single_benchmarks(circuit_sizes, benchmarks, regen=True)

dir = "benchmarks/circuits/random/"

print("Generating joint benchmarks...")
np.random.seed(42)
benchgroups = np.random.choice([f"random{j}-10" for j in range(circuits_per_size)], (circuits_per_size, 2))
benchmark_sets += gen_joint_benchmarks(benchgroups, [[10]*2]*circuits_per_size, folder=dir)

for index,i in enumerate(circuit_sizes[2:]):
    np.random.seed(42)
    benchgroups = np.random.choice([f"random{j}-{i}" for j in range(circuits_per_size)], (circuits_per_size, 2*(index+1)))
    benchmark_sets += gen_joint_benchmarks(benchgroups, [[25]*2*(index+1)]*circuits_per_size, folder=dir)

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

for algo in benchmark_sets:
    name = 'benchmarks/transpiled/' + algo.split('/')[-1].split('.')[0] + "_transpiled.qasm"
    nqubits = sum(int(i) for  i in algo.split('/')[-1].split('-')[1].split('.')[0].split('_'))
    if not os.path.exists(f"benchmarks/transpiled/{algo.split('/')[-1].split('.')[0]}_transpiled.qasm"):
        transpiled_circuit = QuantumCircuit.from_qasm_file(algo)
        transpiled_circuit = transpile(transpiled_circuit, optimization_level=0, basis_gates=['u3', 'cz'])
        transpiled_circuit.remove_final_measurements()
        print(f"Saving {name}...")
        save_circuit(transpiled_circuit, name)
    
    print(f"Running {name}...")
    #Two caches 
    #zone_specs = [
    #    {'type': 'StorageZone', 'bottom_left_x': 90, 'bottom_left_y': 0, 'width': 190, 'height': 50},
    #    {'type': 'EntanglementZone', 'bottom_left_x': 90, 'bottom_left_y': 60, 'width': 190, 'height': 130, 'col_size': 4},
    #    {'type': 'ReadoutZone', 'bottom_left_x': 0, 'bottom_left_y': 60, 'width': 80, 'height': 130},
    #    {'type': 'StorageZone', 'bottom_left_x': 290, 'bottom_left_y': 60, 'width': 80, 'height':130}
    #]
    #One cache
    zone_specs = [
        {'type': 'StorageZone', 'bottom_left_x': 90, 'bottom_left_y': 0, 'width': 190, 'height': 50},
        {'type': 'EntanglementZone', 'bottom_left_x': 90, 'bottom_left_y': 60, 'width': 190, 'height': 130, 'col_size': 4},
        {'type': 'ReadoutZone', 'bottom_left_x': 0, 'bottom_left_y': 60, 'width': 80, 'height': 130},
        {'type': 'ReadoutZone', 'bottom_left_x': 290, 'bottom_left_y': 60, 'width': 80, 'height':130}
    ]
    grid = Grid(zone_specs, 0, name, num_atoms=250)
    ret_vals = grid.return_vals()

    total_fidelity, total_transfer_fidelity, total_coherence_fidelity, total_1q_fidelity, total_2q_fidelity, cir_shuttling_time, execution_time, total_transfer_fidelity = compute_fidelity(ret_vals, nqubits)

    data.loc[len(data)] = [algo.split('/')[-1].split('-')[0],
                            nqubits,
                            total_fidelity,
                            ret_vals[3],
                            total_1q_fidelity,
                            total_2q_fidelity,
                            total_coherence_fidelity,
                            total_transfer_fidelity,
                            cir_shuttling_time,
                            execution_time]

if not os.path.isfile(f"results/pachinqo_results.csv"):
    data.to_csv(f"results/pachinqo_results.csv", index=False)
else:
    data.to_csv(f"results/pachinqo_results.csv", mode='a', header=False, index=False)
'''