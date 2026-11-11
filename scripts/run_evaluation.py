import argparse
import logging
import os
import random
import sys
import time
import traceback
from dataclasses import dataclass

# Allow running both as a script and as a module.
_scripts_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _scripts_dir)
sys.path.insert(0, os.path.dirname(_scripts_dir))

import matplotlib.gridspec as gridspec
import matplotlib.legend as mlegend
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import pandas as pd
import yaml

from baselines.zac_runner import run_zac_single_benchmarks, run_zac_merge_benchmarks
from baselines.pachinqo_runner import run_pachiqo_single_benchmark
from baselines.powermove_runner import run_powermove_single_benchmarks, run_powermove_merge_benchmarks
from baselines.qmap_runner import run_qmap_single_benchmarks, run_qmap_merge_benchmarks
from baselines.zap_runner import run_zap_single_benchmarks, run_zap_merge_benchmarks
from baselines.multiq_runner import (
    run_multiq_planner_eval,
    run_multiq,
)
from tools.gen_benchmarks import gen_single_benchmarks, gen_benchmarks_from_list
from tools.gen_architectures import generate_scaled_arch
from plotting import utils, defaults
from eval_functions import generate_e2e_means_table
from introduction import run_introduction, plot_introduction
from status import status, step, warn, output_to_log
import eval_functions as eval

# Logging goes to the per-stage log file under results/logs.
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s", datefmt="%H:%M:%S")
for _name in ("qiskit", "fontTools", "matplotlib", "stevedore", "PIL"):
    logging.getLogger(_name).setLevel(logging.WARNING)

logger = logging.getLogger("multiq.evaluation")

# Sweeps write per-run config copies here so the base templates stay untouched.
GENERATED_CONFIG_DIR = os.path.join(os.path.dirname(__file__), "..", "config/multiq/_generated")
GENERATED_ARCH_DIR = os.path.join(os.path.dirname(__file__), "..", "config/zac/_generated")
PLOTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results/plots")
os.makedirs(GENERATED_CONFIG_DIR, exist_ok=True)
os.makedirs(GENERATED_ARCH_DIR, exist_ok=True)
os.makedirs(PLOTS_DIR, exist_ok=True)


def _write_generated_config(config, filename):
    path = os.path.join(GENERATED_CONFIG_DIR, filename)
    with open(path, "w") as file:
        yaml.dump(config, file)
    return path


# ----- 1. End-to-End Evaluation -----
def run_end_to_end_evaluation():
    multi_benchmark_set = open("data/multi_eval_bench_list.txt").read().splitlines()
    multi_benchmark_set_pachinqo = open("data/multi_eval_bench_list_pachinqo.txt").read().splitlines()

    set_sizes = [4, 6, 8, 10, 12, 14]

    # (nrows, set_size, perf_weight)
    set_size_perf_weights = [(1, 8, 0.35)]

    zac_settings_file = os.path.join(os.path.dirname(__file__), "../config/zac/general.json")
    general_arch_file = os.path.join(os.path.dirname(__file__), "../config/zac/general_arch.json")

    base_config_file = os.path.join(os.path.dirname(__file__), "..", "config/multiq/e2e_config.yaml")
    zac_results_file = os.path.join(os.path.dirname(__file__), f"../results/zac/e2e_results.csv")
    pachinqo_results_file = os.path.join(os.path.dirname(__file__), f"../results/pachinqo/e2e_results.csv")
    powermove_results_file = os.path.join(os.path.dirname(__file__), f"../results/powermove/e2e_results.csv")
    qmap_results_file = os.path.join(os.path.dirname(__file__), f"../results/qmap/e2e_results.csv")
    zap_results_file = os.path.join(os.path.dirname(__file__), f"../results/zap/e2e_results.csv")
    multiq_results_file = os.path.join(os.path.dirname(__file__), f"../results/multiq/e2e_results.csv")

    n_pachinqo = len(multi_benchmark_set_pachinqo)
    for i, bench in enumerate(multi_benchmark_set_pachinqo):
        step("PachinQo", i + 1, n_pachinqo, bench)
        run_pachiqo_single_benchmark(bench, zac_settings_file, pachinqo_results_file)

    n_single = len(multi_benchmark_set)
    for i, bench in enumerate(multi_benchmark_set):
        step("ZAC", i + 1, n_single, bench)
        run_zac_single_benchmarks(bench, zac_settings_file, zac_results_file)
        step("PowerMove", i + 1, n_single, bench)
        run_powermove_single_benchmarks(bench, general_arch_file, powermove_results_file)
        step("QMAP", i + 1, n_single, bench)
        run_qmap_single_benchmarks(bench, general_arch_file, qmap_results_file)
        step("ZAP", i + 1, n_single, bench)
        run_zap_single_benchmarks(bench, general_arch_file, zap_results_file)

    random.seed(42)  # For reproducibility
    multi_benchmark_sets = [random.sample(multi_benchmark_set, size) for size in set_sizes]

    n_multiq_configs = len(multi_benchmark_sets) * 2
    multiq_config_idx = 0
    for benchmark_set in multi_benchmark_sets:
        for rows in [1, 2]:
            with open(base_config_file, "r") as file:
                config = yaml.safe_load(file)
                config["grid_rows"] = rows
                config["grid_cols"] = len(benchmark_set)
                config["selection_algorithm"] = "fifo"
                if rows == 1 and len(benchmark_set) == 4:
                    config["perf_weight"] = 0.7  # 0.72 full 0.68 is best (0.645092)
                if rows == 2 and len(benchmark_set) == 4:
                    config["perf_weight"] = 0.92  # 1 full 0.94 is best (0.645092)
                if rows == 1 and len(benchmark_set) == 6:
                    config["perf_weight"] = 0.52  # 0.53 full 0.52 is best (0.667146)
                if rows == 2 and len(benchmark_set) == 6:
                    config["perf_weight"] = 1  # 1 full
                if rows == 1 and len(benchmark_set) == 8:
                    config["perf_weight"] = 0.35
                elif rows == 2 and len(benchmark_set) == 8:
                    config["perf_weight"] = 0.8  # 0.84 full 0.8 is best (0.667146)
                elif rows == 1 and len(benchmark_set) == 10:
                    config["perf_weight"] = 0.33
                elif rows == 2 and len(benchmark_set) == 10:
                    config["perf_weight"] = 0.6  # 0.64 full #0.6 is best
                elif rows == 1 and len(benchmark_set) == 12:
                    config["perf_weight"] = 0.18  # 0.24 full 0.18 is better
                elif rows == 2 and len(benchmark_set) == 12:
                    config["perf_weight"] = 0.48  # 0.51 full 0.48 is best (0.598073)
                elif rows == 1 and len(benchmark_set) == 14:
                    config["perf_weight"] = 0.17
                elif rows == 2 and len(benchmark_set) == 14:
                    config["perf_weight"] = 0.4  # 0.42 full #0.4 is best
            generated_config_file = _write_generated_config(
                config, f"e2e_config_set{len(benchmark_set)}_rows{rows}.yaml"
            )

            multiq_config_idx += 1
            step("MultiQ", multiq_config_idx, n_multiq_configs, f"set size {len(benchmark_set)}, {rows} row(s)")

            run_multiq(
                benchmarks=benchmark_set,
                config_file=generated_config_file,
                output_file=multiq_results_file,
            )



# ----- 2. MultiQ overhead evaluation -----
# The scheduling stage is the pluggable backend compiler, so it is shown separately from MultiQ's own overhead.

OVERHEAD_ALGORITHMS = ["dj", "ghz", "qft", "bv", "qpeinexact", "graphstate"]


def run_multiq_overhead_vs_circuit_size():
    circuit_sizes = [20, 50, 100]

    # No-op if the circuits already exist.
    gen_single_benchmarks(circuit_sizes, OVERHEAD_ALGORITHMS)

    base_config_file = os.path.join(os.path.dirname(__file__), "..", "config/multiq/e2e_config.yaml")
    arch_dir = os.path.join(os.path.dirname(__file__), "../config/zac/_generated")

    # Largest perf_weight per size that keeps all 6 tiles in one bin without zac placer crashes.
    PERF_WEIGHT_BY_CIRCUIT_SIZE = {20: 0.5, 50: 0.3, 100: 0.2}
    largest_demand = 6 * max(circuit_sizes)
    arch_path = os.path.join(arch_dir, "general_arch_circuit_scaling_fixed_qpu.json")
    fixed_arch, _, _ = generate_scaled_arch(largest_demand, out_arch_path=arch_path, target_utilization=0.1)
    fixed_qpu_width, fixed_qpu_height = fixed_arch["arch_range"][1]

    n_configs = len(circuit_sizes) * 2
    config_idx = 0
    for size in circuit_sizes:
        benchmark_set = [f"single/{algo}-{size}.qasm" for algo in OVERHEAD_ALGORITHMS]

        results_file = os.path.join(os.path.dirname(__file__), f"../results/multiq/overhead_by_circuit_size_{size}q.csv")

        for rows in [1, 2]:
            with open(base_config_file, "r") as file:
                config = yaml.safe_load(file)
            config["grid_rows"] = rows
            config["qpu_width"] = fixed_qpu_width
            config["qpu_height"] = fixed_qpu_height
            config["selection_algorithm"] = "sa"
            config["perf_weight"] = PERF_WEIGHT_BY_CIRCUIT_SIZE[size]
            tmp_config_path = os.path.join(os.path.dirname(__file__), f"../config/multiq/_generated/overhead_circuit_size_config_{size}q_rows{rows}.yaml")
            with open(tmp_config_path, "w") as file:
                yaml.dump(config, file)

            config_idx += 1
            step("MultiQ", config_idx, n_configs, f"circuit size {size}q, {rows} row(s)")

            run_multiq(
                benchmarks=benchmark_set,
                config_file=tmp_config_path,
                output_file=results_file,
            )



def run_multiq_overhead_vs_qpu_size():
    fixed_circuit_size = 30
    qpu_capacities = [180, 300, 500, 1000, 1200]

    gen_single_benchmarks([fixed_circuit_size], OVERHEAD_ALGORITHMS)
    benchmark_set = [f"single/{algo}-{fixed_circuit_size}.qasm" for algo in OVERHEAD_ALGORITHMS]

    base_config_file = os.path.join(os.path.dirname(__file__), "..", "config/multiq/e2e_config.yaml")
    arch_dir = os.path.join(os.path.dirname(__file__), "../config/zac/_generated")

    # Scaling the entanglement zone at 180q would push qpu_height below entanglement_height.
    group_archs = {
        capacity: generate_scaled_arch(capacity, out_arch_path=os.path.join(arch_dir, f"general_arch_qpu_scaling_{capacity}q.json"), target_utilization=1.0, scale_entanglement=False)
        for capacity in qpu_capacities
    }

    n_configs = len(qpu_capacities) * 2
    config_idx = 0
    for capacity in qpu_capacities:
        arch, actual_r, actual_c = group_archs[capacity]
        qpu_width, qpu_height = arch["arch_range"][1]
        results_file = os.path.join(os.path.dirname(__file__), f"../results/multiq/overhead_by_qpu_size_{capacity}q.csv")

        for rows in [1, 2]:
            with open(base_config_file, "r") as file:
                config = yaml.safe_load(file)
            config["grid_rows"] = rows
            config["qpu_width"] = qpu_width
            config["qpu_height"] = qpu_height
            config["selection_algorithm"] = "sa"
            # Keeps all 6 tiles in one bin at every capacity.
            config["perf_weight"] = 0.3
            tmp_config_path = os.path.join(os.path.dirname(__file__), f"../config/multiq/_generated/overhead_qpu_size_config_{capacity}q_rows{rows}.yaml")
            with open(tmp_config_path, "w") as file:
                yaml.dump(config, file)

            config_idx += 1
            step("MultiQ", config_idx, n_configs, f"QPU capacity {capacity}q ({actual_r}x{actual_c} storage), {rows} row(s)")

            run_multiq(
                benchmarks=benchmark_set,
                config_file=tmp_config_path,
                output_file=results_file,
            )



# ----- 3. Storage-zone rows sweep -----
# With grid_rows=1, qpu_height = entanglement_height + storage_rows * storage_atom_spacing.
ROWS_SWEEP_TARGETS = [5, 15, 25, 35]


def run_multiq_rows_sweep():
    multi_benchmark_set = open("data/multi_eval_bench_list.txt").read().splitlines()
    random.seed(42)
    # Same selection as the set size 4 e2e run.
    benchmark_set = random.sample(multi_benchmark_set, 4)

    base_config_file = os.path.join(os.path.dirname(__file__), "..", "config/multiq/e2e_config.yaml")
    entanglement_height = 40
    storage_atom_spacing = 3
    # At 5 rows, 0.7 splits the set into two bins.
    perf_weight_by_rows = {5: 0.6}
    default_perf_weight = 0.7

    # Optional pinned starting rows per target, since feasibility can differ between machines.
    actual_rows_by_target = {}

    max_retries = 10

    achieved_rows = []
    for target_idx, target_rows in enumerate(ROWS_SWEEP_TARGETS):
        actual_rows = actual_rows_by_target.get(target_rows, target_rows)
        retries = 0
        while True:
            qpu_height = entanglement_height + actual_rows * storage_atom_spacing
            with open(base_config_file, "r") as file:
                config = yaml.safe_load(file)
            config["grid_rows"] = 1
            config["qpu_height"] = qpu_height
            config["selection_algorithm"] = "sa"
            config["perf_weight"] = perf_weight_by_rows.get(actual_rows, default_perf_weight)
            tmp_config_path = os.path.join(os.path.dirname(__file__), f"../config/multiq/_generated/rows_sweep_config_{actual_rows}rows.yaml")
            with open(tmp_config_path, "w") as file:
                yaml.dump(config, file)

            results_file = os.path.join(os.path.dirname(__file__), f"../results/multiq/rows_sweep_{actual_rows}rows.csv")
            if os.path.isfile(results_file):
                os.remove(results_file)  # run_multiq appends to the file.

            step("MultiQ", target_idx + 1, len(ROWS_SWEEP_TARGETS), f"{actual_rows} storage rows (target {target_rows})")
            try:
                run_multiq(
                    benchmarks=benchmark_set,
                    config_file=tmp_config_path,
                    output_file=results_file,
                )
                nbins = pd.read_csv(results_file)["nbins"].iloc[0]
                if nbins != 1:
                    warn("MultiQ", f"{actual_rows} rows bundled into {nbins} bins (expected 1) with perf_weight={config['perf_weight']}, "
                                   f"add a lower override to perf_weight_by_rows for this point")
                achieved_rows.append(actual_rows)
                break
            except Exception:
                retries += 1
                print(traceback.format_exc())
                if retries >= max_retries:
                    raise RuntimeError(
                        f"rows sweep: target_rows={target_rows} still infeasible after {max_retries} bumps "
                        f"(last actual_rows={actual_rows}); pin a working actual_rows_by_target[{target_rows}] "
                        f"or see the traceback in results/logs/rows_sweep.log"
                    )
                warn("MultiQ", f"{actual_rows} rows infeasible (attempt {retries}/{max_retries}), retrying with {actual_rows + 5}")
                actual_rows += 5

    return achieved_rows


def plot_e2e_detailed(rows_sweep_values=ROWS_SWEEP_TARGETS):
    # Pass the row counts returned by run_multiq_rows_sweep if any target was bumped.

    detailed_set_sizes = [4]
    include_pachinqo = True
    include_powermove = True
    include_qmap = True
    include_zap = True

    zac_results_file = os.path.join(os.path.dirname(__file__), f"../results/zac/e2e_results.csv")

    zac_results_file = os.path.join(os.path.dirname(__file__), f"../results/zac/e2e_results.csv")
    pachinqo_results_file = os.path.join(os.path.dirname(__file__), f"../results/pachinqo/e2e_results.csv")
    powermove_results_file = os.path.join(os.path.dirname(__file__), f"../results/powermove/e2e_results.csv")
    qmap_results_file = os.path.join(os.path.dirname(__file__), f"../results/qmap/e2e_results.csv")
    zap_results_file = os.path.join(os.path.dirname(__file__), f"../results/zap/e2e_results.csv")
    multiq_results_file = os.path.join(os.path.dirname(__file__), f"../results/multiq/e2e_results.csv")
    rows_sweep_results_template = os.path.join(os.path.dirname(__file__), "../results/multiq/rows_sweep_{rows}rows.csv")

    fig = plt.figure(figsize=(13, 2.5), constrained_layout=True)
    gs = gridspec.GridSpec(1,3, figure=fig, width_ratios=[0.4, 0.4, 0.2])

    fidelity_ax = fig.add_subplot(gs[0])
    duration_ax = fig.add_subplot(gs[1])
    rows_ax = fig.add_subplot(gs[2])

    set_size = detailed_set_sizes[0]

    print("Plotting fidelity")
    print(f"Plotting results for benchmark set of size {set_size}")
    eval.plot_e2e_results_fidelity(
        ax=fidelity_ax,
        set_size=set_size,
        title=f"(a) Fidelity (Set {set_size})",
        multiq_results_file=multiq_results_file,
        zac_results_file=zac_results_file,
        pachinqo_results_file=pachinqo_results_file,
        powermove_results_file=powermove_results_file,
        qmap_results_file=qmap_results_file,
        zap_results_file=zap_results_file,
        include_pachinqo=include_pachinqo,
        include_powermove=include_powermove,
        include_qmap=include_qmap,
        include_zap=include_zap,
    )
    fidelity_ax.set_xlabel(None)

    print("Plotting circuit duration")
    print(f"Plotting results for benchmark set of size {set_size}")
    eval.plot_e2e_results_duration(
        ax=duration_ax,
        set_size=set_size,
        title=f"(b) Execution time (Set {set_size})",
        multiq_results_file=multiq_results_file,
        zac_results_file=zac_results_file,
        pachinqo_results_file=pachinqo_results_file,
        powermove_results_file=powermove_results_file,
        qmap_results_file=qmap_results_file,
        zap_results_file=zap_results_file,
        include_pachinqo=include_pachinqo,
        include_powermove=include_powermove,
        include_qmap=include_qmap,
        include_zap=include_zap,
    )
    duration_ax.set_xlabel(None)

    print("Plotting fidelity vs. storage zone rows")
    eval.plot_e2e_rows_sweep_fidelity(
        ax=rows_ax,
        title="(c) Fidelity vs. rows",
        row_values=rows_sweep_values,
        results_file_template=rows_sweep_results_template,
    )
    rows_ax.set_title(rows_ax.get_title(loc='left'), fontweight='bold', loc='left', fontsize=11)
    # Seaborn's legend proxies have no hatches, so build handles from the bars.
    _, rows_labels = rows_ax.get_legend_handles_labels()
    rows_handles = [
        mpatches.Patch(facecolor=bars.patches[0].get_facecolor(), hatch=bars.patches[0].get_hatch(),
                        edgecolor='black', label=label)
        for bars, label in zip(rows_ax.containers, rows_labels)
    ]
    # Leave room above the bars for the legend.
    rows_ax.set_ylim(0, 1.6)
    rows_ax.set_yticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
    rows_ax.legend(rows_handles, rows_labels, loc='upper center', bbox_to_anchor=(0.5, 1.02),
                    ncol=2, fontsize=8, frameon=True, title="Benchmark", title_fontsize=10)

    duration_ax.set_ylabel("Execution time (s)", fontsize=11)
    fidelity_ax.set_ylabel("Fidelity", fontsize=11)

    fig.tight_layout(w_pad=-0.8, rect=(-0.013, 0.06, 1.005, 1.045))

    duration_ax.set_ylim(0, 32)
    duration_yticks = [6, 8, 10, 20, 30, 40]
    duration_ax.set_yticks(duration_yticks)
    duration_ax.set_yticklabels([r'$10^1$' if v == 10 else '' for v in duration_yticks])

    # Label clipped bars with their real value.
    duration_ylim_top = duration_ax.get_ylim()[1]
    for container in duration_ax.containers:
        for bar in container:
            height = bar.get_height()
            if height > duration_ylim_top:
                duration_ax.text(bar.get_x(), duration_ylim_top * 0.92, f'{height:.0f}',
                                  ha='right', va='top', fontsize=11, fontweight='bold', rotation=90)

    legend_labels = ['MultiQ (1 Row)', 'MultiQ (2 Row)', 'ZAC']
    if include_powermove:
        legend_labels.append('PowerMove')
    if include_qmap:
        legend_labels.append('QMAP')
    if include_zap:
        legend_labels.append('ZAP')
    if include_pachinqo:
        legend_labels.append('PachinQo')
    # Hue order in plot_e2e_results_fidelity matches legend_labels.
    compiler_handles = [
        mpatches.Patch(facecolor=bars.patches[0].get_facecolor(), hatch=bars.patches[0].get_hatch(),
                        edgecolor='black', label=label)
        for bars, label in zip(fidelity_ax.containers, legend_labels)
    ]
    fig.legend(handles=compiler_handles, loc='lower center', bbox_to_anchor=(0.42, 0.035), ncol=len(legend_labels), fontsize=11, frameon=True, title_fontsize=11)

    fig.savefig("results/plots/e2e_plot_detailed.pdf", format="pdf")

def plot_e2e_detailed_full(detailed_set_sizes=(4, 8, 12), include_pachinqo=True, include_powermove=True, include_qmap=True, include_zap=True):
    zac_results_file = os.path.join(os.path.dirname(__file__), f"../results/zac/e2e_results.csv")
    pachinqo_results_file = os.path.join(os.path.dirname(__file__), f"../results/pachinqo/e2e_results.csv")
    powermove_results_file = os.path.join(os.path.dirname(__file__), f"../results/powermove/e2e_results.csv")
    qmap_results_file = os.path.join(os.path.dirname(__file__), f"../results/qmap/e2e_results.csv")
    zap_results_file = os.path.join(os.path.dirname(__file__), f"../results/zap/e2e_results.csv")
    multiq_results_file = os.path.join(os.path.dirname(__file__), f"../results/multiq/e2e_results.csv")

    fig = plt.figure(figsize=(15, 2.3 * len(detailed_set_sizes)), constrained_layout=True)

    gs = gridspec.GridSpec(len(detailed_set_sizes), 2, figure=fig, width_ratios=[1, 1])

    axes = []
    for idx in range(len(detailed_set_sizes)):
        axes.append(fig.add_subplot(gs[idx * 2]))
        axes.append(fig.add_subplot(gs[idx * 2 + 1]))

    letters = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l"]
    for idx, set_size in enumerate(detailed_set_sizes):
        eval.plot_e2e_results_fidelity(
            ax=axes[idx * 2],
            set_size=set_size,
            title=f"({letters[idx*2]}) Fidelity (Set size: {set_size})",
            multiq_results_file=multiq_results_file,
            zac_results_file=zac_results_file,
            pachinqo_results_file=pachinqo_results_file,
            powermove_results_file=powermove_results_file,
            qmap_results_file=qmap_results_file,
            zap_results_file=zap_results_file,
            include_pachinqo=include_pachinqo,
            include_powermove=include_powermove,
            include_qmap=include_qmap,
            include_zap=include_zap,
        )

        axes[idx * 2].set_xlabel(None)
        axes[idx * 2].tick_params(axis='x', labelsize=8, rotation=20)
        for label in axes[idx * 2].get_xticklabels():
            label.set_ha('right')

    for idx, set_size in enumerate(detailed_set_sizes):
        eval.plot_e2e_results_duration(
            ax=axes[idx * 2 + 1],
            set_size=set_size,
            title=f"({letters[idx*2+1]}) Execution time (Set size: {set_size})",
            multiq_results_file=multiq_results_file,
            zac_results_file=zac_results_file,
            pachinqo_results_file=pachinqo_results_file,
            powermove_results_file=powermove_results_file,
            qmap_results_file=qmap_results_file,
            zap_results_file=zap_results_file,
            include_pachinqo=include_pachinqo,
            include_powermove=include_powermove,
            include_qmap=include_qmap,
            include_zap=include_zap,
        )
        axes[idx * 2 + 1].set_xlabel(None)
        axes[idx * 2 + 1].tick_params(axis='x', labelsize=8, rotation=20)
        for label in axes[idx * 2 + 1].get_xticklabels():
            label.set_ha('right')

    fig.tight_layout(w_pad=0.2, h_pad=0, rect=(-0.01, 0.005, 1.005, 1.005))

    legend_labels = ["MultiQ (1 Row)", "MultiQ (2 Row)", "ZAC"]
    if include_powermove:
        legend_labels.append("PowerMove")
    if include_qmap:
        legend_labels.append("QMAP")
    if include_zap:
        legend_labels.append("ZAP")
    if include_pachinqo:
        legend_labels.append("PachinQo")
    # Hue order in plot_e2e_results_fidelity matches legend_labels.
    compiler_handles = [
        mpatches.Patch(facecolor=bars.patches[0].get_facecolor(), hatch=bars.patches[0].get_hatch(),
                        edgecolor='black', label=label)
        for bars, label in zip(axes[0].containers, legend_labels)
    ]
    fig.legend(
        handles=compiler_handles,
        loc="lower center",
        bbox_to_anchor=(0.52, -0.005),
        ncol=len(legend_labels),
        fontsize=11,
        frameon=True,
        title_fontsize=11,
    )

    fig.savefig("results/plots/e2e_plot_detailed_full.pdf", format="pdf")


def plot_e2e_total_runtime(include_powermove=True, include_qmap=True, include_zap=True, include_pachinqo=True):
    fig, [ax0, ax1] = utils.gen_subplots(1, 2, figsize=(13, 2.85), height_ratios=[0.8, 1])

    set_sizes = [6, 8, 10, 12, 14]

    first_interval = (0, 200)
    second_interval = (500, 2000)

    scale = (first_interval[1] - first_interval[0]) / (second_interval[1] - second_interval[0])

    break_interval = 30

    eval.plot_e2e_results_total_runtime(
        ax=ax0,
        title="Total runtime",
        set_size=set_sizes,
        higher_lower_is_better="lower",
        xticks_visible=False,
        include_powermove=include_powermove,
        include_qmap=include_qmap,
        include_zap=include_zap,
        include_pachinqo=include_pachinqo,
    )
    df = eval.plot_e2e_results_total_runtime(
        ax=ax1,
        title="",
        set_size=set_sizes,
        higher_lower_is_better=None,
        xticks_visible=True,
        include_powermove=include_powermove,
        include_qmap=include_qmap,
        include_zap=include_zap,
        include_pachinqo=include_pachinqo,
    )

    plt.annotate(
        "",
        xy=(
            ax1.containers[2][0].get_x() + ax1.containers[2][0]._width / 2,
            df[df["compiler"] == "MultiQ(2 Row)"][df["set_size"] == "Set 6"]["phase_duration"].sum() + 1,
        ),
        xytext=(
            ax1.containers[2][0].get_x() + ax1.containers[2][0]._width / 2,
            min(df[df["compiler"] == "ZAC"][df["set_size"] == "Set 6"]["phase_duration"].sum(), first_interval[1])
            + 0.8
            * scale
            * (df[df["compiler"] == "ZAC"][df["set_size"] == "Set 6"]["phase_duration"].sum() - second_interval[0])
            + break_interval,
        ),
        fontsize=11,
        color="red",
        ha="center",
        arrowprops=dict(arrowstyle="fancy", color="green"),
    )
    ax1.text(
        ax1.containers[0][0].get_x(),
        (min(df[df["compiler"] == "ZAC"][df["set_size"] == "Set 6"]["phase_duration"].sum(), first_interval[1])
            + 0.8
            * scale
            * (df[df["compiler"] == "ZAC"][df["set_size"] == "Set 6"]["phase_duration"].sum() - second_interval[0])
            + break_interval)/2 + df[df['compiler']=='MultiQ(2 Row)'][df['set_size']=='Set 6']['phase_duration'].sum() / 2,
        f'-{(df[df['compiler']=='ZAC'][df['set_size']=='Set 6']['phase_duration'].sum()/df[df['compiler']=='MultiQ(2 Row)'][df['set_size']=='Set 6']['phase_duration'].sum()):.1f}x',
        fontsize=11,
        color="green",
    )

    plt.annotate(
        "",
        xy=(
            ax1.containers[2][1].get_x() + ax1.containers[2][1]._width / 2,
            df[df["compiler"] == "MultiQ(2 Row)"][df["set_size"] == "Set 8"]["phase_duration"].sum() + 2,
        ),
        xytext=(
            ax1.containers[2][1].get_x() + ax1.containers[2][1]._width / 2,
            min(df[df["compiler"] == "ZAC"][df["set_size"] == "Set 8"]["phase_duration"].sum(), first_interval[1])
            + 0.8
            * scale
            * (df[df["compiler"] == "ZAC"][df["set_size"] == "Set 8"]["phase_duration"].sum() - second_interval[0])
            + break_interval,
        ),
        fontsize=11,
        color="red",
        ha="center",
        arrowprops=dict(arrowstyle="fancy", color="green"),
    )
    ax1.text(
        ax1.containers[0][1].get_x(),
        (min(df[df["compiler"] == "ZAC"][df["set_size"] == "Set 8"]["phase_duration"].sum(), first_interval[1])
            + 0.8
            * scale
            * (df[df["compiler"] == "ZAC"][df["set_size"] == "Set 8"]["phase_duration"].sum() - second_interval[0])
            + break_interval)/2 + df[df['compiler']=='MultiQ(2 Row)'][df['set_size']=='Set 8']['phase_duration'].sum() / 2,
        f'-{(df[df['compiler']=='ZAC'][df['set_size']=='Set 8']['phase_duration'].sum()/df[df['compiler']=='MultiQ(2 Row)'][df['set_size']=='Set 8']['phase_duration'].sum()):.1f}x',
        fontsize=11,
        color="green",
    )

    plt.annotate(
        "",
        xy=(
            ax1.containers[2][2].get_x() + ax1.containers[2][2]._width / 2,
            df[df["compiler"] == "MultiQ(2 Row)"][df["set_size"] == "Set 10"]["phase_duration"].sum() + 1,
        ),
        xytext=(
            ax1.containers[2][2].get_x() + ax1.containers[2][2]._width / 2,
            min(df[df["compiler"] == "ZAC"][df["set_size"] == "Set 10"]["phase_duration"].sum(), first_interval[1])
            + 0.8
            * scale
            * (df[df["compiler"] == "ZAC"][df["set_size"] == "Set 10"]["phase_duration"].sum() - second_interval[0])
            + break_interval,
        ),
        fontsize=11,
        color="red",
        ha="center",
        arrowprops=dict(arrowstyle="fancy", color="green"),
    )
    ax1.text(
        ax1.containers[0][2].get_x(),
        (min(df[df["compiler"] == "ZAC"][df["set_size"] == "Set 10"]["phase_duration"].sum(), first_interval[1])
            + 0.8
            * scale
            * (df[df["compiler"] == "ZAC"][df["set_size"] == "Set 10"]["phase_duration"].sum() - second_interval[0])
            + break_interval)/2 + df[df['compiler']=='MultiQ(2 Row)'][df['set_size']=='Set 10']['phase_duration'].sum() / 2,
        f'-{(df[df['compiler']=='ZAC'][df['set_size']=='Set 10']['phase_duration'].sum()/df[df['compiler']=='MultiQ(2 Row)'][df['set_size']=='Set 10']['phase_duration'].sum()):.1f}x',
        fontsize=11,
        color="green",
    )

    plt.annotate(
        "",
        xy=(
            ax1.containers[2][3].get_x() + ax1.containers[2][3]._width / 2,
            df[df["compiler"] == "MultiQ(2 Row)"][df["set_size"] == "Set 12"]["phase_duration"].sum() + 1,
        ),
        xytext=(
            ax1.containers[2][3].get_x() + ax1.containers[2][3]._width / 2,
            min(df[df["compiler"] == "ZAC"][df["set_size"] == "Set 12"]["phase_duration"].sum(), first_interval[1])
            + 0.8
            * scale
            * (df[df["compiler"] == "ZAC"][df["set_size"] == "Set 12"]["phase_duration"].sum() - second_interval[0])
            + break_interval,
        ),
        fontsize=11,
        color="red",
        ha="center",
        arrowprops=dict(arrowstyle="fancy", color="green"),
    )
    ax1.text(
        ax1.containers[0][3].get_x() - 0.05,
        (min(df[df["compiler"] == "ZAC"][df["set_size"] == "Set 12"]["phase_duration"].sum(), first_interval[1])
            + 0.8
            * scale
            * (df[df["compiler"] == "ZAC"][df["set_size"] == "Set 12"]["phase_duration"].sum() - second_interval[0])
            + break_interval)/2 + df[df['compiler']=='MultiQ(2 Row)'][df['set_size']=='Set 12']['phase_duration'].sum() / 2,
        f'-{(df[df['compiler']=='ZAC'][df['set_size']=='Set 12']['phase_duration'].sum()/df[df['compiler']=='MultiQ(2 Row)'][df['set_size']=='Set 12']['phase_duration'].sum()):.1f}x',
        fontsize=11,
        color="green",
    )

    plt.annotate(
        "",
        xy=(
            ax1.containers[2][4].get_x() + ax1.containers[2][4]._width / 2,
            df[df["compiler"] == "MultiQ(2 Row)"][df["set_size"] == "Set 14"]["phase_duration"].sum() + 1,
        ),
        xytext=(
            ax1.containers[2][4].get_x() + ax1.containers[2][4]._width / 2,
            min(df[df["compiler"] == "ZAC"][df["set_size"] == "Set 14"]["phase_duration"].sum(), first_interval[1])
            + 0.8
            * scale
            * (df[df["compiler"] == "ZAC"][df["set_size"] == "Set 14"]["phase_duration"].sum() - second_interval[0])
            + break_interval,
        ),
        fontsize=11,
        color="red",
        ha="center",
        arrowprops=dict(arrowstyle="fancy", color="green"),
    )
    ax1.text(
        ax1.containers[0][4].get_x() - 0.05,
        (min(df[df["compiler"] == "ZAC"][df["set_size"] == "Set 14"]["phase_duration"].sum(), first_interval[1])
            + 0.8
            * scale
            * (df[df["compiler"] == "ZAC"][df["set_size"] == "Set 14"]["phase_duration"].sum() - second_interval[0])
            + break_interval)/2 + df[df['compiler']=='MultiQ(2 Row)'][df['set_size']=='Set 14']['phase_duration'].sum() / 2,
        f'-{(df[df['compiler']=='ZAC'][df['set_size']=='Set 14']['phase_duration'].sum()/df[df['compiler']=='MultiQ(2 Row)'][df['set_size']=='Set 14']['phase_duration'].sum()):.1f}x',
        fontsize=11,
        color="green",
    )

    ax0.set_ylim(*second_interval)
    ax1.set_ylim(*first_interval)

    ax1.grid(axis="x", visible=False)

    # Each axes has two legends and get_legend() only returns one of them.
    ax0_legends = [c for c in ax0.get_children() if isinstance(c, mlegend.Legend)]
    ax1_legends = [c for c in ax1.get_children() if isinstance(c, mlegend.Legend)]

    # Keep the stage legend; the compiler legend is added at figure level below.
    stage_legend = min(ax0_legends, key=lambda l: len(l.get_texts()))
    stage_legend.set(bbox_to_anchor=(0.37, 1.01), loc="upper left")
    for legend in ax0_legends + ax1_legends:
        if legend is not stage_legend:
            legend.remove()
    ax0.set_ylabel("")
    ax1.set_ylabel("")
    fig.text(
        0.02,
        0.5,
        "Total runtime (ms)",
        ha="center",
        va="center",
        fontsize=12,
        rotation=90,
    )
    ax0.set_xticks([])
    ax0.set_xlabel("")
    ax0.spines.bottom.set_visible(False)
    ax1.spines.top.set_visible(False)

    custom_handles = [
        mpatches.Patch(
            label="MultiQ (1 Row)",
            hatch=defaults.hatches[7],
            facecolor="none",
            edgecolor="black",
        ),
        mpatches.Patch(
            label="MultiQ (2 Row)",
            hatch=defaults.hatches[8],
            facecolor="none",
            edgecolor="black",
        ),
        mpatches.Patch(label="ZAC", hatch=defaults.hatches[2], facecolor="none", edgecolor="black"),
    ]
    legend_labels = ["MultiQ (1 Row)", "MultiQ (2 Row)", "ZAC"]
    if include_powermove:
        custom_handles.append(
            mpatches.Patch(label="PowerMove", hatch=defaults.hatches[4], facecolor="none", edgecolor="black")
        )
        legend_labels.append("PowerMove")
    if include_qmap:
        custom_handles.append(
            mpatches.Patch(label="QMAP", hatch=defaults.hatches[5], facecolor="none", edgecolor="black")
        )
        legend_labels.append("QMAP")
    if include_zap:
        custom_handles.append(
            mpatches.Patch(label="ZAP", hatch="+", facecolor="none", edgecolor="black")
        )
        legend_labels.append("ZAP")
    if include_pachinqo:
        custom_handles.append(
            mpatches.Patch(label="PachinQo", hatch=defaults.hatches[3], facecolor="none", edgecolor="black")
        )
        legend_labels.append("PachinQo")

    d = 0.5  # slope of the axis-break marks
    kwargs = dict(
        marker=[(-1, -d), (1, d)],
        markersize=12,
        linestyle="none",
        color="k",
        mec="k",
        mew=1,
        clip_on=False,
    )
    ax0.plot([0, 1], [0, 0], transform=ax0.transAxes, **kwargs)
    ax1.plot([0, 1], [1, 1], transform=ax1.transAxes, **kwargs)

    fig.legend(
        handles=custom_handles,
        loc="upper left",
        bbox_to_anchor=(0, 1),
        bbox_transform=ax0.transAxes,
        fontsize=10,
        frameon=True,
        labels=legend_labels,
        ncol=3,
        title_fontsize=11,
    )
    fig.subplots_adjust(hspace=0.1)
    fig.tight_layout(rect=(0.01, -0.03, 1.0, 1.04), h_pad=-3.8)

    fig.savefig("results/plots/e2e_durations.pdf", format="pdf")


def plot_planner():
    fig, ((ax0, ax1)) = plt.subplots(1,2, figsize=(13, 2.25), constrained_layout=True)

    eval.plot_planner_eval_fidelity_multiq(ax=ax0, title="(a) MultiQ Planner (Decoherence error)", complete=False)
    eval.plot_planner_eval_utilization_multiq(ax=ax1, title="(b) MultiQ Planner (Utilization)")

    temporal_util_weights = [0.2, 0.4, 0.6, 0.8][::-1]

    fig.legend(
        loc="lower center",
        bbox_to_anchor=(0.52, -0.02),
        ncol=5,
        fontsize=12,
        frameon=True,
        labels=["0.2", "0.4", "0.6", "0.8", "1.0"],
        title="Performance weight (1 - Utilization weight)",
        title_fontsize=11,
    )

    fig.tight_layout(rect=(-0.01, 0.085, 1.005, 1.0), h_pad=2.5, w_pad=0.3)


    fig.savefig("results/plots/planner_plot.pdf", format="pdf")

def plot_bundler():
    fig, ((ax0, ax1)) = plt.subplots(1,2, figsize=(13, 2.5), constrained_layout=True)

    eval.plot_bundler_space_util(ax=ax0, title="(a) Bundler (Spatial utilization)")
    eval.plot_bundler_temporal_util(ax=ax1, title="(b) Bundler (Temporal utilization)")

    ax0.get_xaxis().set_label_coords(0.4, -0.2)
    ax1.get_xaxis().set_label_coords(0.6, -0.2)

    temporal_util_weights = [0.2, 0.4, 0.6, 0.8][::-1]

    legends = [f"SA - {weight}" for weight in temporal_util_weights]
    legends.insert(0, "FIFO")
    fig.legend(
        loc="lower center",
        bbox_to_anchor=(0.52, -0.02),
        ncol=7,
        fontsize=10.5,
        frameon=True,
        labels=legends,
        title="Selection algorithm - Temporal utilization weight (1 - Utilization weight)",
        title_fontsize=11,
    )

    fig.tight_layout(rect=(-0.01, 0.052, 1.006, 1.02), h_pad=2.5, w_pad=0.3)


    fig.savefig("results/plots/bundler_plot.pdf", format="pdf")

def run_planner_eval(set_sizes=None, perf_weights=None, config_file=None, results_file=None):
    multiq_config_file = os.path.join(os.path.dirname(__file__), "../config/multiq/planner_bundler_config.yaml")

    run_multiq_planner_eval(multiq_config_file)


def run_bundler_eval(set_sizes=None, perf_weights=None, config_file=None, results_file=None):
    base_config_file = os.path.join(os.path.dirname(__file__), "../config/multiq/e2e_config.yaml")

    set_sizes = [6, 8, 10, 12, 14]

    random.seed(42)
    benchmark_set = open("data/multi_eval_bench_list.txt").read().splitlines()
    benchmark_set = [os.path.join(os.path.dirname(__file__), "../data/benchmarks", bench) for bench in benchmark_set]
    benchmark_sets = [random.sample(benchmark_set, size) for size in set_sizes]

    with open(base_config_file, "r") as file:
        config = yaml.safe_load(file)
        config["grid_rows"] = 1
        config["perf_weight"] = 0.8
        config["selection_algorithm"] = "fifo"

    fifo_config_file = _write_generated_config(config, "bundler_config_fifo.yaml")

    multiq_results_file = os.path.join(os.path.dirname(__file__), f"../results/multiq/bundler_results.csv")

    n_fifo = len(benchmark_sets)
    for i, benchmark_set in enumerate(benchmark_sets):
        step("MultiQ", i + 1, n_fifo, f"FIFO selection, set size {len(benchmark_set)}")
        run_multiq(
            benchmarks=benchmark_set,
            config_file=fifo_config_file,
            output_file=multiq_results_file,
        )

    temporal_util_weights = [0, 0.2, 0.4, 0.6, 0.8, 1][::-1]
    n_sa_configs = len(temporal_util_weights) * len(benchmark_sets)
    sa_config_idx = 0

    for weight in temporal_util_weights:
        with open(base_config_file, "r") as file:
            config = yaml.safe_load(file)
            config["grid_rows"] = 1
            config["perf_weight"] = 0.8
            config["selection_algorithm"] = "sa"
            config["perf_weight_selector"] = weight

        sa_config_file = _write_generated_config(config, f"bundler_config_sa_{weight}.yaml")

        for benchmark_set in benchmark_sets:
            sa_config_idx += 1
            step("MultiQ", sa_config_idx, n_sa_configs, f"SA selection, temporal utilization weight {weight}, set size {len(benchmark_set)}")
            run_multiq(
                benchmarks=benchmark_set,
                config_file=sa_config_file,
                output_file=multiq_results_file,
            )



def run_controller_eval():
    benchmark_set = open("data/multi_eval_bench_list.txt").read().splitlines()

    multiq_config_file = os.path.join(os.path.dirname(__file__), "../config/multiq/controller_config.yaml")
    multiq_results_file = os.path.join(os.path.dirname(__file__), "../results/multiq/controller_results.csv")

    zac_settings_file = os.path.join(os.path.dirname(__file__), "../config/zac/general.json")
    zac_results_file = os.path.join(os.path.dirname(__file__), "../results/zac/controller_results.csv")

    general_arch_file = os.path.join(os.path.dirname(__file__), "../config/zac/general_arch.json")
    powermove_results_file = os.path.join(os.path.dirname(__file__), "../results/powermove/controller_results.csv")
    qmap_results_file = os.path.join(os.path.dirname(__file__), "../results/qmap/controller_results.csv")
    zap_results_file = os.path.join(os.path.dirname(__file__), "../results/zap/controller_results.csv")

    set_sizes = [4, 6, 8, 10, 12, 14]

    random.seed(42)  # For reproducibility
    multi_benchmark_sets = [random.sample(benchmark_set, size) for size in set_sizes]


    n_sets = len(multi_benchmark_sets)
    for i, benchmark_set in enumerate(multi_benchmark_sets):
        what = f"merged set of size {len(benchmark_set)}"
        step("ZAC", i + 1, n_sets, what)
        run_zac_merge_benchmarks(benchmark_set, zac_settings_file, zac_results_file)
        step("PowerMove", i + 1, n_sets, what)
        run_powermove_merge_benchmarks(benchmark_set, general_arch_file, powermove_results_file)
        step("QMAP", i + 1, n_sets, what)
        run_qmap_merge_benchmarks(benchmark_set, general_arch_file, qmap_results_file)
        step("ZAP", i + 1, n_sets, what)
        run_zap_merge_benchmarks(benchmark_set, general_arch_file, zap_results_file)



def plot_controller_eval(include_powermove=True, include_qmap=True, include_zap=True):
    fig, [ax0, ax1] = utils.gen_subplots(2, 1, figsize=(13, 2.4))

    eval.plot_controler_execution_time(
        ax0,
        title="(a) Execution time",
        include_powermove=include_powermove,
        include_qmap=include_qmap,
        include_zap=include_zap,
    )
    eval.plot_controler_decoherence_error(
        ax1,
        title="(b) Decoherence error",
        include_powermove=include_powermove,
        include_qmap=include_qmap,
        include_zap=include_zap,
    )

    fig.tight_layout(rect=(-0.01, 0.05, 1.01, 1.05), w_pad=0.3)

    legend_labels = ["MultiQ (1 Row)", "MultiQ (2 Rows)", "ZAC"]
    if include_powermove:
        legend_labels.append("PowerMove")
    if include_qmap:
        legend_labels.append("QMAP")
    if include_zap:
        legend_labels.append("ZAP")

    fig.legend(
        loc="lower center",
        bbox_to_anchor=(0.52, -0.02),
        ncol=len(legend_labels),
        fontsize=11,
        frameon=True,
        labels=legend_labels,
    )

    fig.savefig("results/plots/controller_plot.pdf", format="pdf")


def plot_e2e_multiq_overhead_combined():
    fig, axes = plt.subplots(1, 3, figsize=(13, 2.7))

    eval.plot_multiq_overhead_vs_set_size(
        ax=axes[0],
        title="(a) vs set size",
        set_sizes=[4, 6, 8, 10, 12, 14],
        # The e2e results already contain the timing columns.
        results_file="results/multiq/e2e_results.csv",
    )
    eval.plot_multiq_overhead_vs_circuit_size(
        ax=axes[1],
        title="(b) vs circuit size",
        circuit_sizes=[20, 50, 100],
    )
    eval.plot_multiq_overhead_vs_qpu_size(
        ax=axes[2],
        title="(c) vs QPU size",
        qpu_capacities=[180, 300, 500, 1000],
    )

    fig.suptitle("MultiQ overhead breakdown", fontweight="bold", fontsize=12, y=0.97)

    # Replace the per-subplot legends with one shared figure legend.
    handles, labels = None, None
    for ax in axes:
        legends = [c for c in ax.get_children() if isinstance(c, mlegend.Legend)]
        if handles is None and legends:
            handles, labels = [], []
            for legend in legends:
                handles.extend(legend.legend_handles)
                labels.extend([t.get_text() for t in legend.get_texts()])
        for legend in legends:
            legend.remove()

    # Run after removing the legends and before subplots_adjust.
    fig.tight_layout(rect=(-0.01, 0.04, 1.01, 1.12), w_pad=-0.3)
    fig.subplots_adjust(bottom=0.32)
    fig.legend(handles, labels, loc="lower center", ncol=7, bbox_to_anchor=(0.5, 0.02))

    fig.savefig("results/plots/multiq_overhead_combined.pdf", format="pdf")


@dataclass
class Experiment:
    name: str
    description: str
    data_fn: callable = None
    plot_fn: callable = None


# Order matters: e2e plots need rows_sweep data, and later entries reuse e2e data.
EXPERIMENTS = [
    Experiment(
        "introduction",
        "Figure 1: fidelity and execution time vs. circuit size (ZAC, PachinQo, Atomique)",
        data_fn=run_introduction,
        plot_fn=plot_introduction,
    ),
    Experiment("rows_sweep", "Figure 9 (c): MultiQ fidelity vs. storage-zone rows", data_fn=run_multiq_rows_sweep),
    Experiment(
        "e2e",
        "Figure 9: end-to-end fidelity and circuit duration, MultiQ vs. baselines",
        data_fn=run_end_to_end_evaluation,
        plot_fn=plot_e2e_detailed,
    ),
    Experiment("e2e_total_runtime", "Figure 8: end-to-end total runtime (uses e2e data)", plot_fn=plot_e2e_total_runtime),
    Experiment("e2e_means_table", "Table 4: fidelity and execution time means (uses e2e data)", plot_fn=generate_e2e_means_table),
    Experiment("e2e_detailed_full", "Figure 17: per-benchmark fidelity and duration (uses e2e data)", plot_fn=plot_e2e_detailed_full),
    Experiment("planner", "Figure 10: virtual layout planner", data_fn=run_planner_eval, plot_fn=plot_planner),
    Experiment("bundler", "Figure 11: circuit bundler", data_fn=run_bundler_eval, plot_fn=plot_bundler),
    Experiment("controller", "Figure 12: controller", data_fn=run_controller_eval, plot_fn=plot_controller_eval),
    Experiment("overhead_circuit_size", "Figure 13 (b): overhead vs. circuit size", data_fn=run_multiq_overhead_vs_circuit_size),
    Experiment("overhead_qpu_size", "Figure 13 (c): overhead vs. QPU size", data_fn=run_multiq_overhead_vs_qpu_size),
    Experiment(
        "overhead_combined",
        "Figure 13: MultiQ classical overhead breakdown (uses e2e and overhead_* data)",
        plot_fn=plot_e2e_multiq_overhead_combined,
    ),
]


LOGS_DIR = os.path.join(os.path.dirname(__file__), "..", "results/logs")


def _run_stage(name, stage, fn, run_start):
    # Compiler output goes to results/logs/<name>.log; the terminal only shows status lines.
    status(f"=== [{name}] {stage} ===")
    start = time.time()
    with output_to_log(os.path.join(LOGS_DIR, f"{name}.log")):
        fn()
    status(f"=== [{name}] done in {time.time() - start:.1f}s (total {time.time() - run_start:.1f}s) ===")


def _parse_args():
    parser = argparse.ArgumentParser(description="Reproduce the figures of the MultiQ paper (results/plots).")
    parser.add_argument("--list", action="store_true", help="List the experiments and exit.")
    parser.add_argument("--all", action="store_true", help="Run every experiment (default).")
    parser.add_argument("--only", type=str, default=None, help="Comma-separated experiment names to run.")
    parser.add_argument("--data-only", action="store_true", help="Run the compilers without plotting.")
    parser.add_argument("--plots-only", action="store_true", help="Only plot from the results already in results/.")
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

    selected = [n.strip() for n in args.only.split(",")] if args.only else None
    if selected:
        unknown = set(selected) - {exp.name for exp in EXPERIMENTS}
        if unknown:
            raise SystemExit(f"Unknown experiment(s): {', '.join(sorted(unknown))}. Use --list to see the names.")

    os.makedirs(PLOTS_DIR, exist_ok=True)
    os.makedirs(LOGS_DIR, exist_ok=True)
    status(f"Compiler output is written to {os.path.relpath(LOGS_DIR)}/<experiment>.log")
    run_start = time.time()
    if not args.plots_only:
        def prepare():
            gen_benchmarks_from_list("data/multi_eval_bench_list.txt")
            gen_benchmarks_from_list("data/multi_eval_bench_list_pachinqo.txt")
        _run_stage("benchmarks", "preparing benchmarks", prepare, run_start)

    todo = [exp for exp in EXPERIMENTS if selected is None or exp.name in selected]
    for idx, exp in enumerate(todo):
        log_path = os.path.join(LOGS_DIR, f"{exp.name}.log")
        if os.path.isfile(log_path):
            os.remove(log_path)
        if exp.data_fn and not args.plots_only:
            _run_stage(exp.name, f"collecting data ({idx + 1}/{len(todo)})", exp.data_fn, run_start)
        if exp.plot_fn and not args.data_only:
            _run_stage(exp.name, f"plotting ({idx + 1}/{len(todo)})", exp.plot_fn, run_start)

    status(f"Done in {time.time() - run_start:.1f}s, plots in {os.path.relpath(PLOTS_DIR)}")


if __name__ == "__main__":
    main()
