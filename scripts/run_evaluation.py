from baselines.zac_runner import run_zac_single_benchmarks, run_zac_merged_benchmarks
#from baselines.pachinqo_runner import run_pachiqo_single_benchmarks
from baselines.multiq_runner import run_multiq_planner_eval, run_multiq_bundler_eval, run_multiq
from eval_functions import plot_planner_eval_fidelity_multiq, plot_planner_eval_utilization_multiq
import logging
import os
import random
from plotting import utils, bar_plot
import numpy as np

# Set up logging only for multiq messages
logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(levelname)s - %(message)s')
logging.getLogger("qiskit").setLevel(logging.WARNING)
logging.getLogger("fontTools").setLevel(logging.WARNING)
logging.getLogger("matplotlib").setLevel(logging.WARNING)
logging.getLogger("stevedore").setLevel(logging.WARNING)

'''

# ----- End-to-End Evaluation -----

# Running MultiQ and baselines in multiprogramming environment (End-to-End Evaluation)
random.seed(42)  # For reproducibility

multi_benchmark_set = open("data/multi_eval_bench_list.txt").read().splitlines()
multiq_config_file = os.path.join(os.path.dirname(__file__), "../../config/multiq/config.yaml")
multiq_results_file = os.path.join(os.path.dirname(__file__), '../../results/multiq/multiprogramming_results.csv')

zac_settings_file = os.path.join(os.path.dirname(__file__), "../../config/zac/general.json")
zac_results_file = os.path.join(os.path.dirname(__file__), '../../results/zac/multiprogramming_results.csv')

set_sizes = [2, 3, 4, 5, 6, 7, 8, 9, 10]

benchmark_sets = [random.sample(multi_benchmark_set, size) for size in set_sizes]

for idx, benchmark_set in enumerate(benchmark_sets):
    print(f"Running benchmark set {idx + 1} of size {len(benchmark_set)}")
    
    # Run MultiQ with the current benchmark set
    run_multiq(benchmarks=multi_benchmark_set, config_file=multiq_config_file, output_file=multiq_results_file)

# Running single benchmarks on baselines (End-to-End Evaluation)

multi_benchmark_set = np.array(multi_benchmark_set).flatten().tolist()  # Flatten the list of lists to a single list

for idx, bench in enumerate(multi_benchmark_set):
    run_zac_single_benchmarks(bench, zac_settings_file, zac_results_file)


#Plot end-to-end evaluation results

# ----- Compiler Evaluation ----

# Planner Evaluation

run_multiq_planner_eval()

# Bundler Evaluation

'''

run_multiq_bundler_eval()

# ----- Controller Evaluation ----

benchmark_set = open("data/benchmark_list.txt").read().splitlines()


pachinqo_settings_file = os.path.join(os.path.dirname(__file__), "../../config/pachinqo/general.json")

for benchmark in benchmark_set:
    run_zac_single_benchmarks(benchmark_set, zac_settings_file, zac_results_file)
    #run_pachiqo_single_benchmarks(benchmark_set, pachinqo_settings_file, output_file="results/pachinqo_results.csv")




#run_zac_merged_benchmarks()


exit(0)
fig, [ax0, ax1] = utils.gen_subplots(2,1, figsize=(16, 5))

plot_planner_eval_fidelity_multiq(ax=ax0, title="MultiQ Planner performance evaluation (Fidelity)")

plot_planner_eval_utilization_multiq(ax=ax1, title="MultiQ Planner performance evaluation (Fidelity)")

fig.tight_layout(rect=(0,0.01,1,1), h_pad=-0.0008)
#fig.tight_layout(w_pad=-1, rect=[0.011,0.05,0.95,1])

#fig.suptitle('Introduction Plots', fontsize=16)

fig.legend(loc='lower center', bbox_to_anchor=(0.52, 0), ncol=5, fontsize=12, frameon=True, labels=['0.2', '0.4', '0.6', '0.8', '1.0'])

fig.savefig('results/plots/planner_plots_1.pdf', format='pdf')
