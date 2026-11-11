"""Data collection and plot for the introduction figure (Figure 1)."""
import json
import os

import numpy as np
import pandas as pd

from baselines.atomique_runner import run_atomique_single_benchmarks, ATOMIQUE_TIMEOUT
from baselines.zac_runner import run_zac
from framework.grid import Grid
from plotting import utils
from tools.gen_benchmarks import gen_single_benchmarks
import eval_functions
from status import step, warn

BENCH_TYPES = ["ghz", "wstate", "dj"]
SIZES = [25, 50, 100, 150, 200, 250]
RESULTS_DIR = "results/preeval"
ZAC_SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "..", "config/zac/preeval_general.json")

PACHINQO_ZONES = [
    {"type": "StorageZone", "bottom_left_x": 90, "bottom_left_y": 0, "width": 190, "height": 50},
    {"type": "EntanglementZone", "bottom_left_x": 90, "bottom_left_y": 60, "width": 190, "height": 130, "col_size": 4},
    {"type": "ReadoutZone", "bottom_left_x": 0, "bottom_left_y": 60, "width": 80, "height": 130},
    {"type": "ReadoutZone", "bottom_left_x": 290, "bottom_left_y": 60, "width": 80, "height": 130},
]


def _benchmark_path(bench_type, size):
    return f"single/{bench_type}-{size}.qasm"


def _runs():
    runs = [(size, bench_type) for size in SIZES for bench_type in BENCH_TYPES]
    return [(i + 1, len(runs), size, bench_type) for i, (size, bench_type) in enumerate(runs)]


def run_zac_introduction():
    rows = []
    for i, n, size, bench_type in _runs():
        name = f"{bench_type}-{size}"
        step("ZAC", i, n, name)
        run_zac([_benchmark_path(bench_type, size)], ZAC_SETTINGS_FILE)
        fid = json.load(open(f"results/zac/fidelity/{name}.json"))
        rows.append({
            "benchmark": bench_type,
            "nqubits": size,
            "total_fidelity": fid["cir_fidelity"],
            "total_coherence_fidelity": fid["cir_fidelity_coherence"],
            "execution_time": fid["cir_duration"],
        })
    pd.DataFrame(rows).to_csv(f"{RESULTS_DIR}/zac_preeval.csv", index=False)


def _pachinqo_fidelity(returned_values, cir_qubits):
    # Hardware parameters of the 250-atom setup used in Figure 1.
    layers, total_move_distance, nsequential_transfers = returned_values[0], returned_values[1], returned_values[2]
    total_trap_changes = nsequential_transfers * cir_qubits

    gate_1q_fidelity, gate_2q_fidelity = 0.999, 0.995
    gate_1q_time, gate_2q_time = 0.5, 0.2  # us
    decoherence_T2 = 1500000  # us
    transfer_time, transfer_fid = 20, 0.999  # us
    move_speed = 0.55  # um/us

    total_transfer_time = transfer_time * nsequential_transfers
    total_idling_time = total_transfer_time + total_move_distance / move_speed
    total_u3_gates = sum(len(layer[2]) for layer in layers)
    total_cz_gates = sum(len(layer[0]) for layer in layers)

    total_fidelity = (
        gate_1q_fidelity**total_u3_gates
        * gate_2q_fidelity**total_cz_gates
        * transfer_fid**total_trap_changes
        * np.exp(-total_idling_time / decoherence_T2)
    )
    total_execution_time = total_idling_time + gate_1q_time * total_u3_gates + gate_2q_time * total_cz_gates
    return total_fidelity, total_execution_time


def run_pachinqo_introduction():
    from baselines.pachinqo_runner import transpile_single_benchmark

    rows = []
    for i, n, size, bench_type in _runs():
        bench_file = _benchmark_path(bench_type, size)
        step("PachinQo", i, n, f"{bench_type}-{size}")
        try:
            grid = Grid(PACHINQO_ZONES, 0, transpile_single_benchmark(bench_file), num_atoms=250)
            total_fidelity, execution_time = _pachinqo_fidelity(grid.return_vals(), size)
            rows.append({"benchmark": bench_type, "nqubits": size,
                         "total_fidelity": total_fidelity, "execution_time": execution_time})
        except Exception as e:
            warn("PachinQo", f"{bench_type}-{size} failed ({e}), skipping")
    pd.DataFrame(rows).to_csv(f"{RESULTS_DIR}/pachinqo_preeval.csv", index=False)


def run_atomique_introduction():
    output_file = f"{RESULTS_DIR}/atomique_preeval.csv"
    if os.path.isfile(output_file):
        os.remove(output_file)
    for i, n, size, bench_type in _runs():
        step("Atomique", i, n, f"{bench_type}-{size}")
        try:
            run_atomique_single_benchmarks(_benchmark_path(bench_type, size), output_file, timeout=ATOMIQUE_TIMEOUT)
        except (RuntimeError, TimeoutError) as e:
            warn("Atomique", f"{bench_type}-{size} failed ({e}), skipping")


def run_introduction():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    gen_single_benchmarks(SIZES, BENCH_TYPES, regen=False)
    run_zac_introduction()
    run_pachinqo_introduction()
    run_atomique_introduction()


def plot_introduction():
    fig, [ax0, ax1] = utils.gen_subplots(1, 2, figsize=(6, 4.5), height_ratios=[0.9025, 0.95])

    eval_functions.plot_fidelity_vs_circuit_size_zac_pachinqo_atomique(ax0, title="(a) Fidelity vs Circuit size")
    eval_functions.plot_execution_time_vs_circuit_size_zac_pachinqo_atomique(ax1, title="(b) Execution time vs Circuit size")

    ax0.tick_params(axis="x", bottom=False, labelbottom=False)
    ax0.set_xlabel(None)

    fig.tight_layout(rect=(-0.02, 0.035, 1.03, 1.02), h_pad=0.2)
    fig.legend(loc="lower center", bbox_to_anchor=(0.52, -0.01), ncol=4, fontsize=12, frameon=True,
               labels=["ZAC", "PachinQo", "Atomique", "Average"])

    os.makedirs("results/plots", exist_ok=True)
    fig.savefig("results/plots/introduction_plots.pdf", format="pdf")
