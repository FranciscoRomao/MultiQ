import argparse
import os
import sys
import time
from dataclasses import dataclass

# Same dual-invocation shim as run_evaluation.py: supports both
# `python scripts/run_preeval.py` (from repo root) and
# `python -m scripts.run_preeval` (from repo root). See that file's header
# comment for why both sys.path entries are needed.
_scripts_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _scripts_dir)
sys.path.insert(0, os.path.dirname(_scripts_dir))

import pdb
import yaml
import numpy as np
import pandas as pd
import csv
import json
import warnings
from baselines.zac_runner import run_zac_single_benchmarks, run_zac, merge_circuits
from baselines.atomique_runner import run_atomique_single_benchmarks, ATOMIQUE_TIMEOUT
from qiskit import transpile, QuantumCircuit
from tools.gen_benchmarks import single_random_NA_circuit, gen_random_NA_circuits, merge_circuits_from_qasm, save_circuit, gen_single_benchmarks
from framework.grid import Grid #This is pachinqo
import eval_functions as ppfunctions
from plotting import utils, bar_plot, defaults
from matplotlib import gridspec, figure
import matplotlib.pyplot as plt


def _progress(msg):
    # Long sweeps (potentially hours, especially through Atomique) otherwise
    # print nothing per-benchmark -- every progress line gets a wall-clock
    # timestamp so a stalled/hung run is visible from the gap between
    # timestamps, not just silence.
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

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

def run_preeval_pachinqo():
    circuit_sizes = [10, 25]
    depths = [10, 25]
    #circuit_sizes = [8]
    #benchmarks = ["ghz", "wstate", "dj", "grover-noancilla"]
    #benchmarks = ["ghz", "wstate", "dj"]
    circuits_per_size = 3
    benchmark_sets = []

    dir = "data/benchmarks/random/"

    print("Generating single benchmarks...")
    benchmark_sets = gen_random_NA_circuits(circuit_sizes, depths=depths, regen=False, ncircuits_per_size=circuits_per_size, output_folder=dir)
    #benchmark_sets += gen_single_benchmarks(circuit_sizes, benchmarks, regen=True)

    dir = "data/benchmarks/random/"

    print("Generating joint benchmarks...")
    np.random.seed(42)
    benchgroups = np.random.choice([f"random{j}-10.qasm" for j in range(circuits_per_size)], (circuits_per_size, 2))

    for i in benchgroups:
        benchmark_sets.append(merge_circuits_from_qasm(i, output_dir=dir))

    #benchmark_sets += gen_joint_benchmarks(benchgroups, [[10]*2]*circuits_per_size, folder=dir)

    for index,i in enumerate(circuit_sizes[1:]):
        benchgroups = np.random.choice([f"random{j}-{i}.qasm" for j in range(circuits_per_size)], (circuits_per_size, 2))
        for group in benchgroups:
            benchmark_sets.append(merge_circuits_from_qasm(group, output_dir=dir))

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
        name = 'data/benchmarks/transpiled/' + algo.split('/')[-1].split('.')[0] + "_transpiled.qasm"
        nqubits = sum(int(i) for  i in algo.split('/')[-1].split('-')[1].split('.')[0].split('_'))

        transpiled_circuit = QuantumCircuit.from_qasm_file(algo)
        nqubits = transpiled_circuit.num_qubits
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
                {'type': 'StorageZone', 'bottom_left_x': 0, 'bottom_left_y': 0, 'width': 230, 'height': 100},
                {'type': 'EntanglementZone', 'bottom_left_x': 62, 'bottom_left_y': 120, 'width': 100, 'height': 35, 'col_size': 4},
                {'type': 'ReadoutZone', 'bottom_left_x': 0, 'bottom_left_y': 120, 'width': 42, 'height': 35},
                {'type': 'ReadoutZone', 'bottom_left_x': 182, 'bottom_left_y': 120, 'width': 42, 'height':35}
        ]
        #zone_specs = [
        #    {'type': 'StorageZone', 'bottom_left_x': 90, 'bottom_left_y': 0, 'width': 190, 'height': 50},
        #    {'type': 'EntanglementZone', 'bottom_left_x': 90, 'bottom_left_y': 60, 'width': 190, 'height': 130, 'col_size': 4},
        #    {'type': 'ReadoutZone', 'bottom_left_x': 0, 'bottom_left_y': 60, 'width': 80, 'height': 130},
        #    {'type': 'ReadoutZone', 'bottom_left_x': 290, 'bottom_left_y': 60, 'width': 80, 'height':130}
        #]
        grid = Grid(zone_specs, 0, name, num_atoms=250)
        ret_vals = grid.return_vals()

        total_fidelity, total_transfer_fidelity, total_coherence_fidelity, total_1q_fidelity, total_2q_fidelity, cir_shuttling_time, execution_time, total_transfer_fidelity = compute_fidelity(ret_vals, nqubits)

        data.loc[len(data)] = [algo.split('/')[-1].split('.')[0].split('_')[0],
                                nqubits,
                                total_fidelity,
                                ret_vals[3],
                                total_1q_fidelity,
                                total_2q_fidelity,
                                total_coherence_fidelity,
                                total_transfer_fidelity,
                                cir_shuttling_time,
                                execution_time]

    if not os.path.isfile(f"results/preeval/pachinqo_preeval.csv"):
        data.to_csv(f"results/preeval/pachinqo_preeval.csv", index=False)
    else:
        data.to_csv(f"results/preeval/pachinqo_preeval.csv", mode='a', header=False, index=False)

def run_preeval_zac():
    # Running merged benchmarks

    circuit_sizes = [10, 25, 50, 100, 150, 200, 250]
    depths = [10, 25, 50, 100, 150, 200, 250]
    #circuit_sizes = [8]
    #benchmarks = ["ghz", "wstate", "dj", "grover-noancilla"]
    benchmarks = ["ghz", "wstate", "dj"]
    circuits_per_size = 3
    benchmark_sets = []

    dir = "data/benchmarks/single/"

    print("Generating single benchmarks...")
    #benchmark_sets = gen_random_NA_circuits(circuit_sizes, depths=depths, regen=False, ncircuits_per_size=circuits_per_size, output_folder=dir)
    benchmark_sets += gen_single_benchmarks(circuit_sizes, benchmarks, regen=True)

    #dir = "data/benchmarks/random/"

    #print("Generating joint benchmarks...")
    #np.random.seed(42)
    #benchgroups = np.random.choice([f"random{j}-10.qasm" for j in range(circuits_per_size)], (circuits_per_size, 2))
    #
    #for i in benchgroups:
    #    benchmark_sets.append(merge_circuits_from_qasm(i, output_dir=dir))

    #benchmark_sets += gen_joint_benchmarks(benchgroups, [[10]*2]*circuits_per_size, folder=dir)

    #for index,i in enumerate(circuit_sizes[1:]):
    #    benchgroups = np.random.choice([f"random{j}-{i}.qasm" for j in range(circuits_per_size)], (circuits_per_size, 2))
    #    for group in benchgroups:
    #        benchmark_sets.append(merge_circuits_from_qasm(group, output_dir=dir))

    settings_file = 'config/zac/general.json'
    output_file = 'results/preeval/zac_preeval.csv'

    data = pd.DataFrame(columns=['benchmark',
                                 'nqubits',
                                 'total_fidelity',
                                 'total_coherence_fidelity'])

    for benchmark in benchmark_sets:

             # Run the ZAC compiler
            benchmark = benchmark.split('/')[-1]
            benchmark = os.path.join(os.path.dirname(__file__), '../', dir, benchmark)
            
            info = run_zac_single_benchmarks(benchmark, settings_file, output_file)

            print(f"Processing benchmark: {benchmark}")

            fid_file = os.path.join('results/zac/fidelity', f'{benchmark.split(".")[0].split("/")[-1]}.json')
            time_file = os.path.join('results/zac/time', f'{benchmark.split(".")[0].split("/")[-1]}.json')

            fid_res = pd.read_json(fid_file, typ='series')
            time_res = pd.read_json(time_file, typ='series')

            circuit = QuantumCircuit.from_qasm_file(benchmark)
            nqubits = circuit.num_qubits

            data.loc[len(data)] = [benchmark.split('.')[0],
                                   nqubits,
                                   fid_res['cir_fidelity'],
                                   fid_res['cir_fidelity_coherence']]

            results_file = os.path.join('results/zac/', f'{benchmark.split(".")[0].split("/")[-1]}.csv')

            if not os.path.isfile(results_file):
                data.to_csv(results_file, index=False)
            else:
                data.to_csv(results_file, mode='a', header=False, index=False)

def run_zac_layout_preeval():
    #from compilers.atomique.benchmarks.benchmark_set import BenchmarkSets
    #from compilers.atomique.hyperparams import HyperParamSets
    #from compilers.atomique.utils import count_1q_2q_gates, get_n2q_interation_stats
    #from tools.gen_benchmarks import gen_single_benchmarks, gen_joint_benchmarks
    from tools.gen_benchmarks import gen_single_benchmarks
    from baselines.zac_runner import run_zac_preeval

    data = pd.DataFrame(columns=['benchmark',
                                 'nqubits',
                                 'total_fidelity',
                                 'compilation_time',
                                 'total_1q_fidelity',
                                 'total_2q_fidelity',
                                 'total_coherence_fidelity',
                                 'total_transfer_fidelity',
                                 'total_2q_on_idle',
                                 'cir_shuttling_time',
                                 'execution_time',
                                 'ratio',])

    settings_file = f'config/zac/preeval_layouts.json'
    arch_spec_file = f'config/zac/preeval_layouts_arch.json'

    # ---------------
    # Size 25 ratio 1:1 storage + 30% of # of storage atoms on entanglement, same width as storage
    circuit_size = 25
    benchmark_sets = []
    benchmark_sets_bak = benchmark_sets
    benchmarks = ["ghz", "wstate"]
    benchmark_sets += gen_single_benchmarks([circuit_size], benchmarks, regen=True)
    print(f"Benchmark sets:{benchmark_sets}")
    ratio = '1_1'
    settings = json.load(open(settings_file, 'r'))
    layout_name = f'preeval_layouts_{circuit_size}_{ratio}'
    settings['zac_setting'][0]['arch_spec'] = arch_spec_file
    settings['zac_setting'][0]['dir'] = f'results/preeval/{layout_name}/'
    json.dump(settings, open(settings_file, 'w'), indent=2)

    arch_spec = json.load(open(settings['zac_setting'][0]['arch_spec'], 'r'))

    arch_spec['storage_zones'][0]['slms'][0]['c'] = 5
    arch_spec['storage_zones'][0]['slms'][0]['r'] = 5

    arch_spec['entanglement_zones'][0]['slms'][0]['c'] = 2
    arch_spec['entanglement_zones'][0]['slms'][0]['r'] = 2

    arch_spec['entanglement_zones'][0]['slms'][1]['c'] = 2
    arch_spec['entanglement_zones'][0]['slms'][1]['r'] = 2

    arch_spec['entanglement_zones'][0]['slms'][0]['location'] = [0, (arch_spec['storage_zones'][0]['slms'][0]['r']-1)*3 + 10]
    arch_spec['entanglement_zones'][0]['slms'][1]['location'] = [2, (arch_spec['storage_zones'][0]['slms'][0]['r']-1)*3 + 10]

    json.dump(arch_spec, open(settings['zac_setting'][0]['arch_spec'], 'w'), indent=2)

    print("Running ZAC...")
    benchmark_sets = [i.split('benchmarks/')[-1] for i in benchmark_sets]
    info = run_zac_preeval(benchmark_sets, settings_file)
    print(benchmark_sets)
    print(info)

    for i, benchmark in enumerate(benchmark_sets_bak):

        fid_res = pd.read_json(f"results/preeval/{layout_name}/fidelity/{benchmark.split('/')[-1]}_fidelity.json", typ='series')
        time_res = pd.read_json(f"results/preeval/{layout_name}/time/{benchmark.split('/')[-1]}_time.json", typ='series')

        data.loc[len(data)] = [benchmark.split('/')[-1].split('.')[0].split('-')[0],
                               info['nqubits'][i],
                               fid_res['cir_fidelity'],
                               time_res['total'],
                               fid_res['cir_fidelity_1q_gate'],
                               fid_res['cir_fidelity_2q_gate'],
                               fid_res['cir_fidelity_coherence'],
                               fid_res['cir_fidelity_atom_transfer'],
                               fid_res['cir_fidelity_2q_gate_for_idle'],
                               fid_res['cir_shuttling_time'],
                               fid_res['cir_duration'],
                               ratio]
    #----------------
    # Size 25 ration 1 width : 4 height storage + 30% entanglement

    circuit_size = 25
    benchmark_sets = []
    benchmark_sets_bak = benchmark_sets
    benchmarks = ["ghz", "wstate"]
    benchmark_sets += gen_single_benchmarks([circuit_size], benchmarks, regen=True)
    print(f"Benchmark sets:{benchmark_sets}")
    ratio = '1_4'
    settings = json.load(open(settings_file, 'r'))
    layout_name = f'preeval_layouts_{circuit_size}_{ratio}'
    settings['zac_setting'][0]['arch_spec'] = arch_spec_file
    settings['zac_setting'][0]['dir'] = f'results/preeval/{layout_name}/'
    json.dump(settings, open(settings_file, 'w'), indent=2)

    arch_spec = json.load(open(settings['zac_setting'][0]['arch_spec'], 'r'))

    arch_spec['storage_zones'][0]['slms'][0]['c'] = 3
    arch_spec['storage_zones'][0]['slms'][0]['r'] = 9

    arch_spec['entanglement_zones'][0]['slms'][0]['c'] = 1
    arch_spec['entanglement_zones'][0]['slms'][0]['r'] = 4

    arch_spec['entanglement_zones'][0]['slms'][1]['c'] = 1
    arch_spec['entanglement_zones'][0]['slms'][1]['r'] = 4

    arch_spec['entanglement_zones'][0]['slms'][0]['location'] = [0, (arch_spec['storage_zones'][0]['slms'][0]['r']-1)*3 + 10]
    arch_spec['entanglement_zones'][0]['slms'][1]['location'] = [2, (arch_spec['storage_zones'][0]['slms'][0]['r']-1)*3 + 10]

    json.dump(arch_spec, open(settings['zac_setting'][0]['arch_spec'], 'w'), indent=2)

    print("Running ZAC...")
    benchmark_sets = [i.split('benchmarks/')[-1] for i in benchmark_sets]
    info = run_zac_preeval(benchmark_sets, settings_file)
    print(benchmark_sets)
    print(info)

    for i, benchmark in enumerate(benchmark_sets_bak):

        fid_res = pd.read_json(f"results/preeval/{layout_name}/fidelity/{benchmark.split('/')[-1]}_fidelity.json", typ='series')
        time_res = pd.read_json(f"results/preeval/{layout_name}/time/{benchmark.split('/')[-1]}_time.json", typ='series')

        data.loc[len(data)] = [benchmark.split('/')[-1].split('.')[0].split('-')[0],
                               info['nqubits'][i],
                               fid_res['cir_fidelity'],
                               time_res['total'],
                               fid_res['cir_fidelity_1q_gate'],
                               fid_res['cir_fidelity_2q_gate'],
                               fid_res['cir_fidelity_coherence'],
                               fid_res['cir_fidelity_atom_transfer'],
                               fid_res['cir_fidelity_2q_gate_for_idle'],
                               fid_res['cir_shuttling_time'],
                               fid_res['cir_duration'],
                               ratio]

    #----------------
    # Size 25 ration 4 width : 1 height storage + 30% entanglement

    circuit_size = 25
    benchmark_sets = []
    benchmark_sets_bak = benchmark_sets
    benchmarks = ["ghz", "wstate"]
    benchmark_sets += gen_single_benchmarks([circuit_size], benchmarks, regen=True)
    print(f"Benchmark sets:{benchmark_sets}")

    settings = json.load(open(settings_file, 'r'))
    ratio = '4_1'
    layout_name = f'preeval_layouts_{circuit_size}_{ratio}'
    settings['zac_setting'][0]['arch_spec'] = arch_spec_file
    settings['zac_setting'][0]['dir'] = f'results/preeval/{layout_name}/'
    json.dump(settings, open(settings_file, 'w'), indent=2)

    arch_spec = json.load(open(settings['zac_setting'][0]['arch_spec'], 'r'))

    arch_spec['storage_zones'][0]['slms'][0]['c'] = 9
    arch_spec['storage_zones'][0]['slms'][0]['r'] = 3

    arch_spec['entanglement_zones'][0]['slms'][0]['c'] = 3
    arch_spec['entanglement_zones'][0]['slms'][0]['r'] = 2

    arch_spec['entanglement_zones'][0]['slms'][1]['c'] = 3
    arch_spec['entanglement_zones'][0]['slms'][1]['r'] = 2

    arch_spec['entanglement_zones'][0]['slms'][0]['location'] = [0, (arch_spec['storage_zones'][0]['slms'][0]['r']-1)*3 + 10]
    arch_spec['entanglement_zones'][0]['slms'][1]['location'] = [2, (arch_spec['storage_zones'][0]['slms'][0]['r']-1)*3 + 10]

    json.dump(arch_spec, open(settings['zac_setting'][0]['arch_spec'], 'w'), indent=2)

    print("Running ZAC...")
    benchmark_sets = [i.split('benchmarks/')[-1] for i in benchmark_sets]
    info = run_zac_preeval(benchmark_sets, settings_file)
    print(benchmark_sets)
    print(info)

    for i, benchmark in enumerate(benchmark_sets_bak):

        fid_res = pd.read_json(f"results/preeval/{layout_name}/fidelity/{benchmark.split('/')[-1]}_fidelity.json", typ='series')
        time_res = pd.read_json(f"results/preeval/{layout_name}/time/{benchmark.split('/')[-1]}_time.json", typ='series')

        data.loc[len(data)] = [benchmark.split('/')[-1].split('.')[0].split('-')[0],
                               info['nqubits'][i],
                               fid_res['cir_fidelity'],
                               time_res['total'],
                               fid_res['cir_fidelity_1q_gate'],
                               fid_res['cir_fidelity_2q_gate'],
                               fid_res['cir_fidelity_coherence'],
                               fid_res['cir_fidelity_atom_transfer'],
                               fid_res['cir_fidelity_2q_gate_for_idle'],
                               fid_res['cir_shuttling_time'],
                               fid_res['cir_duration'],
                               ratio]

    #----------------
    # Size 50 ratio 1 width : 1 height storage + 30% entanglement

    circuit_size = 50
    benchmark_sets = []
    benchmark_sets_bak = benchmark_sets
    benchmarks = ["ghz", "wstate"]
    benchmark_sets += gen_single_benchmarks([circuit_size], benchmarks, regen=True)
    print(f"Benchmark sets:{benchmark_sets}")

    settings = json.load(open(settings_file, 'r'))
    ratio = '1_1'
    layout_name = f'preeval_layouts_{circuit_size}_{ratio}'
    settings['zac_setting'][0]['arch_spec'] = arch_spec_file
    settings['zac_setting'][0]['dir'] = f'results/preeval/{layout_name}/'
    json.dump(settings, open(settings_file, 'w'), indent=2)

    arch_spec = json.load(open(settings['zac_setting'][0]['arch_spec'], 'r'))

    arch_spec['storage_zones'][0]['slms'][0]['c'] = 8
    arch_spec['storage_zones'][0]['slms'][0]['r'] = 8

    arch_spec['entanglement_zones'][0]['slms'][0]['c'] = 5
    arch_spec['entanglement_zones'][0]['slms'][0]['r'] = 3

    arch_spec['entanglement_zones'][0]['slms'][1]['c'] = 5
    arch_spec['entanglement_zones'][0]['slms'][1]['r'] = 3

    arch_spec['entanglement_zones'][0]['slms'][0]['location'] = [0, (arch_spec['storage_zones'][0]['slms'][0]['r']-1)*3 + 10]
    arch_spec['entanglement_zones'][0]['slms'][1]['location'] = [2, (arch_spec['storage_zones'][0]['slms'][0]['r']-1)*3 + 10]

    json.dump(arch_spec, open(settings['zac_setting'][0]['arch_spec'], 'w'), indent=2)

    print("Running ZAC...")
    benchmark_sets = [i.split('benchmarks/')[-1] for i in benchmark_sets]
    info = run_zac_preeval(benchmark_sets, settings_file)
    print(benchmark_sets)
    print(info)

    for i, benchmark in enumerate(benchmark_sets_bak):

        fid_res = pd.read_json(f"results/preeval/{layout_name}/fidelity/{benchmark.split('/')[-1]}_fidelity.json", typ='series')
        time_res = pd.read_json(f"results/preeval/{layout_name}/time/{benchmark.split('/')[-1]}_time.json", typ='series')

        data.loc[len(data)] = [benchmark.split('/')[-1].split('.')[0].split('-')[0],
                               info['nqubits'][i],
                               fid_res['cir_fidelity'],
                               time_res['total'],
                               fid_res['cir_fidelity_1q_gate'],
                               fid_res['cir_fidelity_2q_gate'],
                               fid_res['cir_fidelity_coherence'],
                               fid_res['cir_fidelity_atom_transfer'],
                               fid_res['cir_fidelity_2q_gate_for_idle'],
                               fid_res['cir_shuttling_time'],
                               fid_res['cir_duration'],
                               ratio]

    #----------------
    # Size 50 ratio 1 width : 4 height storage + 30% entanglement

    circuit_size = 50
    benchmark_sets = []
    benchmark_sets_bak = benchmark_sets
    benchmarks = ["ghz", "wstate"]
    benchmark_sets += gen_single_benchmarks([circuit_size], benchmarks, regen=True)
    print(f"Benchmark sets:{benchmark_sets}")

    settings = json.load(open(settings_file, 'r'))
    ratio = '1_4'
    layout_name = f'preeval_layouts_{circuit_size}_{ratio}'
    settings['zac_setting'][0]['arch_spec'] = arch_spec_file
    settings['zac_setting'][0]['dir'] = f'results/preeval/{layout_name}/'
    json.dump(settings, open(settings_file, 'w'), indent=2)

    arch_spec = json.load(open(settings['zac_setting'][0]['arch_spec'], 'r'))

    arch_spec['storage_zones'][0]['slms'][0]['c'] = 4
    arch_spec['storage_zones'][0]['slms'][0]['r'] = 13

    arch_spec['entanglement_zones'][0]['slms'][0]['c'] = 5
    arch_spec['entanglement_zones'][0]['slms'][0]['r'] = 3

    arch_spec['entanglement_zones'][0]['slms'][1]['c'] = 5
    arch_spec['entanglement_zones'][0]['slms'][1]['r'] = 3

    arch_spec['entanglement_zones'][0]['slms'][0]['location'] = [0, (arch_spec['storage_zones'][0]['slms'][0]['r']-1)*3 + 10]
    arch_spec['entanglement_zones'][0]['slms'][1]['location'] = [2, (arch_spec['storage_zones'][0]['slms'][0]['r']-1)*3 + 10]

    json.dump(arch_spec, open(settings['zac_setting'][0]['arch_spec'], 'w'), indent=2)

    print("Running ZAC...")
    benchmark_sets = [i.split('benchmarks/')[-1] for i in benchmark_sets]
    info = run_zac_preeval(benchmark_sets, settings_file)
    print(benchmark_sets)
    print(info)

    for i, benchmark in enumerate(benchmark_sets_bak):

        fid_res = pd.read_json(f"results/preeval/{layout_name}/fidelity/{benchmark.split('/')[-1]}_fidelity.json", typ='series')
        time_res = pd.read_json(f"results/preeval/{layout_name}/time/{benchmark.split('/')[-1]}_time.json", typ='series')

        data.loc[len(data)] = [benchmark.split('/')[-1].split('.')[0].split('-')[0],
                               info['nqubits'][i],
                               fid_res['cir_fidelity'],
                               time_res['total'],
                               fid_res['cir_fidelity_1q_gate'],
                               fid_res['cir_fidelity_2q_gate'],
                               fid_res['cir_fidelity_coherence'],
                               fid_res['cir_fidelity_atom_transfer'],
                               fid_res['cir_fidelity_2q_gate_for_idle'],
                               fid_res['cir_shuttling_time'],
                               fid_res['cir_duration'],
                               ratio]

    #----------------
    # Size 50 ratio 4 width : 1 height storage + 30% entanglement

    circuit_size = 50
    benchmark_sets = []
    benchmark_sets_bak = benchmark_sets
    benchmarks = ["ghz", "wstate"]
    benchmark_sets += gen_single_benchmarks([circuit_size], benchmarks, regen=True)
    print(f"Benchmark sets:{benchmark_sets}")

    settings = json.load(open(settings_file, 'r'))
    ratio = '4_1'
    layout_name = f'preeval_layouts_{circuit_size}_{ratio}'
    settings['zac_setting'][0]['arch_spec'] = arch_spec_file
    settings['zac_setting'][0]['dir'] = f'results/preeval/{layout_name}/'
    json.dump(settings, open(settings_file, 'w'), indent=2)

    arch_spec = json.load(open(settings['zac_setting'][0]['arch_spec'], 'r'))

    arch_spec['storage_zones'][0]['slms'][0]['c'] = 13
    arch_spec['storage_zones'][0]['slms'][0]['r'] = 4

    arch_spec['entanglement_zones'][0]['slms'][0]['c'] = 5
    arch_spec['entanglement_zones'][0]['slms'][0]['r'] = 3

    arch_spec['entanglement_zones'][0]['slms'][1]['c'] = 5
    arch_spec['entanglement_zones'][0]['slms'][1]['r'] = 3

    arch_spec['entanglement_zones'][0]['slms'][0]['location'] = [0, (arch_spec['storage_zones'][0]['slms'][0]['r']-1)*3 + 10]
    arch_spec['entanglement_zones'][0]['slms'][1]['location'] = [2, (arch_spec['storage_zones'][0]['slms'][0]['r']-1)*3 + 10]

    json.dump(arch_spec, open(settings['zac_setting'][0]['arch_spec'], 'w'), indent=2)

    print("Running ZAC...")
    benchmark_sets = [i.split('benchmarks/')[-1] for i in benchmark_sets]
    info = run_zac_preeval(benchmark_sets, settings_file)
    print(benchmark_sets)
    print(info)

    for i, benchmark in enumerate(benchmark_sets_bak):

        fid_res = pd.read_json(f"results/preeval/{layout_name}/fidelity/{benchmark.split('/')[-1]}_fidelity.json", typ='series')
        time_res = pd.read_json(f"results/preeval/{layout_name}/time/{benchmark.split('/')[-1]}_time.json", typ='series')

        data.loc[len(data)] = [benchmark.split('/')[-1].split('.')[0].split('-')[0],
                               info['nqubits'][i],
                               fid_res['cir_fidelity'],
                               time_res['total'],
                               fid_res['cir_fidelity_1q_gate'],
                               fid_res['cir_fidelity_2q_gate'],
                               fid_res['cir_fidelity_coherence'],
                               fid_res['cir_fidelity_atom_transfer'],
                               fid_res['cir_fidelity_2q_gate_for_idle'],
                               fid_res['cir_shuttling_time'],
                               fid_res['cir_duration'],
                               ratio]
    #----------------
    # Size 100 ratio 1 width : 1 height storage

    circuit_size = 100
    benchmark_sets = []
    benchmark_sets_bak = benchmark_sets
    benchmarks = ["ghz", "wstate"]
    benchmark_sets += gen_single_benchmarks([circuit_size], benchmarks, regen=True)
    print(f"Benchmark sets:{benchmark_sets}")

    settings = json.load(open(settings_file, 'r'))
    ratio = '1_1'
    layout_name = f'preeval_layouts_{circuit_size}_{ratio}'
    settings['zac_setting'][0]['arch_spec'] = arch_spec_file
    settings['zac_setting'][0]['dir'] = f'results/preeval/{layout_name}/'
    json.dump(settings, open(settings_file, 'w'), indent=2)

    arch_spec = json.load(open(settings['zac_setting'][0]['arch_spec'], 'r'))

    arch_spec['storage_zones'][0]['slms'][0]['c'] = 10
    arch_spec['storage_zones'][0]['slms'][0]['r'] = 10

    arch_spec['entanglement_zones'][0]['slms'][0]['c'] = 6
    arch_spec['entanglement_zones'][0]['slms'][0]['r'] = 13

    arch_spec['entanglement_zones'][0]['slms'][1]['c'] = 6
    arch_spec['entanglement_zones'][0]['slms'][1]['r'] = 13

    arch_spec['entanglement_zones'][0]['slms'][0]['location'] = [0, (arch_spec['storage_zones'][0]['slms'][0]['r']-1)*3 + 10]
    arch_spec['entanglement_zones'][0]['slms'][1]['location'] = [2, (arch_spec['storage_zones'][0]['slms'][0]['r']-1)*3 + 10]

    json.dump(arch_spec, open(settings['zac_setting'][0]['arch_spec'], 'w'), indent=2)

    print("Running ZAC...")
    benchmark_sets = [i.split('benchmarks/')[-1] for i in benchmark_sets]
    info = run_zac_preeval(benchmark_sets, settings_file)
    print(benchmark_sets)
    print(info)

    for i, benchmark in enumerate(benchmark_sets_bak):

        fid_res = pd.read_json(f"results/preeval/{layout_name}/fidelity/{benchmark.split('/')[-1]}_fidelity.json", typ='series')
        time_res = pd.read_json(f"results/preeval/{layout_name}/time/{benchmark.split('/')[-1]}_time.json", typ='series')

        data.loc[len(data)] = [benchmark.split('/')[-1].split('.')[0].split('-')[0],
                               info['nqubits'][i],
                               fid_res['cir_fidelity'],
                               time_res['total'],
                               fid_res['cir_fidelity_1q_gate'],
                               fid_res['cir_fidelity_2q_gate'],
                               fid_res['cir_fidelity_coherence'],
                               fid_res['cir_fidelity_atom_transfer'],
                               fid_res['cir_fidelity_2q_gate_for_idle'],
                               fid_res['cir_shuttling_time'],
                               fid_res['cir_duration'],
                               ratio]

    #----------------
    # Size 100 ratio 1 width : 4 height storage

    circuit_size = 100
    benchmark_sets = []
    benchmark_sets_bak = benchmark_sets
    benchmarks = ["ghz", "wstate"]
    benchmark_sets += gen_single_benchmarks([circuit_size], benchmarks, regen=True)
    print(f"Benchmark sets:{benchmark_sets}")

    settings = json.load(open(settings_file, 'r'))
    ratio = '1_4'
    layout_name = f'preeval_layouts_{circuit_size}_{ratio}'
    settings['zac_setting'][0]['arch_spec'] = arch_spec_file
    settings['zac_setting'][0]['dir'] = f'results/preeval/{layout_name}/'
    json.dump(settings, open(settings_file, 'w'), indent=2)

    arch_spec = json.load(open(settings['zac_setting'][0]['arch_spec'], 'r'))

    arch_spec['storage_zones'][0]['slms'][0]['c'] = 5
    arch_spec['storage_zones'][0]['slms'][0]['r'] = 20

    arch_spec['entanglement_zones'][0]['slms'][0]['c'] = 6
    arch_spec['entanglement_zones'][0]['slms'][0]['r'] = 13

    arch_spec['entanglement_zones'][0]['slms'][1]['c'] = 6
    arch_spec['entanglement_zones'][0]['slms'][1]['r'] = 13

    arch_spec['entanglement_zones'][0]['slms'][0]['location'] = [0, (arch_spec['storage_zones'][0]['slms'][0]['r']-1)*3 + 10]
    arch_spec['entanglement_zones'][0]['slms'][1]['location'] = [2, (arch_spec['storage_zones'][0]['slms'][0]['r']-1)*3 + 10]

    json.dump(arch_spec, open(settings['zac_setting'][0]['arch_spec'], 'w'), indent=2)

    print("Running ZAC...")
    benchmark_sets = [i.split('benchmarks/')[-1] for i in benchmark_sets]
    info = run_zac_preeval(benchmark_sets, settings_file)
    print(benchmark_sets)
    print(info)

    for i, benchmark in enumerate(benchmark_sets_bak):

        fid_res = pd.read_json(f"results/preeval/{layout_name}/fidelity/{benchmark.split('/')[-1]}_fidelity.json", typ='series')
        time_res = pd.read_json(f"results/preeval/{layout_name}/time/{benchmark.split('/')[-1]}_time.json", typ='series')

        data.loc[len(data)] = [benchmark.split('/')[-1].split('.')[0].split('-')[0],
                               info['nqubits'][i],
                               fid_res['cir_fidelity'],
                               time_res['total'],
                               fid_res['cir_fidelity_1q_gate'],
                               fid_res['cir_fidelity_2q_gate'],
                               fid_res['cir_fidelity_coherence'],
                               fid_res['cir_fidelity_atom_transfer'],
                               fid_res['cir_fidelity_2q_gate_for_idle'],
                               fid_res['cir_shuttling_time'],
                               fid_res['cir_duration'],
                               ratio]


    #----------------
    # Size 100 ratio 4 width : 1 height storage

    circuit_size = 100
    benchmark_sets = []
    benchmark_sets_bak = benchmark_sets
    benchmarks = ["ghz", "wstate"]
    benchmark_sets += gen_single_benchmarks([circuit_size], benchmarks, regen=True)
    print(f"Benchmark sets:{benchmark_sets}")

    settings = json.load(open(settings_file, 'r'))
    ratio = '4_1'
    layout_name = f'preeval_layouts_{circuit_size}_{ratio}'
    settings['zac_setting'][0]['arch_spec'] = f'settings/preeval_layouts_arch.json'
    settings['zac_setting'][0]['dir'] = f'results/preeval/{layout_name}/'
    json.dump(settings, open(settings_file, 'w'), indent=2)

    arch_spec = json.load(open(settings['zac_setting'][0]['arch_spec'], 'r'))

    arch_spec['storage_zones'][0]['slms'][0]['c'] = 20
    arch_spec['storage_zones'][0]['slms'][0]['r'] = 5

    arch_spec['entanglement_zones'][0]['slms'][0]['c'] = 6
    arch_spec['entanglement_zones'][0]['slms'][0]['r'] = 13

    arch_spec['entanglement_zones'][0]['slms'][1]['c'] = 6
    arch_spec['entanglement_zones'][0]['slms'][1]['r'] = 13

    arch_spec['entanglement_zones'][0]['slms'][0]['location'] = [0, (arch_spec['storage_zones'][0]['slms'][0]['r']-1)*3 + 10]
    arch_spec['entanglement_zones'][0]['slms'][1]['location'] = [2, (arch_spec['storage_zones'][0]['slms'][0]['r']-1)*3 + 10]

    json.dump(arch_spec, open(settings['zac_setting'][0]['arch_spec'], 'w'), indent=2)

    print("Running ZAC...")
    benchmark_sets = [i.split('benchmarks/')[-1] for i in benchmark_sets]
    info = run_zac_preeval(benchmark_sets, settings_file)
    print(benchmark_sets)
    print(info)

    for i, benchmark in enumerate(benchmark_sets_bak):

        fid_res = pd.read_json(f"results/preeval/{layout_name}/fidelity/{benchmark.split('/')[-1]}_fidelity.json", typ='series')
        time_res = pd.read_json(f"results/preeval/{layout_name}/time/{benchmark.split('/')[-1]}_time.json", typ='series')

        data.loc[len(data)] = [benchmark.split('/')[-1].split('.')[0].split('-')[0],
                               info['nqubits'][i],
                               fid_res['cir_fidelity'],
                               time_res['total'],
                               fid_res['cir_fidelity_1q_gate'],
                               fid_res['cir_fidelity_2q_gate'],
                               fid_res['cir_fidelity_coherence'],
                               fid_res['cir_fidelity_atom_transfer'],
                               fid_res['cir_fidelity_2q_gate_for_idle'],
                               fid_res['cir_shuttling_time'],
                               fid_res['cir_duration'],
                               ratio]

    if not os.path.isfile(f"results/preeval_layouts/zac_results.csv"):
        data.to_csv(f"results/preeval/zac_results.csv", index=False)
    else:
        data.to_csv(f"results/preeval/zac_results.csv", mode='a', header=False, index=False)
'''

# ----- Data collection for the introduction/preeval figures -----
# Circuit sizes/types shared across ZAC/PachinQo/Atomique so the introduction
# figure's per-nqubits averaging (eval_functions.py's
# plot_*_vs_circuit_size_zac_pachinqo_atomique) lines up across compilers.
# 25-250 matches the "circuits from 25 to 250 qubits" range shown in the
# figure; data/benchmarks/single already has ghz/wstate/dj at every size.
PREEVAL_BENCH_TYPES = ["ghz", "wstate", "dj"]
PREEVAL_SIZES = [25, 50, 100, 150, 200, 250]
# Dedicated arch spec (not config/zac/general.json, which run_evaluation.py's
# already-verified e2e figures depend on) -- copied from the MultiQ checkout
# that produced the original introduction figure. Its storage/entanglement
# zones are considerably roomier (30x100 storage, 7x20x2 entanglement vs.
# general_arch.json's 36x77/4x22x2), which is why fidelity here is much
# higher than what config/zac/general.json alone would produce.
ZAC_SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "..", "config/zac/preeval_general.json")


def _single_benchmark_path(bench_type, size):
    return f"single/{bench_type}-{size}.qasm"


def _zac_shuttling_time_us(name):
    """Sums the physical atom-transport ('move') sub-instruction durations out
    of ZAC's compiled-circuit code JSON (results/zac/code/{name}.json, written
    by run_zac() alongside the fidelity/time JSONs). cir_duration (used for
    "execution_time" below) is the whole schedule's makespan -- gate
    instructions and rearrangeJob (atom pick-up/move/drop) instructions can
    overlap in it -- so it isn't the circuit's actual shuttling time and
    roughly doubles it. This isolates just the 'move' sub-instructions'
    time so the "Shuttling time" panel plots what its label says."""
    code = json.load(open(f"results/zac/code/{name}.json"))
    return sum(
        sub["end_time"] - sub["begin_time"]
        for instr in code["instructions"] if instr["type"] == "rearrangeJob"
        for sub in instr["insts"] if sub["type"].split(":")[0] == "move"
    )


def _compile_zac_solo(bench_type, size):
    """Compiles one solo benchmark with ZAC and returns its fidelity/duration.
    Used both for run_preeval_zac()'s displayed solo ("Single") sweep and,
    at PREEVAL_ZAC_GROUP_SUBCIRCUIT_SIZE, as the per-sub-circuit baseline
    the "Grouped"/"Grouped Independent" rows are built from."""
    bench_file = _single_benchmark_path(bench_type, size)
    name = f"{bench_type}-{size}"
    _progress(f"[zac] compiling {bench_file}")
    run_zac([bench_file], ZAC_SETTINGS_FILE)

    fid = json.load(open(f"results/zac/fidelity/{name}.json"))
    # cir_duration (from the fidelity/simulation json) is the compiled
    # circuit's own execution duration, matching the "execution_time"
    # PachinQo/Atomique report -- NOT results/zac/time/{name}.json's
    # "total", which is the *compiler's* wall-clock placement/routing time.
    # Stored raw (not pre-divided by 1000) since the plotting functions do
    # their own us->ms conversion, same as PachinQo's raw-microsecond
    # execution_time column.
    return {
        "total_fidelity": fid["cir_fidelity"],
        "total_coherence_fidelity": fid["cir_fidelity_coherence"],
        "execution_time": fid["cir_duration"],
        "shuttling_time": _zac_shuttling_time_us(name),
    }


# The original introduction/preeval figure's "Grouped" sweep (see the
# vendored ~/tmp_MultiQ/results/zac_results.csv this was reconstructed from)
# keeps each sub-circuit at a FIXED size and increases QPU utilization by
# packing more of them onto the chip together, rather than growing one
# pair of circuits -- e.g. its 100%-utilization "Grouped" rows are combos
# of ten 25-qubit circuits (dj_ghz_dj_dj_wstate_dj_wstate_wstate_wstate_dj,
# etc.), not one pair of 125-qubit circuits. That distinction matters here:
# "Grouped Independent" (each sub-circuit run with the whole chip to itself,
# no cross-circuit contention -- see run_preeval_zac()) is the max of the
# *sub-circuits' own* solo time, so keeping that sub-circuit size fixed and
# small is why it stays low and roughly flat across utilization in the
# reference figure, instead of scaling up with utilization like the other
# two bars.
PREEVAL_ZAC_GROUP_SUBCIRCUIT_SIZE = 25
# Sub-circuit counts landing on the same utilization points (20/40/60/80/
# 100%, i.e. 50/100/150/200/250 qubits at the fixed 25-qubit sub-circuit
# size) as the "Single" sweep, so every utilization level shows all 3 bar
# types matching the reference figure (no gaps).
PREEVAL_ZAC_GROUP_COUNTS = [2, 4, 6, 8, 10]
# Multiple random (with-replacement) sub-circuit-type combos per count, for
# averaging -- the reference data has several distinct combos per
# utilization level (e.g. "dj_ghz_dj_dj_wstate_dj_wstate_wstate_wstate_dj"
# alongside other 10-circuit draws) rather than just one.
PREEVAL_ZAC_GROUP_COMBOS_PER_COUNT = 3


def run_preeval_zac():
    """
    Populates results/preeval/zac_preeval.csv with one row per (type, size)
    solo compile (type='Single') plus, per PREEVAL_ZAC_GROUP_COUNTS entry,
    PREEVAL_ZAC_GROUP_COMBOS_PER_COUNT 'Grouped' rows (one merged combo of
    that many PREEVAL_ZAC_GROUP_SUBCIRCUIT_SIZE-qubit circuits) each paired
    with a 'Grouped Independent' row (max of the combo's own sub-circuits'
    solo execution/shuttling times -- i.e. running them fully in parallel
    with no shared-hardware contention, as opposed to 'Grouped' actually
    sharing the chip). Feeds both the introduction figure (Single rows,
    averaged with PachinQo/Atomique per nqubits) and the preeval figure's
    ZAC-only shuttling-vs-utilization panel (which uses the 'shuttling_time'
    column, not 'execution_time' -- see _zac_shuttling_time_us).
    """
    all_sizes = sorted(set(PREEVAL_SIZES) | {PREEVAL_ZAC_GROUP_SUBCIRCUIT_SIZE})
    gen_single_benchmarks(all_sizes, PREEVAL_BENCH_TYPES, regen=False)

    rows = []
    solo_execution_time = {}  # (type, size) -> execution_time [us]
    solo_shuttling_time = {}  # (type, size) -> shuttling_time [us]

    for size in PREEVAL_SIZES:
        for bench_type in PREEVAL_BENCH_TYPES:
            result = _compile_zac_solo(bench_type, size)
            solo_execution_time[(bench_type, size)] = result["execution_time"]
            solo_shuttling_time[(bench_type, size)] = result["shuttling_time"]
            rows.append({"benchmark": bench_type, "nqubits": size, "type": "Single", **result})

    # PREEVAL_ZAC_GROUP_SUBCIRCUIT_SIZE (25) is already in PREEVAL_SIZES, so
    # its solo compile -- needed below as the "Grouped Independent"
    # baseline -- is already covered by the loop above.
    base_size = PREEVAL_ZAC_GROUP_SUBCIRCUIT_SIZE

    os.makedirs(os.path.join(os.path.dirname(__file__), "../data/benchmarks/merged"), exist_ok=True)
    rng = np.random.RandomState(0)
    for count in PREEVAL_ZAC_GROUP_COUNTS:
        for combo_idx in range(PREEVAL_ZAC_GROUP_COMBOS_PER_COUNT):
            combo = list(rng.choice(PREEVAL_BENCH_TYPES, size=count))
            merged_name = f"{'_'.join(combo)}-{combo_idx}"
            circuits = [
                QuantumCircuit.from_qasm_file(f"data/benchmarks/{_single_benchmark_path(t, base_size)}")
                for t in combo
            ]
            save_circuit(merge_circuits(circuits), f"data/benchmarks/merged/{merged_name}.qasm")

            _progress(f"[zac] compiling merged/{merged_name}.qasm ({combo})")
            run_zac([f"merged/{merged_name}.qasm"], ZAC_SETTINGS_FILE)

            fid = json.load(open(f"results/zac/fidelity/{merged_name}.json"))
            grouped_time = fid["cir_duration"]
            grouped_shuttling_time = _zac_shuttling_time_us(merged_name)

            common = {
                "benchmark": "_".join(combo),
                "nqubits": base_size * count,
                "total_fidelity": fid["cir_fidelity"],
                "total_coherence_fidelity": fid["cir_fidelity_coherence"],
            }
            rows.append({**common, "type": "Grouped", "execution_time": grouped_time,
                         "shuttling_time": grouped_shuttling_time})
            rows.append({
                **common,
                "type": "Grouped Independent",
                "execution_time": max(solo_execution_time[(t, base_size)] for t in combo),
                "shuttling_time": max(solo_shuttling_time[(t, base_size)] for t in combo),
            })

    os.makedirs("results/preeval", exist_ok=True)
    pd.DataFrame(rows).to_csv("results/preeval/zac_preeval.csv", index=False)


def _pachinqo_compute_fidelity(returned_values, cir_qubits):
    # Matches the MultiQ checkout that produced the original introduction
    # figure (run_preeval_pachinqo.py's own compute_fidelity) exactly --
    # NOT scripts/baselines/pachinqo_runner.py's compute_fidelity, which
    # uses different gate fidelities/timings tuned for the e2e comparison.
    layers = returned_values[0]
    total_move_distance = returned_values[1]
    nsequential_transfers = returned_values[2]
    total_trap_changes = nsequential_transfers * cir_qubits

    gate_1q_fidelity = 0.999
    gate_2q_fidelity = 0.995
    gate_1q_time = 0.5  # us
    gate_2q_time = 0.2  # us
    decoherence_T2 = 1500000  # us
    transfer_time = 20  # us
    transfer_fid = 0.999
    move_speed = 0.55  # um/us

    total_transfer_fidelity = transfer_fid ** total_trap_changes
    total_transfer_time = transfer_time * nsequential_transfers
    total_shuttling_time = total_move_distance / move_speed
    total_idling_time = total_transfer_time + total_move_distance / move_speed
    total_decoherence_fidelity = np.exp(-total_idling_time / decoherence_T2)

    total_u3_gates = sum(len(layer[2]) for layer in layers)
    total_cz_gates = sum(len(layer[0]) for layer in layers)

    gate_1q_fidelity = gate_1q_fidelity ** total_u3_gates
    gate_2q_fidelity = gate_2q_fidelity ** total_cz_gates
    total_1q_time = gate_1q_time * total_u3_gates
    total_2q_time = gate_2q_time * total_cz_gates

    total_execution_time = total_transfer_time + total_move_distance / move_speed + total_1q_time + total_2q_time
    total_fidelity = gate_1q_fidelity * gate_2q_fidelity * total_transfer_fidelity * total_decoherence_fidelity

    return total_fidelity, total_execution_time


def run_preeval_pachinqo():
    """Populates results/preeval/pachinqo_preeval.csv, one row per (type, size).
    Self-contained (own zone_specs/num_atoms=250/compute_fidelity) rather than
    calling scripts/baselines/pachinqo_runner.run_pachiqo_single_benchmark --
    that function targets a 150-atom grid with different zone dimensions for
    the e2e comparison, which starved these circuits (0 fidelity by 100
    qubits) relative to the original introduction figure's 250-atom setup."""
    from baselines.pachinqo_runner import transpile_single_benchmark

    gen_single_benchmarks(PREEVAL_SIZES, PREEVAL_BENCH_TYPES, regen=False)

    zone_specs = [
        {'type': 'StorageZone', 'bottom_left_x': 90, 'bottom_left_y': 0, 'width': 190, 'height': 50},
        {'type': 'EntanglementZone', 'bottom_left_x': 90, 'bottom_left_y': 60, 'width': 190, 'height': 130, 'col_size': 4},
        {'type': 'ReadoutZone', 'bottom_left_x': 0, 'bottom_left_y': 60, 'width': 80, 'height': 130},
        {'type': 'ReadoutZone', 'bottom_left_x': 290, 'bottom_left_y': 60, 'width': 80, 'height': 130},
    ]

    rows = []
    for size in PREEVAL_SIZES:
        for bench_type in PREEVAL_BENCH_TYPES:
            bench_file = _single_benchmark_path(bench_type, size)
            _progress(f"[pachinqo] compiling {bench_file}")
            try:
                transpiled_path = transpile_single_benchmark(bench_file)
                grid = Grid(zone_specs, 0, transpiled_path, num_atoms=250)
                total_fidelity, execution_time = _pachinqo_compute_fidelity(grid.return_vals(), size)
                rows.append({"benchmark": bench_type, "nqubits": size,
                             "total_fidelity": total_fidelity, "execution_time": execution_time})
            except Exception as e:
                _progress(f"[pachinqo] {bench_file} failed ({e}); skipping")

    os.makedirs("results/preeval", exist_ok=True)
    pd.DataFrame(rows).to_csv("results/preeval/pachinqo_preeval.csv", index=False)


def run_preeval_atomique():
    """Populates results/preeval/atomique_preeval.csv, one row per (type, size).
    FPQAC's own partitioning/routing can be very slow on some circuit
    topologies (a 19-qubit hub-pattern circuit was observed taking 9+ minutes) --
    each compile is bounded by ATOMIQUE_TIMEOUT and skipped with a warning on
    timeout/failure rather than blocking the whole sweep."""
    gen_single_benchmarks(PREEVAL_SIZES, PREEVAL_BENCH_TYPES, regen=False)

    output_file = "results/preeval/atomique_preeval.csv"
    if os.path.isfile(output_file):
        os.remove(output_file)

    for size in PREEVAL_SIZES:
        for bench_type in PREEVAL_BENCH_TYPES:
            bench_file = _single_benchmark_path(bench_type, size)
            _progress(f"[atomique] compiling {bench_file}")
            try:
                run_atomique_single_benchmarks(bench_file, output_file, timeout=ATOMIQUE_TIMEOUT)
            except (RuntimeError, TimeoutError) as e:
                _progress(f"[atomique] {bench_file} failed ({e}); skipping")


def run_preeval_introduction_data():
    run_preeval_zac()
    run_preeval_pachinqo()
    run_preeval_atomique()


def run_zac_layout_preeval():
    # Sweeps 3 storage-zone layout ratios (1:1, 1:4, 4:1) at 2 circuit sizes,
    # feeding the preeval figure's fidelity-vs-layout-ratio panel. Restored
    # from the dead code above (2 bugs fixed: an arch_spec path that pointed
    # at a nonexistent "settings/" dir, and a results-file existence check
    # that looked at "results/preeval_layouts/..." while writing to
    # "results/preeval/...").
    data = pd.DataFrame(columns=['benchmark',
                                 'nqubits',
                                 'total_fidelity',
                                 'compilation_time',
                                 'total_1q_fidelity',
                                 'total_2q_fidelity',
                                 'total_coherence_fidelity',
                                 'total_transfer_fidelity',
                                 'total_2q_on_idle',
                                 'execution_time',
                                 'ratio',])

    settings_file = 'config/zac/preeval_layouts.json'
    arch_spec_file = 'config/zac/preeval_layouts_arch.json'
    benchmarks = ["ghz", "wstate"]

    # (circuit_size, ratio, storage rows/cols, entanglement rows/cols)
    sweep = [
        (25, '1_1', (5, 5), (2, 2)),
        (25, '1_4', (9, 3), (4, 1)),
        (25, '4_1', (3, 9), (2, 3)),
        (50, '1_1', (8, 8), (3, 5)),
        (50, '1_4', (13, 4), (3, 5)),
        (50, '4_1', (4, 13), (3, 5)),
        (100, '1_1', (10, 10), (13, 6)),
        (100, '1_4', (20, 5), (13, 6)),
        (100, '4_1', (5, 20), (13, 6)),
    ]

    for circuit_size, ratio, (storage_r, storage_c), (ent_r, ent_c) in sweep:
        gen_single_benchmarks([circuit_size], benchmarks, regen=False)
        benchmark_paths = [_single_benchmark_path(b, circuit_size) for b in benchmarks]
        _progress(f"[zac layouts] size={circuit_size} ratio={ratio}: {benchmark_paths}")

        settings = json.load(open(settings_file, 'r'))
        settings['zac_setting'][0]['arch_spec'] = arch_spec_file
        json.dump(settings, open(settings_file, 'w'), indent=2)

        arch_spec = json.load(open(arch_spec_file, 'r'))
        arch_spec['storage_zones'][0]['slms'][0]['r'] = storage_r
        arch_spec['storage_zones'][0]['slms'][0]['c'] = storage_c
        arch_spec['entanglement_zones'][0]['slms'][0]['r'] = ent_r
        arch_spec['entanglement_zones'][0]['slms'][0]['c'] = ent_c
        arch_spec['entanglement_zones'][0]['slms'][1]['r'] = ent_r
        arch_spec['entanglement_zones'][0]['slms'][1]['c'] = ent_c
        arch_spec['entanglement_zones'][0]['slms'][0]['location'] = [0, (storage_r - 1) * 3 + 10]
        arch_spec['entanglement_zones'][0]['slms'][1]['location'] = [2, (storage_r - 1) * 3 + 10]
        json.dump(arch_spec, open(arch_spec_file, 'w'), indent=2)

        # run_zac() always writes to the fixed results/zac/{fidelity,time}/
        # location (it creates zac_setting['dir'] but never actually writes
        # there -- see run_zac's own body), so read from there, immediately
        # after each compile so the next ratio's overwrite can't race it.
        run_zac(benchmark_paths, settings_file)

        for bench_type in benchmarks:
            name = f"{bench_type}-{circuit_size}"
            fid_res = pd.read_json(f"results/zac/fidelity/{name}.json", typ='series')
            time_res = pd.read_json(f"results/zac/time/{name}.json", typ='series')

            data.loc[len(data)] = [bench_type,
                                   circuit_size,
                                   fid_res['cir_fidelity'],
                                   time_res['total'],
                                   fid_res['cir_fidelity_1q_gate'],
                                   fid_res['cir_fidelity_2q_gate'],
                                   fid_res['cir_fidelity_coherence'],
                                   fid_res['cir_fidelity_atom_transfer'],
                                   fid_res['cir_fidelity_2q_gate_for_idle'],
                                   fid_res['cir_duration'],
                                   ratio]

    os.makedirs("results/preeval", exist_ok=True)
    data.to_csv("results/preeval/zac_results.csv", index=False)


def run_preeval_data():
    run_preeval_zac()
    run_zac_layout_preeval()


# ----- Motivation / preliminary-eval plots -----
# Folded in from the former scripts/plot_preeval.py and
# scripts/introduction_plots.py, which ran as bare module-level code on
# import (not callable, not composable with a CLI) -- wrapped into functions
# here so they can be registered as experiments below.


def plot_preeval_motivation():
    # Was scripts/plot_preeval.py, originally a 4-panel figure (a layout
    # diagram, 2 unused axes, and a "framework runtime vs fidelity" scatter
    # referencing legend_handles_scatter/legend_labels_scatter that were
    # never actually assigned). Reduced to the 2 panels the current preeval
    # figure needs: ZAC-only shuttling time vs QPU utilization (Sequential /
    # Grouped / Grouped Independent, from run_preeval_zac's zac_preeval.csv),
    # and fidelity vs circuit size across storage-zone layout ratios (from
    # run_zac_layout_preeval's zac_results.csv).
    warnings.simplefilter(action='ignore', category=UserWarning)
    warnings.simplefilter(action='ignore', category=RuntimeWarning)
    warnings.simplefilter(action='ignore', category=FutureWarning)

    # Same figure geometry as the original ~/tmp_MultiQ/plot_preeval.py this
    # was reconstructed from: a compact (6.5, 3) figure, side by side
    # (fidelity-vs-layout-ratio on the left, shuttling-vs-utilization on the
    # right) with panel (a) narrower than (b) (width_ratios=[0.6, 1]) since
    # (a) only has 3 x-groups vs (b)'s 5. Single-column-width target for the
    # paper -- everything below (fonts, the two fig-level legends in place
    # of each axes drawing its own, tight_layout's rect/w_pad) is sized for
    # that same compact canvas, not the ~12in-wide look of this repo's
    # other multi-panel figures.
    fig = plt.figure(figsize=(6.5, 3))
    gs = gridspec.GridSpec(1, 2, figure=fig, width_ratios=[0.6, 1])
    ax0 = fig.add_subplot(gs[0])
    ax1 = fig.add_subplot(gs[1])

    ppfunctions.plot_fidelity_shuttling_times_vs_layout_width_zac(ax=ax0, title='(a) Fidelity vs Circuit size')
    ppfunctions.plot_shuttling_times_vs_utilization_zac(ax=ax1, title='(b) Shuttling time vs Utilization')

    # Both axes plot with legend=False -- rescale their text down to fit the
    # compact canvas, then build the two legends the original placed as
    # shared fig-level legends (not one per axes) so they can sit compactly
    # below the plots instead of eating into either panel's own area.
    for ax in (ax0, ax1):
        for t in (ax.title, ax._left_title, ax._right_title):
            t.set_fontsize(9)
        ax.xaxis.label.set_fontsize(8)
        ax.yaxis.label.set_fontsize(8)
        ax.tick_params(axis='both', labelsize=7)
        for txt in ax.texts:
            # "Compiler: ZAC" reads as a panel sub-heading, not a small
            # data-point annotation like the clipped-bar value label --
            # keep it close to title size rather than lumping it in with
            # the rest of this rescale pass.
            txt.set_fontsize(9 if txt.get_text() == 'Compiler: ZAC' else 7)

    ratio_handles, ratio_labels = ax0.get_legend_handles_labels()
    # The 'ratio' column's raw values ('1_4'/'4_1') aren't display-ready --
    # map them to the same labels the original figure showed.
    ratio_display_names = {'1_4': 'Ratio 1:4', '4_1': 'Ratio 4:1'}
    ratio_labels = [ratio_display_names.get(l, l) for l in ratio_labels]
    strategy_handles, strategy_labels = ax1.get_legend_handles_labels()

    fig.legend(handles=strategy_handles, labels=strategy_labels, loc='lower center',
               bbox_to_anchor=(0.72, 0.02), ncol=2, fontsize=8, frameon=True,
               title='Compilation strategy', title_fontsize=9, columnspacing=0.8)
    fig.legend(handles=ratio_handles, labels=ratio_labels, loc='lower left',
               bbox_to_anchor=(0.07, 0.07), ncol=2, fontsize=8, frameon=True,
               title='Layout ratio (width:height)', title_fontsize=9)

    fig.tight_layout(rect=(-0.02, 0.17, 1.01, 1.03), w_pad=0.4)

    os.makedirs("results/plots", exist_ok=True)
    fig.savefig('results/plots/preeval.pdf', format='pdf')


def plot_introduction_figures():
    # Was scripts/introduction_plots.py. Originally plotted all 3 of
    # fidelity/init-time/exec-time onto a single shared axis (utils.gen_subplots(1, 1, ...)
    # then 3 calls on that one ax) -- they'd all draw on top of each other.
    # Two panels stacked vertically sharing an x-axis (circuit size, 25-250
    # qubits): fidelity (with the 170-qubit/0.08-fidelity threshold
    # annotation) on top, execution time (with the matching "threshold
    # point" annotation) below -- matches the original figure's layout.
    fig, [ax0, ax1] = utils.gen_subplots(1, 2, figsize=(6, 5))

    ppfunctions.plot_fidelity_vs_circuit_size_zac_pachinqo_atomique(ax0, title='(a) Fidelity vs Circuit size')
    ppfunctions.plot_execution_time_vs_circuit_size_zac_pachinqo_atomique(ax1, title='(b) Execution time vs Circuit size')

    ax0.tick_params(axis='x', bottom=False, labelbottom=False)
    ax0.set_xlabel(None)

    fig.tight_layout(rect=(-0.02, 0.035, 1.03, 1.02), h_pad=0.4)

    fig.legend(loc='lower center', bbox_to_anchor=(0.52, -0.01), ncol=4, fontsize=12, frameon=True,
               labels=['ZAC', 'PachinQo', 'Atomique', 'Average'])

    os.makedirs("results/plots", exist_ok=True)
    fig.savefig('results/plots/introduction_plots.pdf', format='pdf')


@dataclass
class Experiment:
    name: str
    description: str
    data_fn: callable = None
    plot_fn: callable = None


EXPERIMENTS = [
    Experiment(
        "introduction",
        "Paper introduction/motivation figure (fidelity/exec-time vs. circuit size, ZAC/PachinQo/Atomique)",
        data_fn=run_preeval_introduction_data,
        plot_fn=plot_introduction_figures,
    ),
    Experiment(
        "preeval",
        "Preliminary-eval figure (ZAC shuttling time vs. QPU utilization; fidelity vs. storage-zone layout ratio)",
        data_fn=run_preeval_data,
        plot_fn=plot_preeval_motivation,
    ),
]


def _parse_args():
    parser = argparse.ArgumentParser(
        description="Regenerate MultiQ's introduction/motivation and preliminary-eval figures (results/preeval/*)."
    )
    parser.add_argument("--list", action="store_true", help="List available experiments and exit.")
    parser.add_argument("--all", action="store_true", help="Run every experiment (default behavior; explicit alias).")
    parser.add_argument(
        "--only", type=str, default=None, help="Comma-separated experiment names to run (default: all)."
    )
    parser.add_argument("--data-only", action="store_true", help="Only run data collection, skip plotting.")
    parser.add_argument(
        "--plots-only", action="store_true", help="Only (re)generate plots from existing results, skip data collection."
    )
    return parser.parse_args()


def main():
    args = _parse_args()

    if args.list:
        for exp in EXPERIMENTS:
            print(f"{exp.name:24s} {exp.description}")
        return

    if args.data_only and args.plots_only:
        raise SystemExit("--data-only and --plots-only are mutually exclusive")
    if args.all and args.only:
        raise SystemExit("--all and --only are mutually exclusive")

    selected_names = [n.strip() for n in args.only.split(",")] if args.only else None
    if selected_names:
        unknown = set(selected_names) - {exp.name for exp in EXPERIMENTS}
        if unknown:
            raise SystemExit(f"Unknown experiment(s): {', '.join(sorted(unknown))}. Use --list to see available names.")

    for exp in EXPERIMENTS:
        if selected_names is not None and exp.name not in selected_names:
            continue
        if exp.data_fn and not args.plots_only:
            print(f"=== [{exp.name}] collecting data ===")
            exp.data_fn()
        if exp.plot_fn and not args.data_only:
            print(f"=== [{exp.name}] plotting ===")
            exp.plot_fn()


if __name__ == "__main__":
    main()