from zac.ds.architecture import Architecture
from zac.zac import ZAC
from zac.simulator.simulator import Simulator as _ZACSimulator
from qiskit import QuantumCircuit
import json
from qiskit.qasm2 import dumps
import os
import logging
import pandas as pd
import random
import math


class Simulator(_ZACSimulator):
    # Use exp(-idle/T) for coherence instead of ZAC's linear model, to match the other compilers.
    def simulate(self):
        results = super().simulate()
        coherence = 1.0
        for t in self.cir_qubit_busy_time:
            coherence *= math.exp(-(results["cir_duration"] - t) / self.time_coherence)
        results["cir_fidelity"] *= coherence / results["cir_fidelity_coherence"]
        results["cir_fidelity_coherence"] = coherence
        self.cir_fidelity = results["cir_fidelity"]
        self.cir_fidelity_coherence = coherence
        return results

logger = logging.getLogger("evaluation.zac_runner")

def save_circuit(circuit, filename):
    qasm_str = dumps(circuit)
    os.makedirs(os.path.dirname(filename) or ".", exist_ok=True)

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
        
        total_qubits = new_circuit.num_qubits + circuit2.num_qubits
        total_clbits = new_circuit.num_clbits + circuit2.num_clbits

        new_circuit = QuantumCircuit(total_qubits, total_clbits)

        new_circuit.compose(
            new_circuit_copy,
            qubits=range(new_circuit_copy.num_qubits),
            clbits=range(new_circuit_copy.num_clbits),
            inplace=True
        )

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


        filename = os.path.join('data/benchmarks',benchmark)

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
            directory = zac_compiler.dir+"code"
            if not os.path.exists(directory):
                os.makedirs(directory)
            directory = zac_compiler.dir+"time"
            if not os.path.exists(directory):
                os.makedirs(directory)
            code_dict = zac_compiler.solve(save_file=False)
            code_file = os.path.join('results/zac/code', f'{benchmark.split('/')[-1].split('.')[0].split('/')[-1]}.json')
            with open(code_file, 'w') as f:
                json.dump(code_dict, f)

            tmp = os.path.join('results/zac/time', f'{benchmark.split('/')[-1].split('.')[0].split('/')[-1]}.json')
            with open(tmp, 'w') as f:  
                json.dump(zac_compiler.runtime_analysis, f, indent = 2)
            
            if to_run_simulation:
                simulator = Simulator()
                simulator.set_arch_spec(spec)
                simulator.parse(code_file)
                fidelity_result = simulator.simulate()
                directory = zac_compiler.dir+"fidelity"
                if not os.path.exists(directory):
                    os.makedirs(directory)
                tmp = os.path.join('results/zac/fidelity', f'{benchmark.split('/')[-1].split('.')[0].split('/')[-1]}.json')
                with open(tmp, 'w') as f:  
                    json.dump(fidelity_result, f, indent = 2)

            if exp_spec["animation"]:
                directory = zac_compiler.dir+"animation"
                if not os.path.exists(directory):
                    os.makedirs(directory)
                tmp =  os.path.join('results/zac/animation', f'{benchmark.split('/')[-1].split('.')[0].split('/')[-1]}.mp4')
                zac_compiler.animate(code_dict, output=tmp)
    return info

def run_zac_single_benchmarks(benchmark_file, settings_file, output_file):

    info = run_zac([benchmark_file], settings_file)
    
    logger.info("ZAC compilation info: %s", info)

    data = pd.DataFrame(columns=['benchmark',
                             'nqubits',
                             'total_fidelity',
                             'total_coherence_fidelity',
                             'total_transfer_fidelity',
                             'total_2q_on_idle',
                             'cir_duration',
                             'compilation_time'])
    

    benchmark = benchmark_file.split('/')[-1]

    fid_file = os.path.join('results/zac/fidelity', f'{benchmark.split(".")[0].split("/")[-1]}.json')
    time_file = os.path.join('results/zac/time', f'{benchmark.split(".")[0].split("/")[-1]}.json')

    fid_res = pd.read_json(fid_file, typ='series')
    time_res = pd.read_json(time_file, typ='series')


    data.loc[len(data)] = [benchmark.split('.')[0],
                           benchmark.split('.')[0].split('-')[-1],
                           fid_res['cir_fidelity'],
                           fid_res['cir_fidelity_coherence'],
                           fid_res['cir_fidelity_atom_transfer'],
                           fid_res['cir_fidelity_2q_gate_for_idle'],
                           fid_res['cir_duration'],
                           time_res['total']]
    
    os.remove(fid_file)
    os.remove(time_file)

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    if not os.path.isfile(output_file):
        data.to_csv(output_file, index=False)
    else:
        data.to_csv(output_file, mode='a', header=False, index=False)

def run_zac_merge_benchmarks(benchmark_set, settings_file, output_file):

    logger = logging.getLogger("zac.evaluation")
    random.seed(42)

    logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)

    bench=''

    merged_bench_files = []

    benchmark_set = [os.path.join(os.path.dirname(__file__), '../../data/benchmarks', bench) for bench in benchmark_set]

    circuits = [QuantumCircuit.from_qasm_file(bench) for bench in benchmark_set]
    merged_circuit = merge_circuits(circuits)

    bench = '-'.join([os.path.basename(b).split('.')[0] for b in benchmark_set])
    merged_bench_files.append(bench)

    save_circuit(merged_circuit, os.path.join(os.path.dirname(__file__), '../../data/benchmarks/merged', f'{bench}.qasm'))
        
    
    settings_file = os.path.join(os.path.dirname(__file__), settings_file)

    merged_bench = [os.path.join('merged', f'{bench}.qasm') for bench in merged_bench_files]

    info = run_zac(merged_bench, settings_file)
    
    logger.info("ZAC compilation info: %s", info)

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
                               fid_res['cir_duration']/1000]
    
        results_file = os.path.join(os.path.dirname(__file__), output_file)

    os.makedirs(os.path.dirname(results_file), exist_ok=True)
    if not os.path.isfile(results_file):
        data.to_csv(results_file, index=False)
    else:
        data.to_csv(results_file, mode='a', header=False, index=False)
