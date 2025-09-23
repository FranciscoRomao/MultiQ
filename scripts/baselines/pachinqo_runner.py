import pdb
import yaml
import numpy as np
import os
import pdb
import pandas as pd
import csv
from qiskit import transpile, QuantumCircuit
from qiskit.qasm2 import dumps
import logging
import random
#from mqt.qmap.na.zoned import  

# In PachinQo's source code it is called "framework"
from framework.grid import Grid


def save_circuit(circuit, filename):
    qasm_str = dumps(circuit)

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
    
    total_busy_time = total_transfer_time + total_1q_time + total_2q_time

    total_execution_time = total_transfer_time + total_move_distance/move_speed + total_1q_time + total_2q_time

    total_idling_time = total_execution_time*cir_qubits - total_busy_time
    
    total_decoherence_fidelity = np.exp(-total_idling_time/decoherence_T2)

    total_fidelity = gate_1q_fidelity*gate_2q_fidelity*total_transfer_fidelity*total_decoherence_fidelity

    return total_fidelity, total_transfer_fidelity, total_decoherence_fidelity, gate_1q_fidelity, gate_2q_fidelity, total_shuttling_time, total_execution_time, total_transfer_fidelity


def transpile_all_benchmarks(benchmark_set) -> list:
    """
    Transpile all benchmarks in the benchmark set.
    """
    # Load the benchmark set
    dir = "data/benchmarks/"
    transpiled_set = []
    
    for algo in benchmark_set:
        file_path = os.path.join(os.path.dirname(__file__), "../../data/benchmarks/", algo)
        name = os.path.join(os.path.dirname(__file__), "../../data/benchmarks/transpiled/", algo.split('/')[-1].split('.')[0] + "_transpiled.qasm")
        transpiled_set.append(name)
        if not os.path.exists(name):
            transpiled_circuit = QuantumCircuit.from_qasm_file(file_path)
            transpiled_circuit = transpile(transpiled_circuit, optimization_level=3, basis_gates=['u3', 'cz'])
            transpiled_circuit.remove_final_measurements()
            print(f"Saving {name}...")
            save_circuit(transpiled_circuit, name)

    return transpiled_set

def transpile_single_benchmark(benchmark) -> str:
    """
    Transpile all benchmarks in the benchmark set.
    """
    # Load the benchmark set
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
    """
    Run single benchmarks using PachinQo.
    """
    
    # Print the results
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
    
    #for algo in benchmark_set:
        #file_path = os.path.join(os.path.dirname(__file__), "../../data/benchmark/", algo)
        #name = 'benchmarks/transpiled/' + algo.split('/')[-1].split('.')[0] + "_transpiled.qasm"
        #nqubits = sum(int(i) for  i in algo.split('/')[-1].split('-')[1].split('.')[0].split('_"))

    zone_specs = [
            {'type': 'StorageZone', 'bottom_left_x': 0, 'bottom_left_y': 0, 'width': 230, 'height': 100},
            {'type': 'EntanglementZone', 'bottom_left_x': 65, 'bottom_left_y': 110, 'width': 100, 'height': 40, 'col_size': 10},
            {'type': 'ReadoutZone', 'bottom_left_x': 0, 'bottom_left_y': 110, 'width': 55, 'height': 40},
            {'type': 'ReadoutZone', 'bottom_left_x': 175, 'bottom_left_y': 110, 'width': 55, 'height':40}
    ]

    print(f"Running {transpiled_benchmark}...")
        
    grid = Grid(zone_specs, 0, transpiled_benchmark, num_atoms=150)

    #grid.print_grid_by_atoms()

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

    if not os.path.isfile(output_file):
        data.to_csv(output_file, index=False)
    else:
        data.to_csv(output_file, mode='a', header=False, index=False)

def run_pachinqo_merged_benchmarks():

    '''
        """
    Run single benchmarks using PachinQo.
    """
    # Load the benchmark set
    benchmark_set = open("data/benchmark_list.txt").read().splitlines()
    settings_file = os.path.join(os.path.dirname(__file__), "../../config/pachinqo/general.json")
    
    dir = "data/benchmarks/"
    
    # Print the results
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
    
    benchmark_set = transpile_all_benchmarks(benchmark_set)
    
    #for algo in benchmark_set:
        #file_path = os.path.join(os.path.dirname(__file__), "../../data/benchmark/", algo)
        #name = 'benchmarks/transpiled/' + algo.split('/')[-1].split('.')[0] + "_transpiled.qasm"
        #nqubits = sum(int(i) for  i in algo.split('/')[-1].split('-')[1].split('.')[0].split('_"))

    zone_specs = [
            {'type': 'StorageZone', 'bottom_left_x': 0, 'bottom_left_y': 0, 'width': 230, 'height': 100},
            {'type': 'EntanglementZone', 'bottom_left_x': 62, 'bottom_left_y': 120, 'width': 100, 'height': 35, 'col_size': 4},
            {'type': 'ReadoutZone', 'bottom_left_x': 0, 'bottom_left_y': 120, 'width': 42, 'height': 35},
            {'type': 'ReadoutZone', 'bottom_left_x': 182, 'bottom_left_y': 120, 'width': 42, 'height':35}
    ]

    for algo in benchmark_set:
        print(f"Running {algo}...")
        
        grid = Grid(zone_specs, 0, algo, num_atoms=150)

        #grid.print_grid_by_atoms()

        ret_vals = grid.return_vals()

        circ = QuantumCircuit.from_qasm_file(algo)
        nqubits = len(circ.qubits)

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

    logger = logging.getLogger("zac.evaluation")
    random.seed(42)

    logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)

    set_sizes = [5, 6, 7, 8, 9, 10]
    perf_weights = [0.2, 0.4, 0.6, 0.8, 1.0]

    benchmark_set = open("data/bundler_eval_bench_list.txt").read().splitlines()

    benchmark_set = [os.path.join(os.path.dirname(__file__), "../../data/benchmarks", bench) for bench in benchmark_set]

    benchmark_sets = [random.sample(benchmark_set, size) for size in set_sizes]

    bench=''

    merged_bench_files = []

    for benchmark_set in benchmark_sets:
        
        circuits = [QuantumCircuit.from_qasm_file(bench) for bench in benchmark_set]
        merged_circuit = merge_circuits(circuits)

        bench = '-'.join([os.path.basename(b).split('.')[0] for b in benchmark_set])
        merged_bench_files.append(bench)

        save_circuit(merged_circuit, os.path.join(os.path.dirname(__file__), '../../data/benchmarks/merged', f'{bench}.qasm'))
        
    print(f"Runnig ZAC for benchmark set: {bench}")
    
    settings_file = os.path.join(os.path.dirname(__file__), "../../config/zac/general.json")

    # Run the ZAC compiler
    info = run_zac(benchmark_set, settings_file)
    
    # Print the results
    logger.info("ZAC Compilation Info:", info)

    data = pd.DataFrame(columns=['benchmark',
                             'nqubits',
                             'total_fidelity',
                             'total_coherence_fidelity',
                             'total_transfer_fidelity',
                             'total_2q_on_idle',
                             'n_bench'])
    
    results_file:str = ''
    
    for i, bench in enumerate(merged_bench_files):

        print(f"Processing benchmark: {bench}")

        fid_file = os.path.join(os.path.dirname(__file__), '../../results/zac/fidelity', f'{bench}.json')
        time_file = os.path.join(os.path.dirname(__file__), '../../results/zac/time', f'{bench}.json')

        fid_res = pd.read_json(fid_file, typ='series')
        time_res = pd.read_json(time_file, typ='series')

        circuit = QuantumCircuit.from_qasm_file(os.path.join(os.path.dirname(__file__), '../../data/benchmarks/merged', f'{bench}.qasm'))

        data.loc[len(data)] = [bench.split('.')[0],
                               circuit.num_qubits,
                               fid_res['cir_fidelity'],
                               fid_res['cir_fidelity_coherence'],
                               fid_res['cir_fidelity_atom_transfer'],
                               fid_res['cir_fidelity_2q_gate_for_idle'],
                               1]
    
        results_file = os.path.join(os.path.dirname(__file__), '../../results/zac/compiled_results.csv')

    if not os.path.isfile(results_file):
        data.to_csv(results_file, index=False)
    else:
        data.to_csv(results_file, mode='a', header=False, index=False)