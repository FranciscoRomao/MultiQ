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

logger = logging.getLogger("evaluation.zac_runner")

def save_circuit(circuit, filename):
    qasm_str = dumps(circuit)

    with open(filename, "w") as f:
        f.write(qasm_str)

def merge_circuits(circuits: list[QuantumCircuit]) -> QuantumCircuit:
    assert len(circuits) >= 1, "At least one circuit is required to merge."

    if len(circuits) == 1:
        return circuits[0]

    new_circuit: QuantumCircuit = circuits[0].copy()

    for i in range(1, len(circuits)):
        circuit2 = circuits[i]
        new_circuit_copy = new_circuit.copy()
        
        # Create a new quantum circuit with enough qubits and classical bits
        total_qubits = new_circuit.num_qubits + circuit2.num_qubits
        total_clbits = new_circuit.num_clbits + circuit2.num_clbits

        new_circuit = QuantumCircuit(total_qubits, total_clbits)

        # Map circuit1's qubits and clbits into the new circuit
        new_circuit.compose(
            new_circuit_copy,
            qubits=range(new_circuit_copy.num_qubits),
            clbits=range(new_circuit_copy.num_clbits),
            inplace=True
        )

        # Map circuit2's qubits and clbits into the new circuit
        new_circuit.compose(
            circuit2,
            qubits=range(new_circuit_copy.num_qubits, total_qubits),
            clbits=range(new_circuit_copy.num_clbits, total_clbits),
            inplace=True
        )
    
    return new_circuit

def run_zac(benchmark_set, settings_file):

    with open(settings_file, 'r') as f:
        exp_spec = json.load(f)

    dict_arch = dict()
    list_zac_setting = exp_spec["zac_setting"]
    to_run_simulation = exp_spec["simulation"]

    info = {'nqubits': []}

    zac_compiler = None

    for benchmark in benchmark_set:
        print("==============================================")
        print("Compile circuit {}".format(benchmark))

        filename = os.path.join(os.path.dirname(__file__), '../../data/benchmarks',benchmark)
        #filename = benchmark.split('/')[-1]
        #filename = filename.split('.')[0]

        for zac_setting in list_zac_setting:
            if zac_setting["arch_spec"] in dict_arch:
                (arch, spec) = dict_arch[zac_setting["arch_spec"]]
            else:
                with open(zac_setting["arch_spec"], 'r') as f:
                    spec = json.load(f)
                arch = Architecture(spec)
                arch.preprocessing() 
                dict_arch[zac_setting["arch_spec"]] = (arch, spec)
            zac_setting["name"] = filename
            zac_compiler = ZAC()
            zac_compiler.parse_setting(zac_setting)
            zac_compiler.set_architecture_spec_path(zac_setting["arch_spec"])
            zac_compiler.set_architecture(arch)
            zac_compiler.set_program(filename)
            # construct directory for result and time profiling
            directory = zac_compiler.dir+"code"
            if not os.path.exists(directory):
                os.makedirs(directory)
            directory = zac_compiler.dir+"time"
            if not os.path.exists(directory):
                os.makedirs(directory)
            code_dict = zac_compiler.solve(save_file=False)
            code_file = os.path.join(os.path.dirname(__file__), '../../results/zac/code', f'{benchmark.split('.')[0].split('/')[-1]}.json')
            with open(code_file, 'w') as f:
                json.dump(code_dict, f)

            tmp = os.path.join(os.path.dirname(__file__), '../../results/zac/time', f'{benchmark.split('.')[0].split('/')[-1]}.json')
            with open(tmp, 'w') as f:  
                json.dump(zac_compiler.runtime_analysis, f, indent = 2)
            
            if to_run_simulation:
                # set arch fidelity 
                # run simulation
                simulator = Simulator()
                simulator.set_arch_spec(spec)
                simulator.parse(code_file)
                fidelity_result = simulator.simulate()
                # continue
                # construct directory for fidelity result
                directory = zac_compiler.dir+"fidelity"
                if not os.path.exists(directory):
                    os.makedirs(directory)
                tmp = os.path.join(os.path.dirname(__file__), '../../results/zac/fidelity', f'{benchmark.split('.')[0].split('/')[-1]}.json')
                with open(tmp, 'w') as f:  
                    json.dump(fidelity_result, f, indent = 2)

            if exp_spec["animation"]:
                # construct directory for fidelity animation
                directory = zac_compiler.dir+"animation"
                if not os.path.exists(directory):
                    os.makedirs(directory)
                tmp =  os.path.join(os.path.dirname(__file__), '../../results/zac/animation', f'{benchmark.split('.')[0].split('/')[-1]}.mp4')
                zac_compiler.animate(code_dict, output=tmp)
    return info

def run_zac_single_benchmarks(benchmark_file, settings_file, output_file):
    """
    Main function to run the ZAC compiler on a set of benchmarks.
    """

    # Running single benchmarks
    #benchmark_set = open("data/benchmark_list.txt").read().splitlines()
    #settings_file = os.path.join(os.path.dirname(__file__), "../../config/zac/general.json")
    #settings_file = "../../config/zac/general.json"

    # Run the ZAC compiler
    info = run_zac([benchmark_file], settings_file)
    
    # Print the results
    logger.info("ZAC Compilation Info:", info)

    data = pd.DataFrame(columns=['benchmark',
                             'nqubits',
                             'total_fidelity',
                             'total_coherence_fidelity',
                             'total_transfer_fidelity',
                             'total_2q_on_idle',
                             'n_bench'])
    
    #for i, benchmark in enumerate(benchmark_set):

    benchmark = benchmark_file.split('/')[-1]

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
    
    os.remove(fid_file)
    os.remove(time_file)

    if not os.path.isfile(output_file):
        data.to_csv(output_file, index=False)
    else:
        data.to_csv(output_file, mode='a', header=False, index=False)

def run_zac_merged_benchmarks():

    logger = logging.getLogger("zac.evaluation")
    random.seed(42)

    logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)

    set_sizes = [2, 3, 4, 5, 6]

    benchmark_set = open("data/controler_eval_bench_list.txt").read().splitlines()

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

    merged_bench = [os.path.join('merged', f'{bench}.qasm') for bench in merged_bench_files]

    # Run the ZAC compiler
    info = run_zac(merged_bench, settings_file)
    
    # Print the results
    logger.info("ZAC Compilation Info:", info)

    data = pd.DataFrame(columns=['benchmark',
                             'nqubits',
                             'total_fidelity',
                             'total_coherence_fidelity',
                             'total_transfer_fidelity',
                             'total_2q_on_idle',
                             'n_bench',
                             'execution_time'])
    
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
                               len(bench.split('-')),
                               fid_res['cir_duration']]
    
        results_file = os.path.join(os.path.dirname(__file__), '../../results/zac/compiled_results.csv')

    if not os.path.isfile(results_file):
        data.to_csv(results_file, index=False)
    else:
        data.to_csv(results_file, mode='a', header=False, index=False)

'''
    logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)

    set_sizes = [5, 6, 7, 8, 9, 10]
    perf_weights = [0.2, 0.4, 0.6, 0.8, 1.0]

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