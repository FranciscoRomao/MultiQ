from zac.ds.architecture import Architecture
from zac.zac import ZAC
from zac.simulator.simulator import Simulator
from qiskit import QuantumCircuit
import json
from qiskit.qasm2 import dumps
import os
import pdb
import logging
import pandas as pd
import random
import logging
import argparse
from multiq.multiq import MultiQ
from multiq.compiler.planner import Planner
from multiq.compiler.scheduler import CircuitSelector
from multiq.compiler.tile import Tile

logger = logging.getLogger("multiq.evaluation.multiq_runner")

def save_circuit(circuit, filename):
    qasm_str = dumps(circuit)

    with open(filename, "w") as f:
        f.write(qasm_str)

def run_multiq_planner_eval(config_file:str = "../../config/multiq/planner_config.yaml"):

    perf_weights = [1.0, 0.8, 0.6, 0.4, 0.2]

    benchmark_set = open("data/multi_eval_bench_list.txt").read().splitlines()

    benchmark_set = [os.path.join(os.path.dirname(__file__), "../../data/benchmarks", bench) for bench in benchmark_set]

    data = pd.DataFrame(columns=['benchmark',
                                 'perf_weight',
                                 'storage_zone_cols',
                                 'nqubits',
                                 'total_fidelity',
                                 'total_1q_gate_fidelity',
                                 'total_2q_gate_fidelity',
                                 'total_coherence_fidelity',
                                 'total_2q_on_idle',
                                 'total_transfer_fidelity',
                                 'total_duration'])

    for weight in perf_weights:
        for bench in benchmark_set:
            logger.info(f"Running MultiQ with weight {weight} on benchmark {bench}")
            mq = MultiQ(config_file)
            mq.config.perf_weight = weight
            output_files = mq.set_inputs([bench])

            stats = pd.read_json(output_files[0][0], typ='series')

            circ = QuantumCircuit().from_qasm_file(bench)

            data.loc[len(data)] = [bench.split('/')[-1],
                                   weight,
                                   mq.bins[0][0].config.storage_zone_cols,
                                   circ.num_qubits,
                                   stats['cir_fidelity'],
                                   stats['cir_fidelity_1q_gate'],
                                   stats['cir_fidelity_2q_gate'],
                                   stats['cir_fidelity_coherence'],
                                   stats['cir_fidelity_2q_gate_for_idle'],
                                   stats['cir_fidelity_atom_transfer'],
                                   stats['cir_duration']]

    results_file = os.path.join(os.path.dirname(__file__), '../../results/multiq/planner_results.csv')
    os.makedirs(os.path.dirname(results_file), exist_ok=True)
    data.to_csv(results_file, mode='a', header=True, index=False)

def run_multiq_bundler_eval(set_sizes:list[int] = [5, 6], perf_weights:list[float] = [0.4, 1.0], config_file:str = "../../config/multiq/bundler_config.yaml", results_file:str = "../../results/multiq/bundler_results.csv"):

    random.seed(42)
    benchmark_set = open("data/bundler_eval_bench_list.txt").read().splitlines()
    benchmark_set = [os.path.join(os.path.dirname(__file__), "../../data/benchmarks", bench) for bench in benchmark_set]

    benchmark_sets = [random.sample(benchmark_set, size) for size in set_sizes]    
    bench = '-'.join([os.path.basename(b).split('.')[0] for b in benchmark_set])

    data = pd.DataFrame(columns=['benchmarks',
                                 'tile_widths',
                                 'algorithm',
                                 'perf_weight',
                                 'nbins',
                                 'temporal_utilization'])
    
    mq = MultiQ(config_file=config_file)

    mq.config.perf_weight = 0.7
    mq.config.grid_rows = 1
    mq.config.selection_algorithm = "fifo"

    # ----- Running MultiQ with fifo selection algorithm

    logger.info(f"Running MultiQ with FIFO selection algorithm on benchmark set: {bench}")
    mq = MultiQ(config_file=config_file)
    fifo_output_files_fid = []
    fifo_output_files_fid = mq.set_inputs(benchmark_set)
    fifo_output_files_code = [file.split('_fidelity')[0] + '.json' for file in fifo_output_files_fid[0]]
    
    avg_set_fidelity = 1
    avg_coherence_fidelity = 1
    avg_transfer_fidelity = 1
    avg_circuit_duration = 1
    temporal_utilization = 1
    temporal_utilization = 0
    circuit_counter = 0

    total_bins_time = 0
    sum_tile_durations = 0

    tile_widths:list[list] = []
    for bin in fifo_output_files_fid:
        tile_widths.append([])
        tile_durations = [pd.read_json(tile, typ='series')['cir_duration'] for tile in bin]
        longest_circuit = max(tile_durations)
        total_bins_time += len(bin) * longest_circuit
        sum_tile_durations += sum(tile_durations)

        #Maybe even multiply by the sizes of the tiles so to scale the temporal utilization by the "number of qubits" in the tile
        temporal_utilization = sum_tile_durations / total_bins_time

        temporal_utilization *= temporal_utilization

        for tile in bin:
        #    circuit_counter += 1
            code_file = tile.split('_fidelity')[0] + '.json'
            code_stats = pd.read_json(code_file, typ='series')
        #   stats = pd.read_json(tile, typ='series')
            tile_widths[-1].append(int(code_stats['tile_width']))
        #   avg_set_fidelity *= stats['cir_fidelity']
        #   avg_coherence_fidelity *= stats['cir_fidelity_coherence']
        #   avg_transfer_fidelity *= stats['cir_fidelity_atom_transfer']
        #   avg_circuit_duration *= stats['cir_duration']

        #avg_set_fidelity = avg_set_fidelity ** (1 / circuit_counter)
        #avg_coherence_fidelity = avg_coherence_fidelity ** (1 / circuit_counter)
        #avg_transfer_fidelity = avg_transfer_fidelity ** (1 / circuit_counter)
        #avg_circuit_duration = avg_circuit_duration ** (1 / circuit_counter)
        #avg_bin_temporal_utilization = avg_bin_temporal_utilization ** (1 / len(output_files_fid))
        
        data.loc[len(data)] = [bench,
                               tile_widths,
                               'fifo',
                               0,
                               avg_circuit_duration,
                               sum_tile_durations/total_bins_time]
    
        os.makedirs(os.path.dirname(results_file), exist_ok=True)
        if not os.path.isfile(results_file):
            data.to_csv(results_file, index=False)
        else:
            data.to_csv(results_file, mode='a', header=False, index=False)

'''
    perf_weights = [0.2, 0.4, 0.6, 0.8, 1.0]

    for idx, weight in enumerate(perf_weights):
        for benchmark_set in benchmark_sets:
            mq = MultiQ(config_file=config_file)

            mq.config.perf_weight = 0.7
            mq.config.perf_weight_selector = weight
            mq.config.grid_rows = 2

            bench = '-'.join([os.path.basename(b).split('.')[0] for b in benchmark_set])
            print(f"Processing benchmark set: {bench} with weight {weight}")
            
            output_files_fid = mq.set_inputs(benchmark_set)
            output_files_code = [file.split('_fidelity')[0] + '.json' for file in output_files_fid[0]]

            avg_set_fidelity = 1
            avg_coherence_fidelity = 1
            avg_transfer_fidelity = 1
            avg_circuit_duration = 1
            temporal_utilization = 1
            temporal_utilization = 0

            circuit_counter = 0

            # Maybe compute here the sorting times for each bin and added to the cummulative duration
            total_bins_time = 0
            sum_tile_durations = 0

            tile_widths:list[list] = []
            for bin in output_files_fid:
                tile_widths.append([])
                tile_durations = [pd.read_json(tile, typ='series')['cir_duration'] for tile in bin]
                longest_circuit = max(tile_durations)
                total_bins_time += len(bin) * longest_circuit
                sum_tile_durations += sum(tile_durations)

                #Maybe even multiply by the sizes of the tiles so to scale the temporal utilization by the "number of qubits" in the tile
                temporal_utilization = sum_tile_durations / total_bins_time

                temporal_utilization *= temporal_utilization

                for tile in bin:
                #    circuit_counter += 1
                    code_file = tile.split('_fidelity')[0] + '.json'
                    code_stats = pd.read_json(code_file, typ='series')
                #    stats = pd.read_json(tile, typ='series')
                    tile_widths[-1].append(int(code_stats['tile_width']))
                #    avg_set_fidelity *= stats['cir_fidelity']
                #    avg_coherence_fidelity *= stats['cir_fidelity_coherence']
                #    avg_transfer_fidelity *= stats['cir_fidelity_atom_transfer']
                #    avg_circuit_duration *= stats['cir_duration']

            #avg_set_fidelity = avg_set_fidelity ** (1 / circuit_counter)
            #avg_coherence_fidelity = avg_coherence_fidelity ** (1 / circuit_counter)
            #avg_transfer_fidelity = avg_transfer_fidelity ** (1 / circuit_counter)
            #avg_circuit_duration = avg_circuit_duration ** (1 / circuit_counter)
            #avg_bin_temporal_utilization = avg_bin_temporal_utilization ** (1 / len(output_files_fid))
            
            data.loc[len(data)] = [bench,
                                   tile_widths,
                                   weight,
                                   avg_circuit_duration,
                                   sum_tile_durations/total_bins_time]
    
            if not os.path.isfile(results_file):
                data.to_csv(results_file, index=False)
            else:
                data.to_csv(results_file, mode='a', header=False, index=False)

            # Clean data because it was already saved
            data.drop(data.index[-1], inplace=True)
'''

def run_multiq(benchmarks:list[str], config_file:str = "../../config/multiq/config.yaml", output_file:str = "../../results/multiq/results.csv"):

    data = pd.DataFrame(columns=['benchmark',
                                 'bin_idx',
                                 'tile_width',
                                 'cir_fidelity',
                                 'nbins',
                                 'cir_coherence',
                                 'cir_transfer_fidelity',
                                 'cir_duration',
                                 'n_aods',
                                 'n_rows',
                                 'selector_algo',
                                 'selector_weight',
                                 'set_size',
                                 'compilation_time',
                                 'planning_time',
                                 'bundling_time',
                                 'scheduling_time',
                                 'placement_time',
                                 'routing_time'])

    mq = MultiQ(config_file=config_file)

    bench = '-'.join([os.path.basename(b).split('.')[0] for b in benchmarks])

    benchmarks = [os.path.join(os.path.dirname(__file__), "../../data/benchmarks", bench) for bench in benchmarks]
    
    output_files = mq.set_inputs(benchmarks)

    avg_set_fidelity = 1
    avg_coherence_fidelity = 1
    avg_transfer_fidelity = 1
    avg_circuit_duration = 1
    cummulative_duration = 0

    # Maybe compute here the sorting times for each bin and added to the cummulative duration
    bench_name = ''

    for bin_idx, bin in enumerate(output_files):
        #tile_durations = [pd.read_json(tile, typ='series')['cir_duration'] for tile in bin]
        #cummulative_duration += max(tile_durations)
        for tile_idx, tile in enumerate(bin):
            bench_name = tile.split('/')[-1].split('_fidelity')[0]
            stats = pd.read_json(tile, typ='series')
            stats_code = pd.read_json(tile.split('_fidelity')[0] + '.json', typ='series')
            #avg_set_fidelity *= stats['cir_fidelity']
            #avg_coherence_fidelity *= stats['cir_fidelity_coherence']
            #avg_transfer_fidelity *= stats['cir_fidelity_atom_transfer']
            #avg_circuit_duration *= avg_circuit_duration

        #avg_set_fidelity = avg_set_fidelity ** (1 / len(output_files))
        #avg_coherence_fidelity = avg_coherence_fidelity ** (1 / len(output_files))
        #avg_transfer_fidelity = avg_transfer_fidelity ** (1 / len(output_files))
        #avg_circuit_duration = avg_circuit_duration ** (1 / len(output_files))
        
            data.loc[len(data)] = [bench_name,
                                   bin_idx,
                                   stats_code['tile_width'],
                                   stats['cir_fidelity'],
                                   len(output_files),
                                   stats['cir_fidelity_coherence'],
                                   stats['cir_fidelity_atom_transfer'],
                                   stats['cir_duration'],
                                   mq.config.num_aods,
                                   mq.config.grid_rows,
                                   mq.config.selection_algorithm,
                                   mq.config.perf_weight_selector,
                                   len(benchmarks),
                                   mq.timing["total"],
                                   mq.timing["planning"],
                                   mq.timing["bundling"],
                                   mq.timing["scheduling"],
                                   mq.timing["placement"],
                                   mq.timing["routing"]]
    
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    if not os.path.isfile(output_file):
        data.to_csv(output_file, index=False)
    else:
        data.to_csv(output_file, mode='a', header=False, index=False)

def run_controler_set_multiq(benchmarks:list[str], config_file:str = "../../config/multiq/config.yaml", output_file:str = "../../results/multiq/results.csv"):

    logger = logging.getLogger("multiq")
    random.seed(42)

    logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)

    benchmarks = [os.path.join(os.path.dirname(__file__), "../../data/benchmarks", bench) for bench in benchmarks]

    data = pd.DataFrame(columns=['benchmarks',
                                 'tile_widths',
                                 'total_fidelity',
                                 'nbins',
                                 'total_coherence_fidelity',
                                 'total_transfer_fidelity',
                                 'avg_bin_duration',
                                 'cummulative_duration',
                                 'nrows'])

    mq = MultiQ(config_file=config_file)

    bench = '-'.join([os.path.basename(b).split('.')[0] for b in benchmarks])
    
    output_files_fid = mq.set_inputs(benchmarks)
    output_files_code = [file.split('_fidelity')[0] + '.json' for file in output_files_fid[0]]

    avg_set_fidelity = 1
    avg_coherence_fidelity = 1
    avg_transfer_fidelity = 1
    avg_circuit_duration = 1
    cummulative_duration = 0

    circuit_counter = 0

    # Maybe compute here the sorting times for each bin and added to the cummulative duration
    tile_widths:list[list] = []
    for bin in output_files_fid:
        tile_widths.append([])
        tile_durations = [pd.read_json(tile, typ='series')['cir_duration'] for tile in bin]
        cummulative_duration += max(tile_durations)/1000
        for tile in bin:
            circuit_counter += 1
            code_file = tile.split('_fidelity')[0] + '.json'
            code_stats = pd.read_json(code_file, typ='series')
            stats = pd.read_json(tile, typ='series')
            tile_widths[-1].append(int(code_stats['tile_width']))
            avg_set_fidelity *= stats['cir_fidelity']
            avg_coherence_fidelity *= stats['cir_fidelity_coherence']
            avg_transfer_fidelity *= stats['cir_fidelity_atom_transfer']
            avg_circuit_duration *= stats['cir_duration']

        avg_set_fidelity = avg_set_fidelity ** (1 / circuit_counter)
        avg_coherence_fidelity = avg_coherence_fidelity ** (1 / circuit_counter)
        avg_transfer_fidelity = avg_transfer_fidelity ** (1 / circuit_counter)
        avg_circuit_duration = avg_circuit_duration ** (1 / circuit_counter)
            
        data.loc[len(data)] = [bench,
                               tile_widths,
                               float(avg_set_fidelity),
                               len(output_files_fid),
                               float(avg_coherence_fidelity),
                               float(avg_transfer_fidelity),
                               avg_circuit_duration,
                               cummulative_duration,
                               mq.config.grid_rows]
    
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        if not os.path.isfile(output_file):
            data.to_csv(output_file, index=False)
        else:
            data.to_csv(output_file, mode='a', header=False, index=False)

        # Clean data because it was already saved
        data.drop(data.index[-1], inplace=True)

def _compute_spatial_utilization(tiles:list[Tile], qpu_width) -> float:

    width_sum = sum(tile.architecture.arch_range[1][0] for tile in tiles)

    total_qpu_width = qpu_width * tiles[0].config.storage_zone_rows
    
    return width_sum/total_qpu_width
        
def _compute_temporal_utilization(tiles:list[Tile]) -> float:

    longest_circuit = [pd.read_json(tile, typ='series')['cir_duration'] for tile in bin]
    total_bins_time = len(tiles) * longest_circuit

    sum_tile_durations = sum(tile_durations)

    #Maybe even multiply by the sizes of the tiles so to scale the temporal utilization by the "number of qubits" in the tile
    temporal_utilization = sum_tile_durations / total_bins_time

    temporal_utilization *= temporal_utilization

    total_duration = sum(tile.architecture for tile in tiles)
    max_duration = max(tile.architecture.duration for tile in tiles)

    if total_duration == 0:
        return 0.0

    return total_duration / (len(tiles) * max_duration)

def run_bundler_comparision():
    """
    Main function to run the ZAC compiler on a set of benchmarks.
    """
    input_files = open("data/bundler_eval_bench_list.txt").read().splitlines()
    
    perf_weights = [0.2, 0.4, 0.6, 0.8, 1.0]
    
    # Setting up MultiQ up to bundler
    mq = MultiQ(config_file="../../config/multiq/bundler_config.yaml")

    # Set algo to FIFO
    mq.config.selection_algorithm = "fifo"

    planner = Planner(mq.config)
    planner.set_input_circuits(input_files, optimization_level=3)
    tiles = planner.set_best_architectures()

    selector = CircuitSelector(mq.config)
    fifo_selected_tiles = selector.select(tiles)

    # Set algo to SA
    mq.config.selection_algorithm = "sa"

    sa_selected_tiles = []

    for weight in perf_weights:
        mq.config.perf_weight_selector = weight

        # Run the bundler
        sa_selected_tiles.append(selector.select(tiles))

