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

logger = logging.getLogger("multiq.evaluation.multiq_runner")

def save_circuit(circuit, filename):
    qasm_str = dumps(circuit)

    with open(filename, "w") as f:
        f.write(qasm_str)

def run_multiq_planner_eval():

    perf_weights = [1.0, 0.8, 0.6, 0.4, 0.2]

    #perf_weights = [0.1, 0.2, 0.4, 0.5]

    benchmark_set = open("data/compiler_eval_bench_list.txt").read().splitlines()

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
            mq = MultiQ()
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
    data.to_csv(results_file, mode='a', header=False, index=False)

def run_multiq_bundler_eval():

    logger = logging.getLogger("multiq")
    random.seed(42)

    logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)

    set_sizes = [10]
    perf_weights = [1, 0.8, 0.6, 0.4, 0.2]

    benchmark_set = open("data/bundler_eval_bench_list.txt").read().splitlines()

    benchmark_set = [os.path.join(os.path.dirname(__file__), "../../data/benchmarks", bench) for bench in benchmark_set]

    benchmark_sets = [random.sample(benchmark_set, size) for size in set_sizes]

    data = pd.DataFrame(columns=['benchmarks',
                                 'perf_weight',
                                 'total_fidelity',
                                 'nbins',
                                 'total_coherence_fidelity',
                                 'total_transfer_fidelity',
                                 'avg_bin_duration',
                                 'cummulative_duration'])

    for idx, weight in enumerate(perf_weights):
        for benchmark_set in benchmark_sets:
            mq = MultiQ()

            mq.config.perf_weight = 0.7
            mq.config.perf_weight_selector = weight
            mq.config.grid_rows = 2

            bench = '-'.join([os.path.basename(b).split('.')[0] for b in benchmark_set])
            print(f"Processing benchmark set: {bench} with weight {weight}")
            
            output_files = mq.set_inputs(benchmark_set)
            stats = pd.read_json(output_files[0][0], typ='series')

            avg_set_fidelity = 1
            avg_coherence_fidelity = 1
            avg_transfer_fidelity = 1
            avg_circuit_duration = 1
            cummulative_duration = 0

            # Maybe compute here the sorting times for each bin and added to the cummulative duration

            for bin in output_files:
                tile_durations = [pd.read_json(tile, typ='series')['cir_duration'] for tile in bin]
                cummulative_duration += max(tile_durations)
                for tile in bin:
                    stats = pd.read_json(tile, typ='series')
                    avg_set_fidelity *= stats['cir_fidelity']
                    avg_coherence_fidelity *= stats['cir_fidelity_coherence']
                    avg_transfer_fidelity *= stats['cir_fidelity_atom_transfer']
                    avg_circuit_duration *= avg_circuit_duration

            avg_set_fidelity = avg_set_fidelity ** (1 / len(output_files))
            avg_coherence_fidelity = avg_coherence_fidelity ** (1 / len(output_files))
            avg_transfer_fidelity = avg_transfer_fidelity ** (1 / len(output_files))
            avg_circuit_duration = avg_circuit_duration ** (1 / len(output_files))
            
            data.loc[len(data)] = [bench,
                                   weight,
                                   float(avg_set_fidelity),
                                   len(output_files),
                                   float(avg_coherence_fidelity),
                                   float(avg_transfer_fidelity),
                                   avg_circuit_duration,
                                   cummulative_duration]
    
    results_file = os.path.join(os.path.dirname(__file__), '../../results/multiq/bundler_results.csv')
    data.to_csv(results_file, mode='a', header=False, index=False)

def run_multiq(benchmarks:list[str], config_file:str = "../../config/multiq/config.yaml", output_file:str = "../../results/multiq/results.csv"):

    data = pd.DataFrame(columns=['benchmarks',
                                 'perf_weight',
                                 'total_fidelity',
                                 'nbins',
                                 'total_coherence_fidelity',
                                 'total_transfer_fidelity',
                                 'avg_bin_duration',
                                 'cummulative_duration'])

    mq = MultiQ(config_file=config_file)

    bench = '-'.join([os.path.basename(b).split('.')[0] for b in benchmarks])
            
    output_files = mq.set_inputs(benchmarks)
    stats = pd.read_json(output_files[0][0], typ='series')

    avg_set_fidelity = 1
    avg_coherence_fidelity = 1
    avg_transfer_fidelity = 1
    avg_circuit_duration = 1
    cummulative_duration = 0

    # Maybe compute here the sorting times for each bin and added to the cummulative duration

    for bin in output_files:
        tile_durations = [pd.read_json(tile, typ='series')['cir_duration'] for tile in bin]
        cummulative_duration += max(tile_durations)
        for tile in bin:
            stats = pd.read_json(tile, typ='series')
            avg_set_fidelity *= stats['cir_fidelity']
            avg_coherence_fidelity *= stats['cir_fidelity_coherence']
            avg_transfer_fidelity *= stats['cir_fidelity_atom_transfer']
            avg_circuit_duration *= avg_circuit_duration

        avg_set_fidelity = avg_set_fidelity ** (1 / len(output_files))
        avg_coherence_fidelity = avg_coherence_fidelity ** (1 / len(output_files))
        avg_transfer_fidelity = avg_transfer_fidelity ** (1 / len(output_files))
        avg_circuit_duration = avg_circuit_duration ** (1 / len(output_files))
            
        data.loc[len(data)] = [bench,
                               float(avg_set_fidelity),
                               len(output_files),
                               float(avg_coherence_fidelity),
                               float(avg_transfer_fidelity),
                               avg_circuit_duration,
                               cummulative_duration]
    
    data.to_csv(output_file, mode='a', header=False, index=False)
'''
def run_multiq_single_benchmarks():
    """
    Main function to run the ZAC compiler on a set of benchmarks.
    """

    # Running single benchmarks
    benchmark_set = open("data/benchmark_list.txt").read().splitlines()
    settings_file = os.path.join(os.path.dirname(__file__), "../../config/zac/general.json")
    #settings_file = "../../config/zac/general.json"

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
    
    for i, benchmark in enumerate(benchmark_set):

        benchmark = benchmark.split('/')[-1]
        print(f"Processing benchmark: {benchmark}")

        fid_file = os.path.join(os.path.dirname(__file__), '../../results/zac/fidelity', f'{benchmark.split(".")[0].split("/")[-1]}.json')
        time_file = os.path.join(os.path.dirname(__file__), '../../results/zac/time', f'{benchmark.split(".")[0].split("/")[-1]}.json')

        fid_res = pd.read_json(fid_file, typ='series')
        time_res = pd.read_json(time_file, typ='series')

        data.loc[len(data)] = [benchmark.split('.')[0],
                               benchmark.split('.')[0].split('n')[-1],
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

'''
'''
    # Running merged benchmarks
    benchmark_set = open("data/benchmark_list.txt").read().splitlines()

    sets = [2,3,4,5,6,7,8]
    counts = 3

    for n in sets:
        for id in range(counts):
            benchmark_groups = random.choices(benchmark_set, k=n)  # Randomly select n benchmarks for merging

            merged_benchmark = merge_circuits(benchmark_groups)
            merged_benchmark_path = os.path.join(os.path.dirname(__file__), '../../data/benchmarks/merged/', f"merged_{n}bench_{id}.json")

            save_circuit(merged_benchmark, merged_benchmark_path)

            benchmark_set = [merged_benchmark_path]

            logger.info(f"Running ZAC on merged benchmarks: {benchmark_set}")

             # Run the ZAC compiler
            info = run_zac(benchmark_set, settings_file)

            for i, benchmark in enumerate(benchmark_set):

                benchmark = merged_benchmark_path.split('/')[-1]
                print(f"Processing benchmark: {benchmark}")

                fid_file = os.path.join(os.path.dirname(__file__), '../../results/zac/fidelity', f'{benchmark.split(".")[0].split("/")[-1]}.json')
                time_file = os.path.join(os.path.dirname(__file__), '../../results/zac/time', f'{benchmark.split(".")[0].split("/")[-1]}.json')

                fid_res = pd.read_json(fid_file, typ='series')
                time_res = pd.read_json(time_file, typ='series')

                data.loc[len(data)] = [benchmark.split('.')[0],
                                       benchmark.split('.')[0].split('n')[-1],
                                       fid_res['cir_fidelity'],
                                       fid_res['cir_fidelity_coherence'],
                                       fid_res['cir_fidelity_atom_transfer'],
                                       fid_res['cir_fidelity_2q_gate_for_idle',
                                        1]]

                results_file = os.path.join(os.path.dirname(__file__), '../../results/zac/', f'{benchmark.split(".")[0].split("/")[-1]}.csv')

                if not os.path.isfile(results_file):
                    data.to_csv(results_file, index=False)
                else:
                    data.to_csv(results_file, mode='a', header=False, index=False)  
'''

#if __name__ == "__main__":
#    main()