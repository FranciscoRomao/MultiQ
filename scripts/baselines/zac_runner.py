from zac.ds.architecture import Architecture
from zac.zac import ZAC
from zac.simulator.simulator import Simulator
import json
import os
import pdb
import logging
import pandas as pd

logger = logging.getLogger("evaluation.zac_runner")

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

        filename = os.path.join(os.path.dirname(__file__), '../../data/benchmarks/', benchmark)
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

def main():
    """
    Main function to run the ZAC compiler on a set of benchmarks.
    """
    benchmark_set = open("data/benchmark_list.txt").read().splitlines()
    settings_file = os.path.join(os.path.dirname(__file__), "../../config/zac/general_2row.json")
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
                             'total_2q_on_idle'])
    
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
                               fid_res['cir_fidelity_2q_gate_for_idle']]
    
        results_file = os.path.join(os.path.dirname(__file__), '../../results/zac/', f'{benchmark.split(".")[0].split("/")[-1]}.csv')

        if not os.path.isfile(results_file):
            data.to_csv(results_file, index=False)
        else:
            data.to_csv(results_file, mode='a', header=False, index=False)    

if __name__ == "__main__":
    main()