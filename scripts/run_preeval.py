import argparse
import os
import sys
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
from baselines.zac_runner import run_zac_single_benchmarks
from qiskit import transpile, QuantumCircuit
from tools.gen_benchmarks import single_random_NA_circuit, gen_random_NA_circuits, merge_circuits_from_qasm, save_circuit, gen_single_benchmarks
from framework.grid import Grid #This is pachinqo
import eval_functions as ppfunctions
from plotting import utils, bar_plot, defaults
from matplotlib import gridspec, figure

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

# ----- Motivation / preliminary-eval plots -----
# Folded in from the former scripts/plot_preeval.py and
# scripts/introduction_plots.py, which ran as bare module-level code on
# import (not callable, not composable with a CLI) -- wrapped into functions
# here so they can be registered as experiments below.


'''
def plot_preeval_motivation():
    # Was scripts/plot_preeval.py. `legend_handles_scatter`/`legend_labels_scatter`
    # were referenced below without being defined -- the call that produces
    # them (into a third panel, ax3) was commented out. Restoring that call
    # (uncommenting `ax3` + the scatter-plot call it was clearly meant to
    # feed) since that's the only source of those variables in this file.
    warnings.simplefilter(action='ignore', category=UserWarning)
    warnings.simplefilter(action='ignore', category=RuntimeWarning)
    warnings.simplefilter(action='ignore', category=FutureWarning)

    fig = figure.Figure(figsize=(18, 6))
    gs = gridspec.GridSpec(2, 3)

    ax0 = fig.add_subplot(gs[0:2, 0])  # Layout plot
    ax1 = fig.add_subplot(gs[0, 1])
    ax2 = fig.add_subplot(gs[1, 1])
    ax3 = fig.add_subplot(gs[0:2, 2])

    ppfunctions.plot_fidelity_vs_utilization_zac(ax=ax0)

    legend_handles_scatter, legend_labels_scatter = ppfunctions.plot_compilation_time_vs_fidelity_scatter_plot(
        ax=ax3, title='(c) Framework runtime vs Fidelity'
    )

    fig.legend(handles=legend_handles_scatter, labels=legend_labels_scatter, loc='lower center',
               bbox_to_anchor=(0.852, -0.01), ncol=2, fontsize=12, frameon=True)

    fig.legend(loc='lower center', bbox_to_anchor=(0.52, 0.01), ncol=3, fontsize=12, frameon=True,
               labels=['Single', 'Grouped', 'Grouped Independent'])

    fig.text(0.335, 0.23, "PachinQo", fontweight='bold', rotation=90, fontsize=18)
    fig.text(0.335, 0.74, "ZAC", fontweight='bold', rotation=90, fontsize=18)

    fig.tight_layout(rect=(0.005, 0.07, 1, 1), h_pad=0.005)

    fig.savefig('results/preeval/preeval.pdf', format='pdf')
'''


def plot_introduction_figures():
    # Was scripts/introduction_plots.py.
    fig, [ax0] = utils.gen_subplots(1, 1, figsize=(6.5, 3.5))

    ppfunctions.plot_fidelity_vs_circuit_size_zac_pachinqo_atomique(ax0, title='(a) Fidelity vs Circuit size')
    ppfunctions.plot_initialization_time_vs_qpu_size(ax0, title='(b) Initialization Time vs QPU size')
    ppfunctions.plot_execution_time_vs_circuit_size_zac_pachinqo_atomique(ax0, title='(c) Execution time vs Circuit size')

    fig.tight_layout()

    fig.legend(loc='lower center', bbox_to_anchor=(0.52, 0.935), ncol=4, fontsize=12, frameon=True,
               labels=['ZAC', 'PachinQo', 'Atomique', 'Average'])

    fig.savefig('results/preeval/introduction_plots.png', format='png', dpi=300, bbox_inches='tight')


@dataclass
class Experiment:
    name: str
    description: str
    data_fn: callable = None
    plot_fn: callable = None


EXPERIMENTS = [
    Experiment(
        "introduction",
        "Paper introduction/motivation figure (fidelity/init-time/exec-time vs. ZAC/PachinQo/Atomique)",
        plot_fn=plot_introduction_figures,
    ),
    # Other experiments (preeval_zac, preeval_pachinqo, preeval_zac_layouts)
    # commented out along with their functions above -- not needed for the
    # current plot set.
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