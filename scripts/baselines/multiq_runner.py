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

#logger = logging.getLogger("evaluation.zac_runner")

def save_circuit(circuit, filename):
    qasm_str = dumps(circuit)

    with open(filename, "w") as f:
        f.write(qasm_str)

def run_multiq_planner_eval():

    perf_weights = [0.2, 0.4, 0.6, 0.8, 1.0]

    benchmark_set = open("data/benchmark_list.txt").read().splitlines()

    for weight in perf_weights:
        for bench in benchmark_set:

            mq = MultiQ()
            mq.config.perf_weight = weight
            mq.set_inputs([bench])

            #results = 

'''
def run_multiq_bundler_eval():

    logger = logging.getLogger("multiq")

    logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)

    perf_weights = [0.2, 0.4, 0.6, 0.8, 1.0]

    bundler_configs = [


    benchmark_set = open("data/benchmark_list.txt").read().splitlines()

    for weight in perf_weights:
        for bench in benchmark_set:

            mq = MultiQ()
            mq.config.perf_weight = weight
            mq.set_inputs(args.input)
'''
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