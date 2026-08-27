import argparse
import os
import sys
import time
from dataclasses import dataclass

# Makes this runnable both as `python scripts/run_evaluation.py` (from repo root)
# and as `python -m scripts.run_evaluation` (from repo root). The two styles put
# different things on sys.path: `-m` adds the repo root (needed by
# eval_functions.py's `from scripts.plotting import ...`), while direct script
# invocation adds scripts/ itself (needed by this file's own `from baselines...`/
# `from plotting...`). Add both explicitly so either invocation works.
_scripts_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _scripts_dir)
sys.path.insert(0, os.path.dirname(_scripts_dir))

from baselines.zac_runner import run_zac_single_benchmarks, run_zac_merge_benchmarks
from baselines.pachinqo_runner import run_pachiqo_single_benchmark
from baselines.powermove_runner import run_powermove_single_benchmarks, run_powermove_merge_benchmarks
from baselines.qmap_runner import run_qmap_single_benchmarks, run_qmap_merge_benchmarks
from baselines.zap_runner import run_zap_single_benchmarks, run_zap_merge_benchmarks
from baselines.multiq_runner import (
    run_multiq_planner_eval,
    run_multiq_bundler_eval,
    run_multiq,
    run_controler_set_multiq,
)
from tools.gen_benchmarks import gen_single_benchmarks
from tools.gen_architectures import generate_scaled_arch
import eval_functions as eval

from eval_functions import plot_planner_eval_fidelity_multiq, plot_planner_eval_utilization_multiq, plot_e2e_results_duration, plot_e2e_results_fidelity, plot_e2e_results_total_runtime, plot_bundler_temporal_util, plot_bundler_space_util, plot_multiq_overhead_vs_set_size, plot_multiq_overhead_vs_circuit_size, plot_multiq_overhead_vs_qpu_size
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.legend as mlegend
import random
from plotting import utils, bar_plot, defaults
import numpy as np
import logging
import yaml
import pandas as pd
import matplotlib.gridspec as gridspec

# Set up logging only for multiq messages
# %(asctime)s so every logger.info(...) call (here and in the baseline
# runner modules) is timestamped -- otherwise a 3-hour run's log looks
# identical whether it's progressing or stuck.
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s", datefmt="%H:%M:%S")
logging.getLogger("qiskit").setLevel(logging.WARNING)
logging.getLogger("fontTools").setLevel(logging.WARNING)
logging.getLogger("matplotlib").setLevel(logging.WARNING)
logging.getLogger("stevedore").setLevel(logging.WARNING)
logging.getLogger("PIL").setLevel(logging.WARNING)

logger = logging.getLogger("multiq.evaluation")


def _progress(msg):
    # Long sweeps (hours) otherwise print nothing per-benchmark -- every
    # progress line gets a wall-clock timestamp so a stalled/hung run is
    # visible from the gap between timestamps, not just silence.
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

# Base configs/architectures in config/multiq and config/zac are read-only
# templates -- every sweep below derives a per-run working copy instead of
# overwriting them in place (overwriting the template was the previous
# behavior, and is why the tracked base configs kept showing up as modified
# in `git status` after a run). Derived files are gitignored scratch, not
# pipeline output.
GENERATED_CONFIG_DIR = os.path.join(os.path.dirname(__file__), "..", "config/multiq/_generated")
GENERATED_ARCH_DIR = os.path.join(os.path.dirname(__file__), "..", "config/zac/_generated")
os.makedirs(GENERATED_CONFIG_DIR, exist_ok=True)
os.makedirs(GENERATED_ARCH_DIR, exist_ok=True)


def _write_generated_config(config, filename):
    path = os.path.join(GENERATED_CONFIG_DIR, filename)
    with open(path, "w") as file:
        yaml.dump(config, file)
    return path


# ----- 1. End-to-End Evaluation -----
def run_end_to_end_evaluation():
    # ----- 1. End-to-End Evaluation -----
    # Running MultiQ and baselines in multiprogramming environment (End-to-End Evaluation)

    multi_benchmark_set = open("data/multi_eval_bench_list.txt").read().splitlines()
    multi_benchmark_set_pachinqo = open("data/multi_eval_bench_list_pachinqo.txt").read().splitlines()

    set_sizes = [4, 6, 8, 10, 12, 14]
    #set_sizes = [8, 12]

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

    # Running baselines (ZAC, Pachinqo, PowerMove, qmap and ZAP) on single benchmarks
    n_pachinqo = len(multi_benchmark_set_pachinqo)
    _progress(f"Baseline sweep (PachinQo): {n_pachinqo} benchmarks")
    for i, bench in enumerate(multi_benchmark_set_pachinqo):
        _progress(f"  [{i + 1}/{n_pachinqo}] PachinQo: {bench}")
        run_pachiqo_single_benchmark(bench, zac_settings_file, pachinqo_results_file)

    n_single = len(multi_benchmark_set)
    _progress(f"Baseline sweep (ZAC/PowerMove/QMAP/ZAP): {n_single} benchmarks")
    for i, bench in enumerate(multi_benchmark_set):
        _progress(f"  [{i + 1}/{n_single}] {bench}")
        run_zac_single_benchmarks(bench, zac_settings_file, zac_results_file)
        run_powermove_single_benchmarks(bench, general_arch_file, powermove_results_file)
        run_qmap_single_benchmarks(bench, general_arch_file, qmap_results_file)
        run_zap_single_benchmarks(bench, general_arch_file, zap_results_file)

    #exit()
    # Selecting random subsets of benchmarks for MultiQ evaluation
    random.seed(42)  # For reproducibility
    multi_benchmark_sets = [random.sample(multi_benchmark_set, size) for size in set_sizes]

    n_multiq_configs = len(multi_benchmark_sets) * 2
    multiq_config_idx = 0
    for benchmark_set in multi_benchmark_sets:
        _progress(f"Running MultiQ with benchmark set of size {len(benchmark_set)}")

        for rows in [1, 2]:
            with open(base_config_file, "r") as file:
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
                    config["perf_weight"] = 0.35
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
            generated_config_file = _write_generated_config(
                config, f"e2e_config_set{len(benchmark_set)}_rows{rows}.yaml"
            )

            multiq_config_idx += 1
            _progress(f"  [{multiq_config_idx}/{n_multiq_configs}] MultiQ, set size {len(benchmark_set)}, {rows} row(s)")

            run_multiq(
                benchmarks=benchmark_set,
                config_file=generated_config_file,
                output_file=multiq_results_file,
            )

    _progress("run_end_to_end_evaluation done")


# ----- 2. MultiQ overhead evaluation -----
# Answers "what does MultiQ's own classical processing (virtual layout
# decision + orchestration) cost, and does it scale with larger circuits and
# larger QPUs?" -- separate from comparing against baseline compilers, since
# MultiQ accepts any NA compiler as its per-tile backend (the "scheduling"
# stage below is that swappable backend, not MultiQ's own logic; kept in the
# breakdown as a labeled reference segment, not folded into the total).
#
# Three independent sweeps, each varying exactly one thing:
#   - vs set size:     fixed default QPU, circuit count 4-14 (mirrors plot 1)
#   - vs circuit size: QPU FIXED at the size needed for the largest group,
#                       circuit count fixed at 6, circuit size 20-200q
#   - vs QPU size:      circuits FIXED at 30q x 6, QPU capacity 180-1200
#
# No baselines are run in any of these -- the reviewer's question is about
# MultiQ's own overhead, not backend/baseline compile speed.

OVERHEAD_ALGORITHMS = ["dj", "ghz", "qft", "bv", "qpeinexact", "graphstate"]


'''
def run_multiq_overhead_vs_set_size():
    # Redundant with run_end_to_end_evaluation: same seed(42), same
    # set_sizes, same perf_weight table -- it re-runs the identical 12 MultiQ
    # configs (6 sizes x 2 rows) just to write them to a separate CSV.
    # run_multiq() already records planning/bundling/scheduling/placement/
    # routing_time on every call, so plot_multiq_overhead_vs_set_size now
    # reads those columns straight out of results/multiq/e2e_results.csv
    # instead. Left here commented in case the e2e sweep's config/benchmark
    # pool ever diverges from this one and a dedicated run is needed again.
    multi_benchmark_set = open("data/multi_eval_bench_list.txt").read().splitlines()
    set_sizes = [4, 6, 8, 10, 12, 14]

    base_config_file = os.path.join(os.path.dirname(__file__), "..", "config/multiq/e2e_config.yaml")
    results_file = os.path.join(os.path.dirname(__file__), "../results/multiq/overhead_by_set_size.csv")

    # Same hand-tuned perf_weight table as run_end_to_end_evaluation, since
    # this sweeps the exact same circuit pool/set sizes/QPU.
    perf_weights = {
        (1, 4): 0.7, (2, 4): 0.92,
        (1, 6): 0.52, (2, 6): 1,
        (1, 8): 0.35, (2, 8): 0.8,
        (1, 10): 0.33, (2, 10): 0.6,
        (1, 12): 0.18, (2, 12): 0.48,
        (1, 14): 0.17, (2, 14): 0.4,
    }

    random.seed(42)
    multi_benchmark_sets = [random.sample(multi_benchmark_set, size) for size in set_sizes]

    for benchmark_set in multi_benchmark_sets:
        size = len(benchmark_set)
        print(f"Running MultiQ overhead eval for set size {size}")

        for rows in [1, 2]:
            with open(base_config_file, "r") as file:
                config = yaml.safe_load(file)
            config["grid_rows"] = rows
            config["selector_algo"] = "fifo"
            config["perf_weight"] = perf_weights[(rows, size)]
            tmp_config_path = os.path.join(os.path.dirname(__file__), f"../config/multiq/_generated/overhead_set_size_config_{size}_rows{rows}.yaml")
            with open(tmp_config_path, "w") as file:
                yaml.dump(config, file)

            run_multiq(
                benchmarks=benchmark_set,
                config_file=tmp_config_path,
                output_file=results_file,
            )
'''


def run_multiq_overhead_vs_circuit_size():
    circuit_sizes = [20, 50, 100]

    # One-time setup: generate the 30 circuits (cached, no-op if they already exist).
    gen_single_benchmarks(circuit_sizes, OVERHEAD_ALGORITHMS)

    base_config_file = os.path.join(os.path.dirname(__file__), "..", "config/multiq/e2e_config.yaml")
    arch_dir = os.path.join(os.path.dirname(__file__), "../config/zac/_generated")

    # QPU fixed for the whole sweep, sized for the largest group (6x200q).
    # All 6 tiles need to land in a single bin for every group -- multiple
    # bins would mean different groups are doing structurally different work
    # (independent smaller compiles vs one genuinely joint compile), which
    # would skew the overhead comparison across the sweep rather than
    # isolating circuit size as the only varying factor.
    #
    # A single large circuit's own tile needs real physical width regardless
    # of aggregate qubit capacity, so a tight ~90-100% utilization target
    # isn't enough on its own. The key lever is perf_weight (== "alpha" in
    # planner.py's tile-width formula: selected_storage_width =
    # ceil(best_storage_width*perf_weight + minimum_storage_width*(1-perf_weight))):
    # pushing it down forces narrow/tall tiles (minimum_storage_width
    # dominates) instead of wide/short ones, letting more circuits fit
    # side-by-side per unit of width. This trades circuit fidelity for
    # compilability (qubits travel further to the entanglement zone in a
    # tall tile) -- an acceptable tradeoff here since this sweep is about
    # compilation overhead at MultiQ's scaling limits, not runtime fidelity.
    #
    # One fixed perf_weight across the whole sweep doesn't work: small
    # circuits forced narrow inside this (200q-sized) QPU hit unrelated zac
    # placer edge cases (assert(0) in intermediate placement, ZeroDivisionError
    # in the SA placer's temperature calibration, or a ValueError) well before
    # reaching whatever value the largest circuits need just to fit at all.
    # Confirmed by direct full-pipeline (mq.set_inputs) testing per size, at
    # both rows=1 and rows=2: the largest perf_weight that still bundles all
    # 6 tiles into exactly 1 bin without crashing, decreasing monotonically
    # as circuit size grows (larger circuits need narrower tiles to fit).
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
            config["selector_algo"] = "fifo"
            config["perf_weight"] = PERF_WEIGHT_BY_CIRCUIT_SIZE[size]
            tmp_config_path = os.path.join(os.path.dirname(__file__), f"../config/multiq/_generated/overhead_circuit_size_config_{size}q_rows{rows}.yaml")
            with open(tmp_config_path, "w") as file:
                yaml.dump(config, file)

            config_idx += 1
            _progress(f"  [{config_idx}/{n_configs}] MultiQ overhead eval for circuit size {size}q with {rows} rows (fixed QPU)")

            run_multiq(
                benchmarks=benchmark_set,
                config_file=tmp_config_path,
                output_file=results_file,
            )

    _progress("run_multiq_overhead_vs_circuit_size done")


def run_multiq_overhead_vs_qpu_size():
    fixed_circuit_size = 30
    qpu_capacities = [180, 300, 500, 1000, 1200]

    gen_single_benchmarks([fixed_circuit_size], OVERHEAD_ALGORITHMS)
    benchmark_set = [f"single/{algo}-{fixed_circuit_size}.qasm" for algo in OVERHEAD_ALGORITHMS]

    base_config_file = os.path.join(os.path.dirname(__file__), "..", "config/multiq/e2e_config.yaml")
    arch_dir = os.path.join(os.path.dirname(__file__), "../config/zac/_generated")

    # target_utilization=1.0 -> capacity is used directly as the target (with
    # the function's own floor-bump rounding up to the next valid grid),
    # rather than padded further -- these values are already the intended
    # QPU sizes, not a "demand" needing utilization headroom.
    # scale_entanglement=False: circuits are small and fixed here (30q), so
    # there's no need for the entanglement zone's extra width, and scaling it
    # down at the smallest capacity (180) shrinks qpu_height below MultiQ's
    # own fixed entanglement_height config constant, which breaks tile
    # geometry entirely (confirmed: assert(0) in zac's Architecture.preprocessing).
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
            config["selector_algo"] = "fifo"
            # A lower perf_weight forces narrower/taller tiles so all 6 fit
            # in one bin at every capacity -- see
            # run_multiq_overhead_vs_circuit_size's comment for the full
            # rationale (this sweep's circuits are fixed/small at 30q, so one
            # uniform value works across the whole range, unlike that
            # sweep). Confirmed via direct full-pipeline (mq.set_inputs)
            # testing: all 5 capacities x 2 rows bundle into exactly 1 bin at
            # perf_weight=0.3 with no crashes; 0.01 (tried first, matching
            # the circuit-size sweep) crashed with the same zac placer edge
            # cases seen there.
            config["perf_weight"] = 0.3
            tmp_config_path = os.path.join(os.path.dirname(__file__), f"../config/multiq/_generated/overhead_qpu_size_config_{capacity}q_rows{rows}.yaml")
            with open(tmp_config_path, "w") as file:
                yaml.dump(config, file)

            config_idx += 1
            _progress(f"  [{config_idx}/{n_configs}] MultiQ overhead eval for QPU capacity {capacity}q (actual {actual_r}x{actual_c}) with {rows} rows")

            run_multiq(
                benchmarks=benchmark_set,
                config_file=tmp_config_path,
                output_file=results_file,
            )

    _progress("run_multiq_overhead_vs_qpu_size done")


# ----- 3. Storage-zone rows sweep (reviewer request) -----
# The reviewer conflated "grid_rows" (the multiprogramming-grid rows already
# swept as [1, 2] in the e2e panels above, i.e. "MultiQ (1 Row)/(2 Row)")
# with "storage zone rows" -- the number of rows inside a single tile's
# storage zone. That value isn't a direct config knob: it's derived in
# planner.py's _compute_tile_layout as
#   storage_rows = (qpu_height - entanglement_height) // grid_rows // storage_atom_spacing
# so with grid_rows fixed at 1 (to keep this axis independent of the
# existing grid-rows sweep), it inverts cleanly to
#   qpu_height = entanglement_height + target_rows * storage_atom_spacing
ROWS_SWEEP_TARGETS = [5, 15, 25, 35]


def run_multiq_rows_sweep():
    multi_benchmark_set = open("data/multi_eval_bench_list.txt").read().splitlines()
    random.seed(42)
    # Identical selection to the existing set_size=4 e2e panel, so the new
    # panel stays directly comparable to panels (a)/(b) on the same figure.
    benchmark_set = random.sample(multi_benchmark_set, 4)

    base_config_file = os.path.join(os.path.dirname(__file__), "..", "config/multiq/e2e_config.yaml")
    entanglement_height = 40
    storage_atom_spacing = 3
    # Starting point: the tuned value for rows=1/set_size=4 in the existing
    # e2e sweep. Not guaranteed to hold across the whole range -- fewer rows
    # forces much wider tiles for the same qubit count, which can hit the
    # same zac placer edge cases documented above
    # run_multiq_overhead_vs_circuit_size. Retune empirically per point if a
    # run crashes or produces a degenerate bundling.
    #
    # rows=5 needed its own override: at perf_weight=0.7 the SA bin packer
    # split the 4-circuit set into 2 bins instead of 1 (tiles too wide to
    # all fit side by side), which would make that point structurally
    # different from the other three (2 circuits/bin vs 4) rather than a
    # clean isolated "fewer rows" comparison. 0.6 (found empirically by
    # trial) forces narrower tiles that still all fit in a single bin.
    perf_weight_by_rows = {5: 0.6}
    default_perf_weight = 0.7

    achieved_rows = []
    for target_rows in ROWS_SWEEP_TARGETS:
        actual_rows = target_rows
        while True:
            qpu_height = entanglement_height + actual_rows * storage_atom_spacing
            with open(base_config_file, "r") as file:
                config = yaml.safe_load(file)
            config["grid_rows"] = 1
            config["qpu_height"] = qpu_height
            config["selector_algo"] = "fifo"
            config["perf_weight"] = perf_weight_by_rows.get(actual_rows, default_perf_weight)
            tmp_config_path = os.path.join(os.path.dirname(__file__), f"../config/multiq/_generated/rows_sweep_config_{actual_rows}rows.yaml")
            with open(tmp_config_path, "w") as file:
                yaml.dump(config, file)

            results_file = os.path.join(os.path.dirname(__file__), f"../results/multiq/rows_sweep_{actual_rows}rows.csv")
            if os.path.isfile(results_file):
                os.remove(results_file)  # run_multiq appends -- start fresh per point

            _progress(f"Running MultiQ rows sweep: target storage rows={target_rows}, actual={actual_rows} (qpu_height={qpu_height})")
            try:
                run_multiq(
                    benchmarks=benchmark_set,
                    config_file=tmp_config_path,
                    output_file=results_file,
                )
                nbins = pd.read_csv(results_file)["nbins"].iloc[0]
                if nbins != 1:
                    _progress(f"rows={actual_rows} bundled into {nbins} bins (expected 1) with perf_weight={config['perf_weight']} -- "
                          f"add a lower override to perf_weight_by_rows for this point to force a single bin")
                achieved_rows.append(actual_rows)
                break
            except Exception as e:
                _progress(f"rows={actual_rows} infeasible ({e}); bumping up and retrying")
                actual_rows += 5

    _progress(f"Rows sweep complete. Achieved row counts: {achieved_rows}")
    return achieved_rows


'''
def plot_e2e_detailed_half():
    # ----- Plot end-to-end evaluation results fidelity and exection time for MultiQ and baselines

    detailed_set_sizes = [8]
    include_pachinqo = False

    zac_results_file = os.path.join(os.path.dirname(__file__), f"../results/zac/e2e_results.csv")

    zac_results_file = os.path.join(os.path.dirname(__file__), f"../results/zac/e2e_results.csv")
    pachinqo_results_file = os.path.join(os.path.dirname(__file__), f"../results/pachinqo/e2e_results.csv")
    multiq_results_file = os.path.join(os.path.dirname(__file__), f"../results/multiq/e2e_results.csv")

    #fig = plt.figure(figsize=(13, 2.5), constrained_layout=True)
    fig = plt.figure(figsize=(7, 3), constrained_layout=True)
    gs = gridspec.GridSpec(1,1, figure=fig)

    axes = []
    for idx in range(len(detailed_set_sizes)):
        axes.append(fig.add_subplot(gs[idx * 1]))
        #axes.append(fig.add_subplot(gs[idx * 2 + 1]))

    print("Plotting fidelity")
    #letters = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"]
    for idx, set in enumerate(detailed_set_sizes):
        print(f"Plotting results for benchmark set of size {set}")
        eval.plot_e2e_results_fidelity(
            ax=axes[idx],
            set_size=set,
            title=f"Fidelity (Set size: {set})",
            multiq_results_file=multiq_results_file,
            zac_results_file=zac_results_file,
            pachinqo_results_file=pachinqo_results_file,
            include_pachinqo=include_pachinqo,
        )

        axes[idx].set_xlabel(None)

    fig.tight_layout(w_pad=0.3, rect=(-0.013, 0.06, 1.005, 1.045))

    if include_pachinqo:
        fig.legend(loc='lower center', bbox_to_anchor=(0.52, 0), ncol=5, fontsize=11, frameon=True, labels=['MultiQ (1 Row)', 'MultiQ (2 Row)', 'ZAC', 'PachinQo'], title_fontsize=11)
    else:
        fig.legend(loc='lower center', bbox_to_anchor=(0.52, 0), ncol=5, fontsize=11, frameon=True, labels=['MultiQ (1 Row)', 'MultiQ (2 Row)', 'ZAC'], title_fontsize=11)

    fig.savefig("results/plots/e2e_plot_detailed.pdf", format="pdf")
'''

def plot_e2e_detailed(rows_sweep_values=ROWS_SWEEP_TARGETS):
    # ----- Plot end-to-end evaluation results fidelity and exection time for MultiQ and baselines
    # Panel (c) is the reviewer-requested fidelity-vs-storage-zone-rows plot;
    # pass the row counts `run_multiq_rows_sweep()` actually produced (its
    # return value) if any point got bumped up from the requested target.

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
        title=f"(a) Fidelity (Set size: {set_size})",
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
        title=f"(b) Execution time (Set size: {set_size})",
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
    rows_handles, rows_labels = rows_ax.get_legend_handles_labels()
    rows_ax.legend(rows_handles, rows_labels, loc='upper left',
                    ncol=1, fontsize=8, frameon=True, title="Benchmark", title_fontsize=8)

    duration_ax.set_ylabel("Execution time (s)", fontsize=11)
    fidelity_ax.set_ylabel("Fidelity", fontsize=11)

    fig.tight_layout(w_pad=-1, rect=(-0.013, 0.06, 1.005, 1.045))

    #ylim(0, 35)
    duration_ax.set_ylim(0, 32)
    duration_yticks = [6, 8, 10, 20, 30, 40]
    duration_ax.set_yticks(duration_yticks)
    duration_ax.set_yticklabels([r'$10^1$' if v == 10 else '' for v in duration_yticks])

    # Bars taller than the y-axis cap get clipped; label the true value to the
    # left of those bars instead of letting them run off the top silently.
    duration_ylim_top = duration_ax.get_ylim()[1]
    for container in duration_ax.containers:
        for bar in container:
            height = bar.get_height()
            if height > duration_ylim_top:
                duration_ax.text(bar.get_x(), duration_ylim_top * 0.92, f'{height:.0f}',
                                  ha='right', va='top', fontsize=10, rotation=90)

    legend_labels = ['MultiQ (1 Row)', 'MultiQ (2 Row)', 'ZAC']
    if include_powermove:
        legend_labels.append('PowerMove')
    if include_qmap:
        legend_labels.append('QMAP')
    if include_zap:
        legend_labels.append('ZAP')
    if include_pachinqo:
        legend_labels.append('PachinQo')
    fig.legend(loc='lower center', bbox_to_anchor=(0.5, 0.035), ncol=len(legend_labels), fontsize=11, frameon=True, labels=legend_labels, title_fontsize=11)

    fig.savefig("results/plots/e2e_plot_detailed.pdf", format="pdf")

'''
def plot_e2e_detailed_full():
    # ----- Plot end-to-end evaluation results fidelity and exection time for MultiQ and baselines

    #detailed_set_sizes = [4, 6, 8, 10, 12, 14]
    detailed_set_sizes = [4, 8, 12]

    zac_results_file = os.path.join(os.path.dirname(__file__), f"../results/zac/e2e_results.csv")

    zac_results_file = os.path.join(os.path.dirname(__file__), f"../results/zac/e2e_results.csv")
    pachinqo_results_file = os.path.join(os.path.dirname(__file__), f"../results/pachinqo/e2e_results.csv")
    multiq_results_file = os.path.join(os.path.dirname(__file__), f"../results/multiq/e2e_results.csv")

    fig = plt.figure(figsize=(15, 2.3 * len(detailed_set_sizes)), constrained_layout=True)

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
            title=f"({letters[idx*2]}) Fidelity (Set size: {set})",
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
            title=f"({letters[idx*2+1]}) Execution time (Set size: {set})",
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
'''


def plot_e2e_total_runtime(include_powermove=True, include_qmap=True, include_zap=True):
    # ----- Plot end-to-end evaluation results total runtime for MultiQ and baselines

    fig, [ax0, ax1] = utils.gen_subplots(1, 2, figsize=(13, 3), height_ratios=[0.8, 1])

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
        include_powermove=include_powermove,
        include_qmap=include_qmap,
        include_zap=include_zap,
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

    ax0.get_legend().set(bbox_to_anchor=(0.35, 0.99), loc="upper left")
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

    fig.legend(
        handles=custom_handles,
        loc="upper left",
        bbox_to_anchor=(0, 0.99),
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


'''
def plot_e2e_total_runtime_complete():
    # ----- Plot end-to-end evaluation results total runtime for MultiQ and baselines

    set_sizes = [4, 6, 8, 10, 12, 14]

    fig, (ax0) = plt.subplots(1, 1, figsize=(13, 2.5), constrained_layout=True)

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
        bbox_to_anchor=(0.33, 0.905),
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
'''

'''
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
'''

def plot_planner():
    # ----- Plotting Planner and Bundler Results ----
    fig, ((ax0, ax1)) = plt.subplots(1,2, figsize=(13, 2.5), constrained_layout=True)

    eval.plot_planner_eval_fidelity_multiq(ax=ax0, title="(a) MultiQ Planner (Decoherence error)", complete=False)
    eval.plot_planner_eval_utilization_multiq(ax=ax1, title="(b) MultiQ Planner (Utilization)")

    # fig.legend(loc='lower center', bbox_to_anchor=(0.52, 0), ncol=5, fontsize=12, frameon=True, labels=['0.2', '0.4', '0.6', '0.8', '1.0'], title='Performance weight', title_fontsize=10)

    # change xlabel position
    #ax2.get_xaxis().set_label_coords(0.4, -0.2)
    #ax3.get_xaxis().set_label_coords(0.6, -0.2)

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

    #legends = [f"SA - {weight}" for weight in temporal_util_weights]
    #legends.insert(0, "FIFO")  # Ensure 'fifo' is first
    #fig.legend(
    #    loc="lower center",
    #    bbox_to_anchor=(0.52, -0.002),
    #    ncol=7,
    #    fontsize=12,
    #    frameon=True,
    #    labels=legends,
    #    title="Selection algorithm - Temporal utilization weight",
    #    title_fontsize=11,
    #)

    fig.tight_layout(rect=(-0.01, 0.085, 1.005, 1.04), h_pad=2.5, w_pad=0.3)

    """
    fig.savefig('results/plots/bundler_plots.pdf', format='pdf')

    fig.tight_layout(rect=(0,0.08,1,1), w_pad=-0.4)

    fig.savefig('results/plots/planner_bundler_plots.pdf', format='pdf')

    fig.tight_layout(rect=(0,0.08,1,1), w_pad=-0.4)

    fig.legend(loc='lower center', bbox_to_anchor=(0.52, 0), ncol=5, fontsize=12, frameon=True, labels=['0.2', '0.4', '0.6', '0.8', '1.0'], title='Performance weight', title_fontsize=11)
    """

    fig.savefig("results/plots/planner_plot.pdf", format="pdf")

def plot_bundler():
    # ----- Plotting Planner and Bundler Results ----
    fig, ((ax0, ax1)) = plt.subplots(1,2, figsize=(13, 2.5), constrained_layout=True)

    # fig.legend(loc='lower center', bbox_to_anchor=(0.52, 0), ncol=5, fontsize=12, frameon=True, labels=['0.2', '0.4', '0.6', '0.8', '1.0'], title='Performance weight', title_fontsize=10)

    eval.plot_bundler_space_util(ax=ax0, title="(a) Bundler (Spatial utilization)")
    eval.plot_bundler_temporal_util(ax=ax1, title="(b) Bundler (Temporal utilization)")

    # change xlabel position
    ax0.get_xaxis().set_label_coords(0.4, -0.2)
    ax1.get_xaxis().set_label_coords(0.6, -0.2)

    temporal_util_weights = [0.2, 0.4, 0.6, 0.8][::-1]

    legends = [f"SA - {weight}" for weight in temporal_util_weights]
    legends.insert(0, "FIFO")  # Ensure 'fifo' is first
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

    """
    fig.savefig('results/plots/bundler_plots.pdf', format='pdf')

    fig.tight_layout(rect=(0,0.08,1,1), w_pad=-0.4)

    fig.savefig('results/plots/planner_bundler_plots.pdf', format='pdf')

    fig.tight_layout(rect=(0,0.08,1,1), w_pad=-0.4)

    fig.legend(loc='lower center', bbox_to_anchor=(0.52, 0), ncol=5, fontsize=12, frameon=True, labels=['0.2', '0.4', '0.6', '0.8', '1.0'], title='Performance weight', title_fontsize=11)
    """

    fig.savefig("results/plots/bundler_plot.pdf", format="pdf")

def run_planner_eval(set_sizes=None, perf_weights=None, config_file=None, results_file=None):
    multiq_config_file = os.path.join(os.path.dirname(__file__), "../config/multiq/planner_bundler_config.yaml")

    run_multiq_planner_eval(multiq_config_file)


def run_bundler_eval(set_sizes=None, perf_weights=None, config_file=None, results_file=None):
    # 2.2 Bundler Evaluation
    base_config_file = os.path.join(os.path.dirname(__file__), "../config/multiq/e2e_config.yaml")

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
    with open(base_config_file, "r") as file:
        config = yaml.safe_load(file)
        config["grid_rows"] = 1
        # config['grid_cols'] = len(benchmark_set) // rows
        config["perf_weight"] = 0.8
        config["selection_algorithm"] = "fifo"

    fifo_config_file = _write_generated_config(config, "bundler_config_fifo.yaml")

    # ----- Running MultiQ with fifo selection algorithm

    multiq_results_file = os.path.join(os.path.dirname(__file__), f"../results/multiq/bundler_results.csv")

    n_fifo = len(benchmark_sets)
    for i, benchmark_set in enumerate(benchmark_sets):
        bench = "-".join([os.path.basename(b).split(".")[0] for b in benchmark_set])
        logger.info(f"[{i + 1}/{n_fifo}] Running MultiQ with FIFO selection algorithm on benchmark set: {bench}")
        run_multiq(
            benchmarks=benchmark_set,
            config_file=fifo_config_file,
            output_file=multiq_results_file,
        )

    temporal_util_weights = [0, 0.2, 0.4, 0.6, 0.8, 1][::-1]  # Performance selection weights for bundler evaluation
    n_sa_configs = len(temporal_util_weights) * len(benchmark_sets)
    sa_config_idx = 0

    for weight in temporal_util_weights:
        # Setting up config for fifo selection evaluation
        with open(base_config_file, "r") as file:
            config = yaml.safe_load(file)
            config["grid_rows"] = 1
            # config['grid_cols'] = len(benchmark_set) // rows
            config["perf_weight"] = 0.8
            config["selection_algorithm"] = "sa"
            config["perf_weight_selector"] = weight

        sa_config_file = _write_generated_config(config, f"bundler_config_sa_{weight}.yaml")

        for benchmark_set in benchmark_sets:
            bench = "-".join([os.path.basename(b).split(".")[0] for b in benchmark_set])
            sa_config_idx += 1
            logger.info(
                f"[{sa_config_idx}/{n_sa_configs}] Running MultiQ with bundler evaluation on benchmark: {bench} with temporal utilization weight: {weight}"
            )
            run_multiq(
                benchmarks=benchmark_set,
                config_file=sa_config_file,
                output_file=multiq_results_file,
            )

    _progress("run_bundler_eval done")

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

    general_arch_file = os.path.join(os.path.dirname(__file__), "../config/zac/general_arch.json")
    powermove_results_file = os.path.join(os.path.dirname(__file__), "../results/powermove/controller_results.csv")
    qmap_results_file = os.path.join(os.path.dirname(__file__), "../results/qmap/controller_results.csv")
    zap_results_file = os.path.join(os.path.dirname(__file__), "../results/zap/controller_results.csv")

    set_sizes = [4, 6, 8, 10, 12, 14]

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

    n_sets = len(multi_benchmark_sets)
    for i, benchmark_set in enumerate(multi_benchmark_sets):
        _progress(f"[{i + 1}/{n_sets}] Controller baselines (ZAC/PowerMove/QMAP/ZAP) on merged set of size {len(benchmark_set)}")
        run_zac_merge_benchmarks(benchmark_set, zac_settings_file, zac_results_file)
        run_powermove_merge_benchmarks(benchmark_set, general_arch_file, powermove_results_file)
        run_qmap_merge_benchmarks(benchmark_set, general_arch_file, qmap_results_file)
        run_zap_merge_benchmarks(benchmark_set, general_arch_file, zap_results_file)
        # run_pachiqo_single_benchmarks(benchmark_set, pachinqo_settings_file, output_file="results/pachinqo_results.csv")

    _progress("run_controller_eval done")


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


'''
def plot_controller_eval_half(include_powermove=True, include_qmap=True, include_zap=True):
    fig, [ax0] = utils.gen_subplots(1, 1, figsize=(7, 3))

    #eval.plot_controler_execution_time(ax0, title="(a) Execution time")
    eval.plot_controler_decoherence_error(
        ax0,
        title="Decoherence error",
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
        bbox_to_anchor=(0.52, -0.01),
        ncol=len(legend_labels),
        fontsize=11,
        frameon=True,
        labels=legend_labels,
    )

    fig.savefig("results/plots/controller_plot_half.pdf", format="pdf")


def _finish_overhead_plot(fig, ax, output_path):
    # stacked_grouped_barplot's ax.legend(loc=<tuple>) doesn't reserve figure
    # width for a 5-category legend row (the "compilation (backend)" label is
    # long enough to overflow a 7-inch figure and gets silently clipped).
    # Pull it out to a figure-level anchor instead, which sizes correctly.
    #
    # stacked_grouped_barplot now attaches two legends to the axes (stage
    # colors, and row-config hatches) -- only the most recent one is
    # reachable via ax.get_legend(), so gather both via findobj instead.
    legends = [c for c in ax.get_children() if isinstance(c, mlegend.Legend)]
    handles, labels = [], []
    for legend in legends:
        handles.extend(legend.legend_handles)
        labels.extend([t.get_text() for t in legend.get_texts()])
        legend.remove()
    fig.subplots_adjust(bottom=0.34)
    fig.legend(handles, labels, loc="lower center", ncol=3, bbox_to_anchor=(0.5, 0.01))

    fig.savefig(output_path, format="pdf")


def plot_e2e_multiq_overhead_vs_set_size():
    # ----- Plot MultiQ's own overhead breakdown vs circuit-set size

    fig, ax = plt.subplots(1, 1, figsize=(7, 4.5))

    set_sizes = [4, 6, 8, 10, 12, 14]

    eval.plot_multiq_overhead_vs_set_size(
        ax=ax,
        title="MultiQ overhead vs set size",
        set_sizes=set_sizes,
    )

    _finish_overhead_plot(fig, ax, "results/plots/multiq_overhead_vs_set_size.pdf")


def plot_e2e_multiq_overhead_vs_circuit_size():
    # ----- Plot MultiQ's own overhead breakdown vs circuit size (fixed QPU)

    fig, ax = plt.subplots(1, 1, figsize=(7, 4.5))

    circuit_sizes = [20, 50, 100]

    eval.plot_multiq_overhead_vs_circuit_size(
        ax=ax,
        title="MultiQ overhead vs circuit size (fixed QPU)",
        circuit_sizes=circuit_sizes,
    )

    _finish_overhead_plot(fig, ax, "results/plots/multiq_overhead_vs_circuit_size.pdf")


def plot_e2e_multiq_overhead_vs_qpu_size():
    # ----- Plot MultiQ's own overhead breakdown vs QPU size (fixed circuits)

    fig, ax = plt.subplots(1, 1, figsize=(7, 4.5))

    qpu_capacities = [180, 300, 500, 1000, 1200]

    eval.plot_multiq_overhead_vs_qpu_size(
        ax=ax,
        title="MultiQ overhead vs QPU size (6x30q circuits, fixed)",
        qpu_capacities=qpu_capacities,
    )

    _finish_overhead_plot(fig, ax, "results/plots/multiq_overhead_vs_qpu_size.pdf")
'''


def plot_e2e_multiq_overhead_combined():
    # ----- All three MultiQ overhead-breakdown plots side by side in one figure

    fig, axes = plt.subplots(1, 3, figsize=(18, 4.5))

    eval.plot_multiq_overhead_vs_set_size(
        ax=axes[0],
        title="vs set size",
        set_sizes=[4, 6, 8, 10, 12, 14],
        # Reuses "e2e"'s output instead of a dedicated overhead_by_set_size.csv
        # sweep -- run_multiq() already records the same timing columns on
        # every call, and the e2e sweep covers the identical 6 sizes x 2 rows
        # configs (same seed, same perf_weight table). See
        # run_multiq_overhead_vs_set_size's comment for the full rationale.
        results_file="results/multiq/e2e_results.csv",
    )
    eval.plot_multiq_overhead_vs_circuit_size(
        ax=axes[1],
        title="vs circuit size (fixed QPU)",
        circuit_sizes=[20, 50, 100],
    )
    eval.plot_multiq_overhead_vs_qpu_size(
        ax=axes[2],
        title="vs QPU size (6x30q, fixed)",
        qpu_capacities=[180, 300, 500, 1000, 1200],
    )

    fig.suptitle("MultiQ overhead breakdown", fontweight="bold")

    # Each subplot's stacked_grouped_barplot call added its own pair of
    # on-axis legends (stage colors + row-config hatches, same categories
    # every time) -- keep one shared pair instead of three identical copies,
    # using the same figure-level-anchor fix as _finish_overhead_plot (see
    # that function's comment for why it's needed, and for why both legends
    # must be gathered via findobj rather than ax.get_legend()).
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

    fig.subplots_adjust(bottom=0.32)
    fig.legend(handles, labels, loc="lower center", ncol=5, bbox_to_anchor=(0.5, 0.01))

    fig.savefig("results/plots/multiq_overhead_combined.pdf", format="pdf")


@dataclass
class Experiment:
    name: str
    description: str
    data_fn: callable = None
    plot_fn: callable = None


# Order matters for --all: rows_sweep must run before e2e, since
# plot_e2e_detailed's panel (c) reads rows_sweep's CSV output.
EXPERIMENTS = [
    Experiment(
        "rows_sweep",
        "MultiQ fidelity vs. storage-zone rows (reviewer request; feeds e2e panel c)",
        data_fn=run_multiq_rows_sweep,
    ),
    Experiment(
        "e2e",
        "End-to-end MultiQ vs. baselines: fidelity/duration/rows-sweep (main paper figure)",
        data_fn=run_end_to_end_evaluation,
        plot_fn=plot_e2e_detailed,
    ),
    Experiment("e2e_total_runtime", "e2e total runtime (broken y-axis)", plot_fn=plot_e2e_total_runtime),
    # Data-only entries below: no plot_fn since their own individual plot
    # functions are commented out for now, but their data still feeds
    # "overhead_combined" below. overhead_set_size has no entry here anymore
    # -- it's redundant with "e2e"'s data (see run_multiq_overhead_vs_set_size's
    # comment); plot_e2e_multiq_overhead_combined now reads e2e_results.csv
    # for that panel instead.
    Experiment(
        "overhead_circuit_size",
        "MultiQ's own compilation overhead vs. circuit size (fixed QPU) (data only)",
        data_fn=run_multiq_overhead_vs_circuit_size,
    ),
    Experiment(
        "overhead_qpu_size",
        "MultiQ's own compilation overhead vs. QPU size (fixed circuits) (data only)",
        data_fn=run_multiq_overhead_vs_qpu_size,
    ),
    Experiment(
        "overhead_combined",
        "All three overhead sweeps side by side (needs 'e2e' and the two overhead_* experiments' data)",
        plot_fn=plot_e2e_multiq_overhead_combined,
    ),
    Experiment("planner", "MultiQ planner evaluation", data_fn=run_planner_eval, plot_fn=plot_planner),
    Experiment("bundler", "MultiQ bundler evaluation", data_fn=run_bundler_eval, plot_fn=plot_bundler),
    Experiment(
        "controller", "Controller evaluation vs. baselines", data_fn=run_controller_eval, plot_fn=plot_controller_eval
    ),
]


def _parse_args():
    parser = argparse.ArgumentParser(
        description="Regenerate MultiQ's main evaluation figures (results/plots/*.pdf)."
    )
    parser.add_argument("--list", action="store_true", help="List available experiments and exit.")
    parser.add_argument("--all", action="store_true", help="Run every experiment (default behavior; explicit alias).")
    parser.add_argument(
        "--only", type=str, default=None, help="Comma-separated experiment names to run (default: all)."
    )
    parser.add_argument("--data-only", action="store_true", help="Only run data collection, skip plotting.")
    parser.add_argument(
        "--plots-only", action="store_true", help="Only (re)generate plots from existing results, skip data collection."
    )
    return parser.parse_args()


def main():
    args = _parse_args()

    if args.list:
        for exp in EXPERIMENTS:
            print(f"{exp.name:28s} {exp.description}")
        return

    if args.data_only and args.plots_only:
        raise SystemExit("--data-only and --plots-only are mutually exclusive")
    if args.all and args.only:
        raise SystemExit("--all and --only are mutually exclusive")

    selected_names = [n.strip() for n in args.only.split(",")] if args.only else None
    if selected_names:
        unknown = set(selected_names) - {exp.name for exp in EXPERIMENTS}
        if unknown:
            raise SystemExit(f"Unknown experiment(s): {', '.join(sorted(unknown))}. Use --list to see available names.")

    run_start = time.time()
    for exp in EXPERIMENTS:
        if selected_names is not None and exp.name not in selected_names:
            continue
        if exp.data_fn and not args.plots_only:
            _progress(f"=== [{exp.name}] collecting data ===")
            stage_start = time.time()
            exp.data_fn()
            _progress(f"=== [{exp.name}] data done in {time.time() - stage_start:.1f}s (total elapsed {time.time() - run_start:.1f}s) ===")
        if exp.plot_fn and not args.data_only:
            _progress(f"=== [{exp.name}] plotting ===")
            stage_start = time.time()
            exp.plot_fn()
            _progress(f"=== [{exp.name}] plot done in {time.time() - stage_start:.1f}s (total elapsed {time.time() - run_start:.1f}s) ===")

    _progress(f"All selected experiments done in {time.time() - run_start:.1f}s")


if __name__ == "__main__":
    main()
