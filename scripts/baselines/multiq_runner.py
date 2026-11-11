from qiskit import QuantumCircuit
from qiskit.qasm2 import dumps
import os
import logging
import pandas as pd
from multiq.multiq import MultiQ
from status import step

logger = logging.getLogger("multiq.evaluation.multiq_runner")

def save_circuit(circuit, filename):
    qasm_str = dumps(circuit)
    os.makedirs(os.path.dirname(filename) or ".", exist_ok=True)

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

    n_runs = len(perf_weights) * len(benchmark_set)
    run_idx = 0
    for weight in perf_weights:
        for bench in benchmark_set:
            run_idx += 1
            step("MultiQ", run_idx, n_runs, f"perf_weight {weight}, {os.path.basename(bench)}")
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

    bench_name = ''

    for bin_idx, bin in enumerate(output_files):
        for tile_idx, tile in enumerate(bin):
            bench_name = tile.split('/')[-1].split('_fidelity')[0]
            stats = pd.read_json(tile, typ='series')
            stats_code = pd.read_json(tile.split('_fidelity')[0] + '.json', typ='series')
        
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


        


