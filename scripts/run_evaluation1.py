from baselines.zac_runner import run_zac_single_benchmarks, run_zac_merged_benchmarks
#from baselines.pachinqo_runner import run_pachiqo_single_benchmarks
from baselines.multiq_runner import run_multiq_planner_eval, run_multiq_bundler_eval, run_multiq
from eval_functions import plot_planner_eval_fidelity_multiq, plot_planner_eval_utilization_multiq, plot_bundler_eval_utilization_multiq, plot_bundler_eval_decoherence_multiq
import os
import random
from plotting import utils, bar_plot
import numpy as np
import logging

# Set up logging only for multiq messages
logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(levelname)s - %(message)s')
logging.getLogger("qiskit").setLevel(logging.WARNING)
logging.getLogger("fontTools").setLevel(logging.WARNING)
logging.getLogger("matplotlib").setLevel(logging.WARNING)
logging.getLogger("stevedore").setLevel(logging.WARNING)
logging.getLogger("PIL").setLevel(logging.WARNING)

'''
# ----- 1. End-to-End Evaluation -----

# Running MultiQ and baselines in multiprogramming environment (End-to-End Evaluation)
random.seed(42)  # For reproducibility

multi_benchmark_set = open("data/multi_eval_bench_list.txt").read().splitlines()

#set_sizes = [2, 3, 4, 5, 6, 7, 8, 9, 10]
set_sizes = [2, 3, 4]

multi_benchmark_sets = [random.sample(multi_benchmark_set, size) for size in set_sizes]

multiq_config_file = os.path.join(os.path.dirname(__file__), "../config/config.yaml")
multiq_results_file = os.path.join(os.path.dirname(__file__), '../results/multiq/multiprogramming_results.csv')

zac_settings_file = os.path.join(os.path.dirname(__file__), "../config/zac/general.json")
zac_results_file = os.path.join(os.path.dirname(__file__), '../results/zac/multiprogramming_results.csv')

for idx, benchmark_set in enumerate(multi_benchmark_sets):
    print(f"Running benchmark set {idx + 1} of size {len(benchmark_set)}")
    
    # Run MultiQ with the current benchmark set
    run_multiq(benchmarks=benchmark_set, config_file=multiq_config_file, output_file=multiq_results_file)
# Running single benchmarks on baselines (End-to-End Evaluation)

for bench_set in multi_benchmark_sets:
    for bench in bench_set:
        print(f"Running single benchmark: {bench}")
        run_zac_single_benchmarks(bench, zac_settings_file, zac_results_file)
        #run_pachinqo_single_benchmarks(bench, pachinqo_settings_file, output_file="results/pachinqo_results.csv")

#Plot end-to-end evaluation results
# TODO

# ----- 2. Compiler Evaluation ----

'''
'''
# 2.1 Planner Evaluation

run_multiq_planner_eval()

# Plot planner evaluation results
fig, [ax0, ax1] = utils.gen_subplots(2,1, figsize=(13.2, 3.5))

plot_planner_eval_fidelity_multiq(ax=ax0, title="MultiQ Planner (Decoherence error)")

plot_planner_eval_utilization_multiq(ax=ax1, title="MultiQ Planner (Utilization)")

fig.tight_layout(rect=(0,0.08,1,1), h_pad=-0.1, w_pad=-0.01)

fig.legend(loc='lower center', bbox_to_anchor=(0.52, 0), ncol=5, fontsize=12, frameon=True, labels=['0.2', '0.4', '0.6', '0.8', '1.0'], title='Performance weight', title_fontsize=11)

fig.savefig('results/plots/planner_plots.pdf', format='pdf')
'''

# 2.2 Bundler Evaluation

multiq_config_file = os.path.join(os.path.dirname(__file__), "../config/multiq/bundler_config.yaml")
multiq_results_file = os.path.join(os.path.dirname(__file__), '../results/multiq/bundler_results.csv')

set_sizes = [2, 4, 6, 8, 10]  # Tile widths
perf_weights = [0.2, 0.4, 0.6, 0.8, 1.0]  # Performance weights

run_multiq_bundler_eval(set_sizes=set_sizes, perf_weights=perf_weights, config_file=multiq_config_file, results_file=multiq_results_file)

# Plot bundler evaluation results
fig, [ax0, ax1] = utils.gen_subplots(2,1, figsize=(13.2, 3.5))

plot_bundler_eval_decoherence_multiq(ax=ax0, title="a) Bundler (Decoherence Fidelity)")

plot_bundler_eval_utilization_multiq(ax=ax1, title="b) Bundler (Utilization)")

fig.tight_layout(rect=(0,0.08,1,1), h_pad=-0.1, w_pad=-0.01)

fig.legend(loc='lower center', bbox_to_anchor=(0.52, 0), ncol=2, fontsize=12, frameon=True, labels=['0.2', '0.4', '0.6', '0.8', '1.0'], title='Performance weight', title_fontsize=11)

fig.savefig('results/plots/bundler_plots.pdf', format='pdf')

'''
# ----- 3. Controller Evaluation ----
benchmark_set = open("data/benchmark_list.txt").read().splitlines()

pachinqo_settings_file = os.path.join(os.path.dirname(__file__), "../../config/pachinqo/general.json")

for benchmark in benchmark_set:
    run_zac_single_benchmarks(benchmark_set, zac_settings_file, zac_results_file)
    #run_pachiqo_single_benchmarks(benchmark_set, pachinqo_settings_file, output_file="results/pachinqo_results.csv")
'''