"""Runs a single benchmark through the FPQAC ("Atomique") compiler and dumps
its fidelity/timing report as JSON.

This file is MultiQ's own glue code, not part of the upstream FPQA-C
artifact-evaluation repository copied into this directory (benchmark_set.py,
hyperparams.py, compilers/, utils.py) -- none of that upstream code is
modified. It exists because that code targets Qiskit 0.38 and is run here in
its own isolated venv (compilers/atomique/.venv, see requirements-runner.txt)
rather than MultiQ's own Qiskit 2.x environment.

Must be run as a module (not a bare script!) with the repo root as the
working directory, e.g. from scripts/baselines/atomique_runner.py:
    compilers/atomique/.venv/bin/python -m compilers.atomique.driver \\
        --qasm <path> --type <name> --nqubits <n> --output <json>

Running it as `python driver.py` instead would make Python auto-prepend
compilers/atomique itself to sys.path, which collides with the identically
named compilers/atomique/compilers/ subpackage and breaks the upstream
code's own "from compilers.atomique.X import Y" absolute imports.
"""
import argparse
import json
import os
import shutil

from compilers.atomique.benchmarks.benchmark_set import AlgorithmBenchmark
from compilers.atomique.hyperparams import HyperParamSets
from compilers.atomique.compilers.FPQAC.fpqac_generic_compiler import FPQACGenericCompiler


class AttrDict(dict):
    """Minimal torchpack.utils.config.Config stand-in: attribute access over
    a nested dict, plus the .dict() upstream hyperparams.py relies on. Avoids
    pulling in torchpack (and its torch dependency) for the handful of
    dict-like operations the upstream code actually needs."""

    def __getattr__(self, key):
        try:
            value = self[key]
        except KeyError as exc:
            raise AttributeError(key) from exc
        return AttrDict(value) if isinstance(value, dict) else value

    def __setattr__(self, key, value):
        self[key] = value

    def dict(self):
        return {k: (v.dict() if isinstance(v, AttrDict) else v) for k, v in self.items()}


def build_configs(n_rows, n_cols):
    # Mirrors the upstream example config (configs/example, and Weaver's
    # atomique_config.yml): fpqac_generic compiler, default1 hyperparameter
    # base set, no parameter sweep. n_rows/n_cols scale the atom array
    # capacity to fit the benchmark's qubit count -- the example config's
    # own default ([10, 10, 10], i.e. 3 arrays of 100 atoms) is sized for
    # their own example circuits, not MultiQ's up-to-250-qubit ones.
    return AttrDict({
        "compiler": AttrDict({"name": "fpqac_generic", "print_log": False, "results_path": "results"}),
        "backend_params": AttrDict({
            "base_set": "default1",
            "retranspile_changes": AttrDict({}),
            "nonretranspile_changes": AttrDict({}),
            "backer_penalty": [0],
        }),
        "_n_rows": n_rows,
        "_n_cols": n_cols,
    })


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--qasm", required=True, help="Path to the input QASM file")
    parser.add_argument("--type", required=True, help="Benchmark name, e.g. 'bv'")
    parser.add_argument("--nqubits", required=True, type=int)
    parser.add_argument("--output", required=True, help="Path to write the JSON report to")
    parser.add_argument("--n-rows", type=int, default=None, help="Atom array rows (default: fit nqubits)")
    parser.add_argument("--n-cols", type=int, default=None, help="Atom array cols (default: fit nqubits)")
    args = parser.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    algo_dir = os.path.join(here, "benchmarks", "algorithm")
    os.makedirs(algo_dir, exist_ok=True)
    staged_path = os.path.join(algo_dir, f"{args.type}_n{args.nqubits}.qasm")
    shutil.copyfile(args.qasm, staged_path)

    # 3 arrays (n_aods=2 -> 2 AOD arrays + 1 SLM array by default1), each
    # square enough to hold every qubit -- see build_configs() note above.
    side = args.n_rows or args.n_cols or max(10, int(args.nqubits ** 0.5) + 1)
    n_rows = args.n_rows or side
    n_cols = args.n_cols or side

    cwd = os.getcwd()
    os.chdir(here)
    try:
        configs = build_configs(n_rows, n_cols)
        hyperparam_sets = HyperParamSets(configs)
        for hp in hyperparam_sets.all_sets:
            hp.n_rows = hp.n_rows * 0 + n_rows
            hp.n_cols = hp.n_cols * 0 + n_cols
            hp.n_atoms_per_array = hp.n_rows * hp.n_cols
            # Per-layer arrays, not scalars -- mirrors get_default1_params's
            # own "self.fpqac_generic_n_rows_cmap = self.n_rows" (it discards
            # the scalar default from its own signature).
            hp.fpqac_generic_n_rows_cmap = hp.n_rows
            hp.fpqac_generic_n_cols_cmap = hp.n_cols

        benchmark = AlgorithmBenchmark(args.type, args.nqubits)

        class _BenchmarkSets:
            all_benchmarks = [benchmark]

        compiler = FPQACGenericCompiler(configs)
        results = compiler.run(benchmark_sets=_BenchmarkSets(), hyperparam_sets=hyperparam_sets)
    finally:
        os.chdir(cwd)
        os.remove(staged_path)

    report = results[0]
    out = {
        "nqubits": args.nqubits,
        "total_fidelity": report["fidelity"]["total_fidelity"],
        "execution_time": report["time"]["total_time"],
        "compilation_time": report["circ_stats"]["compilation_time"],
        "n_1q_gate": report["circ_stats"]["n_1q_gate"],
        "n_2q_gate": report["circ_stats"]["n_2q_gate"],
    }
    with open(args.output, "w") as f:
        json.dump(out, f)


if __name__ == "__main__":
    main()
