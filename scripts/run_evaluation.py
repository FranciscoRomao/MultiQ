from baselines.zac_runner import run_zac_single_benchmarks, run_zac_merge_benchmarks
from baselines.pachinqo_runner import run_pachiqo_single_benchmark
from baselines.multiq_runner import (
    run_multiq_planner_eval,
    run_multiq_bundler_eval,
    run_multiq,
    run_controler_set_multiq,
)
import eval_functions as eval

# from eval_functions import plot_planner_eval_fidelity_multiq, plot_planner_eval_utilization_multiq, plot_controler_eval, plot_e2e_results_duration, plot_e2e_results_fidelity, plot_e2e_results_total_runtime, plot_bundler_temporal_util, plot_bundler_space_util
import os
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import random
from plotting import utils, bar_plot, defaults
import numpy as np
import logging
import yaml
import pandas as pd
import matplotlib.gridspec as gridspec

# Set up logging only for multiq messages
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(name)s: %(message)s")
logging.getLogger("qiskit").setLevel(logging.WARNING)
logging.getLogger("fontTools").setLevel(logging.WARNING)
logging.getLogger("matplotlib").setLevel(logging.WARNING)
logging.getLogger("stevedore").setLevel(logging.WARNING)
logging.getLogger("PIL").setLevel(logging.WARNING)

logger = logging.getLogger("multiq.evaluation")


# ----- 1. End-to-End Evaluation -----
def run_end_to_end_evaluation():
    # ----- 1. End-to-End Evaluation -----
    # Running MultiQ and baselines in multiprogramming environment (End-to-End Evaluation)

    multi_benchmark_set = open("data/multi_eval_bench_list.txt").read().splitlines()
    multi_benchmark_set_pachinqo = open("data/multi_eval_bench_list_pachinqo.txt").read().splitlines()

    set_sizes = [4, 6, 8, 10, 12, 14]

    # (nrows, set_size, perf_weight)
    set_size_perf_weights = [(1, 8, 0.35)]

    zac_settings_file = os.path.join(os.path.dirname(__file__), "../config/zac/general.json")

    multiq_config_file = os.path.join(os.path.dirname(__file__), "..", "config/multiq/e2e_config.yaml")
    zac_results_file = os.path.join(os.path.dirname(__file__), f"../results/zac/e2e_results.csv")
    pachinqo_results_file = os.path.join(os.path.dirname(__file__), f"../results/pachinqo/e2e_results.csv")
    multiq_results_file = os.path.join(os.path.dirname(__file__), f"../results/multiq/e2e_results.csv")

    # Running baselines (ZAC and Pachinqo) on single benchmarks
    for _, bench in enumerate(multi_benchmark_set_pachinqo):
        run_pachiqo_single_benchmark(bench, zac_settings_file, pachinqo_results_file)
    
    for _, bench in enumerate(multi_benchmark_set):
        run_zac_single_benchmarks(bench, zac_settings_file, zac_results_file)
    

    # Selecting random subsets of benchmarks for MultiQ evaluation
    random.seed(42)  # For reproducibility
    multi_benchmark_sets = [random.sample(multi_benchmark_set, size) for size in set_sizes]

    for benchmark_set in multi_benchmark_sets:
        print(f"Running MultiQ with benchmark set of size {len(benchmark_set)}")

        for rows in [1, 2]:
            multiq_config_file = os.path.join(os.path.dirname(__file__), multiq_config_file)
            with open(multiq_config_file, "r") as file:
                config = yaml.safe_load(file)
                config["grid_rows"] = rows
                config["grid_cols"] = len(benchmark_set)
                config["selector_algo"] = "fifo"
                if rows == 1 and len(benchmark_set) == 4:
                    config["perf_weight"] = 0.7  # 0.72 full 0.68 is best (0.645092)
                    #continue
                if rows == 2 and len(benchmark_set) == 4:
                    config["perf_weight"] = 0.92  # 1 full 0.94 is best (0.645092)
                    #continue
                if rows == 1 and len(benchmark_set) == 6:
                    config["perf_weight"] = 0.52  # 0.53 full 0.52 is best (0.667146)
                    #continue
                if rows == 2 and len(benchmark_set) == 6:
                    config["perf_weight"] = 1  # 1 full
                    #continue
                if rows == 1 and len(benchmark_set) == 8:
                    config["perf_weight"] = 0.41
                    #continue
                elif rows == 2 and len(benchmark_set) == 8:
                    config["perf_weight"] = 0.8  # 0.84 full 0.8 is best (0.667146)
                    #continue
                elif rows == 1 and len(benchmark_set) == 10:
                    config["perf_weight"] = 0.33
                    #continue
                elif rows == 2 and len(benchmark_set) == 10:
                    config["perf_weight"] = 0.6  # 0.64 full #0.6 is best
                    #continue
                elif rows == 1 and len(benchmark_set) == 12:
                    config["perf_weight"] = 0.18  # 0.24 full 0.18 is better
                    #continue
                elif rows == 2 and len(benchmark_set) == 12:
                    config["perf_weight"] = 0.48  # 0.51 full 0.48 is best (0.598073)
                    #continue
                elif rows == 1 and len(benchmark_set) == 14:
                    config["perf_weight"] = 0.17
                    #continue
                elif rows == 2 and len(benchmark_set) == 14:
                    config["perf_weight"] = 0.4  # 0.42 full #0.4 is best
                    #continue
            with open(multiq_config_file, "w") as file:
                yaml.dump(config, file)

            print(f"Running MultiQ with {rows} rows")

            run_multiq(
                benchmarks=benchmark_set,
                config_file=multiq_config_file,
                output_file=multiq_results_file,
            )


def plot_e2e_detailed():
    # ----- Plot end-to-end evaluation results fidelity and exection time for MultiQ and baselines

    detailed_set_sizes = [8]

    zac_results_file = os.path.join(os.path.dirname(__file__), f"../results/zac/e2e_results.csv")

    zac_results_file = os.path.join(os.path.dirname(__file__), f"../results/zac/e2e_results.csv")
    pachinqo_results_file = os.path.join(os.path.dirname(__file__), f"../results/pachinqo/e2e_results.csv")
    multiq_results_file = os.path.join(os.path.dirname(__file__), f"../results/multiq/e2e_results.csv")

    fig = plt.figure(figsize=(13, 2.5), constrained_layout=True)
    gs = gridspec.GridSpec(1,2, figure=fig)

    axes = []
    for idx in range(len(detailed_set_sizes)):
        axes.append(fig.add_subplot(gs[idx * 2]))
        axes.append(fig.add_subplot(gs[idx * 2 + 1]))

    print("Plotting fidelity")
    letters = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"]
    for idx, set in enumerate(detailed_set_sizes):
        print(f"Plotting results for benchmark set of size {set}")
        eval.plot_e2e_results_fidelity(
            ax=axes[idx],
            set_size=set,
            title=f"({letters[idx]}) Fidelity (Set size: {set})",
            multiq_results_file=multiq_results_file,
            zac_results_file=zac_results_file,
            pachinqo_results_file=pachinqo_results_file,
        )

        axes[idx].set_xlabel(None)

    print("Plotting circuit duration")
    for idx, set in enumerate(detailed_set_sizes):
        print(f"Plotting results for benchmark set of size {set}")
        eval.plot_e2e_results_duration(
            ax=axes[idx + len(detailed_set_sizes)],
            set_size=set,
            title=f"({letters[idx+len(detailed_set_sizes)]}) Execution time (Set size: {set})",
            multiq_results_file=multiq_results_file,
            zac_results_file=zac_results_file,
            pachinqo_results_file=pachinqo_results_file,
        )
        axes[idx + len(detailed_set_sizes)].set_xlabel(None)

    fig.tight_layout(w_pad=0.3, rect=(-0.013, 0.06, 1.005, 1.045))

    fig.legend(loc='lower center', bbox_to_anchor=(0.52, -0.005), ncol=5, fontsize=11, frameon=True, labels=['MultiQ (1 Row)', 'MultiQ (2 Row)', 'ZAC'], title_fontsize=11)

    fig.savefig("results/plots/e2e_plot_detailed.pdf", format="pdf")


def plot_e2e_detailed_full():
    # ----- Plot end-to-end evaluation results fidelity and exection time for MultiQ and baselines

    detailed_set_sizes = [4, 6, 8, 10, 12, 14]

    zac_results_file = os.path.join(os.path.dirname(__file__), f"../results/zac/e2e_results.csv")

    zac_results_file = os.path.join(os.path.dirname(__file__), f"../results/zac/e2e_results.csv")
    pachinqo_results_file = os.path.join(os.path.dirname(__file__), f"../results/pachinqo/e2e_results.csv")
    multiq_results_file = os.path.join(os.path.dirname(__file__), f"../results/multiq/e2e_results.csv")

    fig = plt.figure(figsize=(15, 2.5 * len(detailed_set_sizes)), constrained_layout=True)

    gs = gridspec.GridSpec(len(detailed_set_sizes), 2, figure=fig, width_ratios=[1, 1])

    axes = []
    for idx in range(len(detailed_set_sizes)):
        axes.append(fig.add_subplot(gs[idx * 2]))
        axes.append(fig.add_subplot(gs[idx * 2 + 1]))

    print("Plotting fidelity")
    letters = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l"]
    for idx, set in enumerate(detailed_set_sizes):
        print(f"Plotting results for benchmark set of size {set}")
        eval.plot_e2e_results_fidelity(
            ax=axes[idx * 2],
            set_size=set,
            title=f"({letters[idx]}) Fidelity (Set size: {set})",
            multiq_results_file=multiq_results_file,
            zac_results_file=zac_results_file,
            pachinqo_results_file=pachinqo_results_file,
            include_pachinqo=True,
        )

        axes[idx * 2].set_xlabel(None)

    print("Plotting circuit duration")
    for idx, set in enumerate(detailed_set_sizes):
        print(f"Plotting results for benchmark set of size {set}")
        eval.plot_e2e_results_duration(
            ax=axes[idx * 2 + 1],
            set_size=set,
            title=f"({letters[idx+len(detailed_set_sizes)]}) Execution time (Set size: {set})",
            multiq_results_file=multiq_results_file,
            zac_results_file=zac_results_file,
            pachinqo_results_file=pachinqo_results_file,
            include_pachinqo=True,
        )
        axes[idx * 2 + 1].set_xlabel(None)

    # fig.tight_layout(w_pad=0.2, h_pad=0.1, rect=(-0.008, 0.05, 1.005, 1.02))
    fig.tight_layout(w_pad=0.2, h_pad=0, rect=(-0.01, 0.005, 1.005, 1.005))
    fig.legend(
        loc="lower center",
        bbox_to_anchor=(0.52, -0.005),
        ncol=5,
        fontsize=11,
        frameon=True,
        labels=["MultiQ (1 Row)", "MultiQ (2 Row)", "ZAC", "PachinQo"],
        title_fontsize=11,
    )

    fig.savefig("results/plots/e2e_plot_detailed_full.pdf", format="pdf")


def plot_e2e_total_runtime():
    # ----- Plot end-to-end evaluation results total runtime for MultiQ and baselines

    fig, [ax0, ax1] = utils.gen_subplots(1, 2, figsize=(7, 3), height_ratios=[0.8, 1])

    set_sizes = [6, 8, 10, 12, 14]

    first_interval = (0, 200)
    second_interval = (500, 2000)

    scale = (first_interval[1] - first_interval[0]) / (second_interval[1] - second_interval[0])

    break_interval = 30

    # fig, (ax0,ax1) = plt.subplots(2, 1, figsize=(7, 3), )

    eval.plot_e2e_results_total_runtime(
        ax=ax0,
        title="Total runtime",
        set_size=set_sizes,
        higher_lower_is_better="lower",
        xticks_visible=False,
    )
    df = eval.plot_e2e_results_total_runtime(
        ax=ax1,
        title="",
        set_size=set_sizes,
        higher_lower_is_better=None,
        xticks_visible=True,
    )

    plt.annotate(
        "",
        xy=(
            ax1.containers[2][0].get_x() + ax1.containers[2][0]._width / 2,
            df[df["compiler"] == "MultiQ\n2 Row"][df["set_size"] == "Set 6"]["phase_duration"].sum() + 1,
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
            + break_interval)/2 + df[df['compiler']=='MultiQ\n2 Row'][df['set_size']=='Set 6']['phase_duration'].sum() / 2,
        f'-{(df[df['compiler']=='ZAC'][df['set_size']=='Set 6']['phase_duration'].sum()/df[df['compiler']=='MultiQ\n2 Row'][df['set_size']=='Set 6']['phase_duration'].sum()):.1f}x',
        fontsize=11,
        color="green",
    )

    plt.annotate(
        "",
        xy=(
            ax1.containers[2][1].get_x() + ax1.containers[2][1]._width / 2,
            df[df["compiler"] == "MultiQ\n2 Row"][df["set_size"] == "Set 8"]["phase_duration"].sum() + 2,
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
            + break_interval)/2 + df[df['compiler']=='MultiQ\n2 Row'][df['set_size']=='Set 8']['phase_duration'].sum() / 2,
        f'-{(df[df['compiler']=='ZAC'][df['set_size']=='Set 8']['phase_duration'].sum()/df[df['compiler']=='MultiQ\n2 Row'][df['set_size']=='Set 8']['phase_duration'].sum()):.1f}x',
        fontsize=11,
        color="green",
    )

    plt.annotate(
        "",
        xy=(
            ax1.containers[2][2].get_x() + ax1.containers[2][2]._width / 2,
            df[df["compiler"] == "MultiQ\n2 Row"][df["set_size"] == "Set 10"]["phase_duration"].sum() + 1,
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
            + break_interval)/2 + df[df['compiler']=='MultiQ\n2 Row'][df['set_size']=='Set 10']['phase_duration'].sum() / 2,
        f'-{(df[df['compiler']=='ZAC'][df['set_size']=='Set 10']['phase_duration'].sum()/df[df['compiler']=='MultiQ\n2 Row'][df['set_size']=='Set 10']['phase_duration'].sum()):.1f}x',
        fontsize=11,
        color="green",
    )

    plt.annotate(
        "",
        xy=(
            ax1.containers[2][3].get_x() + ax1.containers[2][3]._width / 2,
            df[df["compiler"] == "MultiQ\n2 Row"][df["set_size"] == "Set 12"]["phase_duration"].sum() + 1,
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
            + break_interval)/2 + df[df['compiler']=='MultiQ\n2 Row'][df['set_size']=='Set 12']['phase_duration'].sum() / 2,
        f'-{(df[df['compiler']=='ZAC'][df['set_size']=='Set 12']['phase_duration'].sum()/df[df['compiler']=='MultiQ\n2 Row'][df['set_size']=='Set 12']['phase_duration'].sum()):.1f}x',
        fontsize=11,
        color="green",
    )

    plt.annotate(
        "",
        xy=(
            ax1.containers[2][4].get_x() + ax1.containers[2][4]._width / 2,
            df[df["compiler"] == "MultiQ\n2 Row"][df["set_size"] == "Set 14"]["phase_duration"].sum() + 1,
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
            + break_interval)/2 + df[df['compiler']=='MultiQ\n2 Row'][df['set_size']=='Set 14']['phase_duration'].sum() / 2,
        f'-{(df[df['compiler']=='ZAC'][df['set_size']=='Set 14']['phase_duration'].sum()/df[df['compiler']=='MultiQ\n2 Row'][df['set_size']=='Set 14']['phase_duration'].sum()):.1f}x',
        fontsize=11,
        color="green",
    )

    # print(f'Mean ratios: \n \t MultiQ (1 Row) vs ZAC {df[df["compiler"] == "MultiQ (1 Row)"][""].mean() - df[df["compiler"] == "ZAC"]["cir_duration"].mean()} \n \t MultiQ (2 Row) vs ZAC {df[df["compiler"] == "MultiQ (2 Row)"]["cir_duration"].mean() - df[df["compiler"] == "ZAC"]["cir_duration"].mean()}')

    ax0.set_ylim(*second_interval)
    ax1.set_ylim(*first_interval)

    ax1.grid(axis="x", visible=False)

    ax0.get_legend().set(bbox_to_anchor=(0.3, 0.385))
    ax1.get_legend().remove()  # Remove legend from the first plot
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
    ax0.set_xticks([])  # Hide x-ticks for the first plot
    ax0.set_xlabel("")  # Remove x-label from the first plot
    ax0.spines.bottom.set_visible(False)  # Hide the top spine for the first plot
    ax1.spines.top.set_visible(False)  # Hide the top spine for the second plot

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

    d = 0.5  # proportion of vertical to horizontal extent of the slanted line
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

    # fig.legend(handles=custom_handles, bbox_to_anchor=(0.53, 0.92), fontsize=11, frameon=True, labels=['MultiQ (1 Row)', 'MultiQ (2 Row)', 'ZAC'], title_fontsize=11)
    fig.legend(
        handles=custom_handles,
        bbox_to_anchor=(0.365, 0.9),
        fontsize=11,
        frameon=True,
        labels=["MultiQ (1 Row)", "MultiQ (2 Row)", "ZAC"],
        title_fontsize=11,
    )
    fig.subplots_adjust(hspace=0.1)
    fig.tight_layout(rect=(0.01, -0.03, 1.03, 1.04), h_pad=-3.8)

    fig.savefig("results/plots/e2e_durations.pdf", format="pdf")


def plot_e2e_total_runtime_complete():
    # ----- Plot end-to-end evaluation results total runtime for MultiQ and baselines

    set_sizes = [4, 6, 8, 10, 12, 14]

    fig, (ax0) = plt.subplots(1, 1, figsize=(13, 3), constrained_layout=True)

    df = eval.plot_e2e_results_total_runtime(ax=ax0, title="Total runtime", set_size=set_sizes, include_pachinqo=True)

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
        mpatches.Patch(
            label="PachinQo",
            hatch=defaults.hatches[3],
            facecolor="none",
            edgecolor="black",
        ),
    ]

    plt.annotate('', xy=(ax0.containers[2][0].get_x() + ax0.containers[2][0]._width/2, df[df['compiler']=='MultiQ\n2 Row'][df['set_size']=='Set 4']['phase_duration'].sum()+1), xytext=(ax0.containers[2][0].get_x() + ax0.containers[2][0]._width/2, df[df['compiler']=='ZAC'][df['set_size']=='Set 4']['phase_duration'].sum()), fontsize=11, color='red', ha='center', arrowprops=dict(arrowstyle='fancy', color='green'))
    ax0.text(ax0.containers[0][0].get_x()+ ax0.containers[0][0]._width/4, df[df['compiler']=='ZAC'][df['set_size']=='Set 4']['phase_duration'].sum()/2, f'-{(df[df['compiler']=='ZAC'][df['set_size']=='Set 4']['phase_duration'].sum()/df[df['compiler']=='MultiQ\n2 Row'][df['set_size']=='Set 4']['phase_duration'].sum()):.1f}x', fontsize=11, color='green')

    plt.annotate('', xy=(ax0.containers[2][1].get_x() + ax0.containers[2][1]._width/2, df[df['compiler']=='MultiQ\n2 Row'][df['set_size']=='Set 6']['phase_duration'].sum()+2), xytext=(ax0.containers[2][1].get_x() + ax0.containers[2][1]._width/2, df[df['compiler']=='ZAC'][df['set_size']=='Set 6']['phase_duration'].sum()), fontsize=11, color='red', ha='center', arrowprops=dict(arrowstyle='fancy', color='green'))
    ax0.text(ax0.containers[0][1].get_x()+ ax0.containers[0][1]._width/4, df[df['compiler']=='ZAC'][df['set_size']=='Set 6']['phase_duration'].sum()/2, f'-{(df[df['compiler']=='ZAC'][df['set_size']=='Set 6']['phase_duration'].sum()/df[df['compiler']=='MultiQ\n2 Row'][df['set_size']=='Set 6']['phase_duration'].sum()):.1f}x', fontsize=11, color='green')

    plt.annotate('', xy=(ax0.containers[2][2].get_x() + ax0.containers[2][2]._width/2, df[df['compiler']=='MultiQ\n2 Row'][df['set_size']=='Set 8']['phase_duration'].sum()+1), xytext=(ax0.containers[2][2].get_x() + ax0.containers[2][2]._width/2, df[df['compiler']=='ZAC'][df['set_size']=='Set 8']['phase_duration'].sum()), fontsize=11, color='red', ha='center', arrowprops=dict(arrowstyle='fancy', color='green'))
    ax0.text(ax0.containers[0][2].get_x()+ ax0.containers[0][2]._width/4, df[df['compiler']=='ZAC'][df['set_size']=='Set 8']['phase_duration'].sum()/2, f'-{(df[df['compiler']=='ZAC'][df['set_size']=='Set 8']['phase_duration'].sum()/df[df['compiler']=='MultiQ\n2 Row'][df['set_size']=='Set 8']['phase_duration'].sum()):.1f}x', fontsize=11, color='green')

    plt.annotate('', xy=(ax0.containers[2][3].get_x() + ax0.containers[2][3]._width/2, df[df['compiler']=='MultiQ\n2 Row'][df['set_size']=='Set 10']['phase_duration'].sum()+1), xytext=(ax0.containers[2][3].get_x() + ax0.containers[2][3]._width/2, df[df['compiler']=='ZAC'][df['set_size']=='Set 10']['phase_duration'].sum()), fontsize=11, color='red', ha='center', arrowprops=dict(arrowstyle='fancy', color='green'))
    ax0.text(ax0.containers[0][3].get_x(), df[df['compiler']=='ZAC'][df['set_size']=='Set 10']['phase_duration'].sum()/2, f'-{(df[df['compiler']=='ZAC'][df['set_size']=='Set 10']['phase_duration'].sum()/df[df['compiler']=='MultiQ\n2 Row'][df['set_size']=='Set 10']['phase_duration'].sum()):.1f}x', fontsize=11, color='green')

    plt.annotate('', xy=(ax0.containers[2][4].get_x() + ax0.containers[2][4]._width/2, df[df['compiler']=='MultiQ\n2 Row'][df['set_size']=='Set 12']['phase_duration'].sum()+1), xytext=(ax0.containers[2][4].get_x() + ax0.containers[2][4]._width/2, df[df['compiler']=='ZAC'][df['set_size']=='Set 12']['phase_duration'].sum()), fontsize=11, color='red', ha='center', arrowprops=dict(arrowstyle='fancy', color='green'))
    ax0.text(ax0.containers[0][4].get_x(), df[df['compiler']=='ZAC'][df['set_size']=='Set 12']['phase_duration'].sum()/2, f'-{(df[df['compiler']=='ZAC'][df['set_size']=='Set 12']['phase_duration'].sum()/df[df['compiler']=='MultiQ\n2 Row'][df['set_size']=='Set 12']['phase_duration'].sum()):.1f}x', fontsize=11, color='green')

    plt.annotate('', xy=(ax0.containers[2][5].get_x() + ax0.containers[2][5]._width/2, df[df['compiler']=='MultiQ\n2 Row'][df['set_size']=='Set 14']['phase_duration'].sum()+1), xytext=(ax0.containers[2][5].get_x() + ax0.containers[2][5]._width/2, df[df['compiler']=='ZAC'][df['set_size']=='Set 14']['phase_duration'].sum()), fontsize=11, color='red', ha='center', arrowprops=dict(arrowstyle='fancy', color='green'))
    ax0.text(ax0.containers[0][5].get_x(), df[df['compiler']=='ZAC'][df['set_size']=='Set 14']['phase_duration'].sum()/2, f'-{(df[df['compiler']=='ZAC'][df['set_size']=='Set 14']['phase_duration'].sum()/df[df['compiler']=='MultiQ\n2 Row'][df['set_size']=='Set 14']['phase_duration'].sum()):.1f}x', fontsize=11, color='green')

    #print(f'Mean ratios: \n \t MultiQ (1 Row) vs ZAC {df[df["compiler"] == "MultiQ (1 Row)"][""].mean() - df[df["compiler"] == "ZAC"]["cir_duration"].mean()} \n \t MultiQ (2 Row) vs ZAC {df[df["compiler"] == "MultiQ (2 Row)"]["cir_duration"].mean() - df[df["compiler"] == "ZAC"]["cir_duration"].mean()}')

    fig.legend(
        handles=custom_handles,
        bbox_to_anchor=(0.33, 0.923),
        fontsize=11,
        frameon=True,
        labels=["MultiQ (1 Row)", "MultiQ (2 Row)", "ZAC", "PachinQo"],
        title_fontsize=11,
    )

    fig.savefig("results/plots/e2e_durations_complete.pdf", format="pdf")


def plot_e2e_means():
    # ----- Plot end-to-end evaluation results fidelity and exection time only for Means

    zac_results_file = os.path.join(os.path.dirname(__file__), f"../results/zac/e2e_results.csv")
    pachinqo_results_file = os.path.join(os.path.dirname(__file__), f"../results/pachinqo/e2e_results.csv")
    multiq_results_file = os.path.join(os.path.dirname(__file__), f"../results/multiq/e2e_results.csv")

    set_sizes = [4, 6, 8, 10, 12, 14]

    fig, (ax0, ax1) = plt.subplots(2, 1, figsize=(5, 5))

    eval.plot_e2e_results_fidelity_means(
        ax=ax0,
        set_sizes=set_sizes,
        title=f"Fidelity",
        multiq_results_file=multiq_results_file,
        zac_results_file=zac_results_file,
        pachinqo_results_file=pachinqo_results_file,
    )
    eval.plot_e2e_results_duration_means(
        ax=ax1,
        set_sizes=set_sizes,
        title=f"Circuit duration",
        multiq_results_file=multiq_results_file,
        zac_results_file=zac_results_file,
        pachinqo_results_file=pachinqo_results_file,
    )

    ax1.tick_params(labelsize=12)

    ax0.set_xlabel("")

    fig.legend(
        loc="lower center",
        bbox_to_anchor=(0.52, -0.007),
        ncol=5,
        fontsize=11,
        frameon=True,
        labels=["ZAC", "MultiQ (1 Row)", "MultiQ (2 Row)"],
        title_fontsize=11,
    )

    fig.savefig("results/plots/e2e_plot_means.pdf", format="pdf")


def plot_planner_bundler():
    # ----- Plotting Planner and Bundler Results ----
    fig, ((ax0, ax1), (ax2, ax3)) = plt.subplots(2, 2, figsize=(15, 5.2), constrained_layout=True)

    eval.plot_planner_eval_fidelity_multiq(ax=ax0, title="(a) MultiQ Planner (Decoherence error)", complete=False)
    eval.plot_planner_eval_utilization_multiq(ax=ax1, title="(b) MultiQ Planner (Utilization)")

    # fig.legend(loc='lower center', bbox_to_anchor=(0.52, 0), ncol=5, fontsize=12, frameon=True, labels=['0.2', '0.4', '0.6', '0.8', '1.0'], title='Performance weight', title_fontsize=10)

    eval.plot_bundler_space_util(ax=ax2, title="(c) Bundler (Spatial utilization)")
    eval.plot_bundler_temporal_util(ax=ax3, title="(d) Bundler (Temporal utilization)")

    # change xlabel position
    ax2.get_xaxis().set_label_coords(0.4, -0.2)
    ax3.get_xaxis().set_label_coords(0.6, -0.2)

    temporal_util_weights = [0.2, 0.4, 0.6, 0.8][::-1]

    fig.legend(
        loc="lower center",
        bbox_to_anchor=(0.52, 0.48),
        ncol=5,
        fontsize=12,
        frameon=True,
        labels=["0.2", "0.4", "0.6", "0.8", "1.0"],
        title="Performance weight",
        title_fontsize=11,
    )

    legends = [f"SA - {weight}" for weight in temporal_util_weights]
    legends.insert(0, "FIFO")  # Ensure 'fifo' is first
    fig.legend(
        loc="lower center",
        bbox_to_anchor=(0.52, -0.002),
        ncol=7,
        fontsize=12,
        frameon=True,
        labels=legends,
        title="Selection algorithm - Temporal utilization weight",
        title_fontsize=11,
    )

    fig.tight_layout(rect=(-0.01, 0.035, 1.005, 1.015), h_pad=2.5, w_pad=0.3)

    """
    fig.savefig('results/plots/bundler_plots.pdf', format='pdf')

    fig.tight_layout(rect=(0,0.08,1,1), w_pad=-0.4)

    fig.savefig('results/plots/planner_bundler_plots.pdf', format='pdf')

    fig.tight_layout(rect=(0,0.08,1,1), w_pad=-0.4)

    fig.legend(loc='lower center', bbox_to_anchor=(0.52, 0), ncol=5, fontsize=12, frameon=True, labels=['0.2', '0.4', '0.6', '0.8', '1.0'], title='Performance weight', title_fontsize=11)
    """

    fig.savefig("results/plots/planner_bundler_plot.pdf", format="pdf")


def run_planner_eval(set_sizes=None, perf_weights=None, config_file=None, results_file=None):
    multiq_config_file = os.path.join(os.path.dirname(__file__), "../config/multiq/planner_bundler_config.yaml")

    run_multiq_planner_eval(multiq_config_file)


def run_bundler_eval(set_sizes=None, perf_weights=None, config_file=None, results_file=None):
    # 2.2 Bundler Evaluation
    multiq_config_file = os.path.join(os.path.dirname(__file__), "../config/multiq/e2e_config.yaml")

    # set_sizes = [4,6,8,10]
    set_sizes = [6, 8, 10, 12, 14]

    random.seed(42)
    benchmark_set = open("data/multi_eval_bench_list.txt").read().splitlines()
    benchmark_set = [os.path.join(os.path.dirname(__file__), "../data/benchmarks", bench) for bench in benchmark_set]
    benchmark_sets = [random.sample(benchmark_set, size) for size in set_sizes]

    # data = pd.DataFrame(columns=['benchmarks',
    #                             'tile_widths',
    #                             'algorithm',
    #                             'perf_weight',
    #                             'nbins',
    #                             'temporal_utilization'])

    # Setting up config for fifo selection evaluation
    with open(multiq_config_file, "r") as file:
        config = yaml.safe_load(file)
        config["grid_rows"] = 1
        # config['grid_cols'] = len(benchmark_set) // rows
        config["perf_weight"] = 0.8
        config["selection_algorithm"] = "fifo"

    with open(multiq_config_file, "w") as file:
        yaml.dump(config, file)

    # ----- Running MultiQ with fifo selection algorithm

    multiq_results_file = os.path.join(os.path.dirname(__file__), f"../results/multiq/bundler_results.csv")

    for benchmark_set in benchmark_sets:
        bench = "-".join([os.path.basename(b).split(".")[0] for b in benchmark_set])
        logger.info(f"Running MultiQ with FIFO selection algorithm on benchmark set: {bench}")
        run_multiq(
            benchmarks=benchmark_set,
            config_file=multiq_config_file,
            output_file=multiq_results_file,
        )

    temporal_util_weights = [0, 0.2, 0.4, 0.6, 0.8, 1][::-1]  # Performance selection weights for bundler evaluation

    for weight in temporal_util_weights:
        # Setting up config for fifo selection evaluation
        with open(multiq_config_file, "r") as file:
            config = yaml.safe_load(file)
            config["grid_rows"] = 1
            # config['grid_cols'] = len(benchmark_set) // rows
            config["perf_weight"] = 0.8
            config["selection_algorithm"] = "sa"
            config["perf_weight_selector"] = weight

        with open(multiq_config_file, "w") as file:
            yaml.dump(config, file)

        for benchmark_set in benchmark_sets:
            bench = "-".join([os.path.basename(b).split(".")[0] for b in benchmark_set])
            logger.info(
                f"Running MultiQ with bundler evaluation on benchmark: {bench} with temporal utilization weight: {weight}"
            )
            run_multiq(
                benchmarks=benchmark_set,
                config_file=multiq_config_file,
                output_file=multiq_results_file,
            )

    """
    # Plot bundler evaluation results
    fig, [ax0, ax1] = utils.gen_subplots(2,1, figsize=(13.2, 3.5))

    eval.plot_bundler_space_util(ax=ax0, title="a) Bundler (Spatial utilization)")
    eval.plot_bundler_temporal_util(ax=ax1, title="b) Bundler (Temporal utilization)")

    fig.tight_layout(rect=(0,0.11,1,1), h_pad=-0.1, w_pad=-0.01)
    
    legends = [f'SA - {weight}' for weight in temporal_util_weights]
    legends.insert(0, 'FIFO')  # Ensure 'fifo' is first

    fig.legend(loc='lower center', bbox_to_anchor=(0.52, -0.01), ncol=5, fontsize=12, frameon=True, labels=legends, title='Selection algorithm - Temporal utilization weight', title_fontsize=11)

    fig.savefig('results/plots/bundler_plots.pdf', format='pdf')
    """


def run_controller_eval():
    benchmark_set = open("data/multi_eval_bench_list.txt").read().splitlines()

    multiq_config_file = os.path.join(os.path.dirname(__file__), "../config/multiq/controller_config.yaml")
    multiq_results_file = os.path.join(os.path.dirname(__file__), "../results/multiq/controller_results.csv")

    zac_settings_file = os.path.join(os.path.dirname(__file__), "../config/zac/general.json")
    zac_results_file = os.path.join(os.path.dirname(__file__), "../results/zac/controller_results.csv")

    set_sizes = [4, 6, 8, 10, 12, 14]  # Tile widths

    random.seed(42)  # For reproducibility
    multi_benchmark_sets = [random.sample(benchmark_set, size) for size in set_sizes]

    """
    #pachinqo_settings_file = os.path.join(os.path.dirname(__file__), "../../config/pachinqo/general.json")
    
    for row in [1,2]:
        # Setting up config for controller evaluation
        with open(multiq_config_file, 'r') as file:
            config = yaml.safe_load(file)
            config['grid_rows'] = row
            #config['grid_cols'] = len(multi_benchmark_sets[0]) // row

        with open(multiq_config_file, 'w') as file:
            yaml.dump(config, file)

        print(f"Running MultiQ with {row} rows")
        #run_controler_set_multiq(benchmarks=multi_benchmark_sets[0], config_file=multiq_config_file, output_file=multiq_results_file)
    
    #for benchmark_set in multi_benchmark_sets:
            run_controler_set_multiq(benchmarks=benchmark_set, config_file=multiq_config_file, output_file=multiq_results_file)
    for benchmark_set in multi_benchmark_sets:

        for rows in [1,2]:
            multiq_config_file = os.path.join(os.path.dirname(__file__), multiq_config_file)
            with open(multiq_config_file, 'r') as file:
                config = yaml.safe_load(file)
                config['grid_rows'] = rows
                config['grid_cols'] = len(benchmark_set)
                config['selector_algo'] = 'fifo'
                if rows == 1 and len(benchmark_set) == 4:
                    config['perf_weight'] = 0.7 #0.72 full 0.68 is best (0.645092)
                    continue
                if rows == 2 and len(benchmark_set) == 4:
                    config['perf_weight'] = 0.92 #1 full 0.94 is best (0.645092)
                    continue
                if rows == 1 and len(benchmark_set) == 6:
                    config['perf_weight'] = 0.52 #0.53 full 0.52 is best (0.667146)
                    continue
                if rows == 2 and len(benchmark_set) == 6:
                    config['perf_weight'] = 1 #1 full
                    continue
                if rows == 1 and len(benchmark_set) == 8:
                    config['perf_weight'] = 0.41
                    continue
                elif rows == 2 and len(benchmark_set) == 8:
                    config['perf_weight'] = 0.8 #0.84 full 0.8 is best (0.667146)
                    continue
                elif rows == 1 and len(benchmark_set) == 10:
                    config['perf_weight'] = 0.33
                    continue
                elif rows == 2 and len(benchmark_set) == 10:
                    config['perf_weight'] = 0.6 #0.64 full #0.6 is best
                    continue
                elif rows == 1 and len(benchmark_set) == 12:
                    config['perf_weight'] = 0.18 #0.24 full 0.18 is better
                    continue
                elif rows == 2 and len(benchmark_set) == 12:
                    config['perf_weight'] = 0.48 #0.51 full 0.48 is best (0.598073)
                    continue
                elif rows == 1 and len(benchmark_set) == 14:
                    config['perf_weight'] = 0.17
                    continue
                elif rows == 2 and len(benchmark_set) == 14:
                    config['perf_weight'] = 0.4 #0.42 full #0.4 is best
                    continue
            with open(multiq_config_file, 'w') as file:
                yaml.dump(config, file)

            print(f"Running MultiQ with {rows} rows")
            #multiq_results_file = os.path.join(os.path.dirname(__file__), f'../results/multiq/e2e_results_set{len(benchmark_set)}.csv')

            run_multiq(benchmarks=benchmark_set, config_file=multiq_config_file, output_file=multiq_results_file)
    """

    for benchmark_set in multi_benchmark_sets:
        run_zac_merge_benchmarks(benchmark_set, zac_settings_file, zac_results_file)
        # run_pachiqo_single_benchmarks(benchmark_set, pachinqo_settings_file, output_file="results/pachinqo_results.csv")


def plot_controller_eval():
    fig, [ax0, ax1] = utils.gen_subplots(2, 1, figsize=(13, 2.4))

    eval.plot_controler_execution_time(ax0, title="(a) Execution time")
    eval.plot_controler_decoherence_error(ax1, title="(b) Decoherence error")

    fig.tight_layout(rect=(-0.01, 0, 1.01, 1.05), w_pad=0.3)

    fig.legend(
        loc="lower center",
        bbox_to_anchor=(0.52, -0.01),
        ncol=3,
        fontsize=11,
        frameon=True,
        labels=["MultiQ (1 Row)", "MultiQ (2 Rows)", "ZAC"],
    )

    fig.savefig("results/plots/controller_plot.pdf", format="pdf")

if __name__ == "__main__":
    # Run the script directly to execute the evaluations
    # Uncomment the sections you want to run
    '''
    run_end_to_end_evaluation()
    plot_e2e_detailed()
    plot_e2e_detailed_full()
    plot_e2e_total_runtime()

    plot_e2e_total_runtime_complete()

    '''
    plot_e2e_means()
    '''

    run_planner_eval()

    run_bundler_eval()

    plot_planner_bundler()
    
    run_controller_eval()

    plot_controller_eval()
    '''
