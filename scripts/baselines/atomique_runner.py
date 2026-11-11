import json
import os
import subprocess
import tempfile

import pandas as pd
from qiskit import QuantumCircuit

# FPQAC needs an old Qiskit release, so it runs as a subprocess in its own venv.
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
ATOMIQUE_VENV_PYTHON = os.path.join(_REPO_ROOT, "compilers/atomique/.venv/bin/python")

ATOMIQUE_TIMEOUT = 30 * 60  # seconds


def _parse_benchmark_type(benchmark_file: str) -> str:
    """Strip a trailing "-<size>" or "_n<size>" from the file name to get the benchmark type."""
    name = os.path.basename(benchmark_file).rsplit(".", 1)[0]
    for sep in ("_n", "-"):
        bench_type, found, suffix = name.rpartition(sep)
        if found and suffix.isdigit():
            return bench_type
    raise ValueError(
        f"Expected '<type>-<nqubits>.qasm' or '<type>_n<nqubits>.qasm' naming, got: {benchmark_file}"
    )


def _compile_one(benchmark_path: str, bench_type: str, nqubits: int, timeout: int) -> dict:
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        output_path = tmp.name

    try:
        subprocess.run(
            [
                ATOMIQUE_VENV_PYTHON,
                "-m",
                "compilers.atomique.driver",
                "--qasm",
                os.path.abspath(benchmark_path),
                "--type",
                bench_type,
                "--nqubits",
                str(nqubits),
                "--output",
                output_path,
            ],
            cwd=_REPO_ROOT,
            timeout=timeout,
            check=True,
            capture_output=True,
            text=True,
        )
        with open(output_path) as f:
            return json.load(f)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"Atomique (FPQAC) compile failed for {benchmark_path}:\n{e.stderr}"
        ) from e
    except subprocess.TimeoutExpired as e:
        raise TimeoutError(
            f"Atomique (FPQAC) compile timed out after {timeout}s for {benchmark_path}"
        ) from e
    finally:
        if os.path.isfile(output_path):
            os.remove(output_path)


def run_atomique_single_benchmarks(benchmark_file: str, output_file: str, timeout: int = ATOMIQUE_TIMEOUT):
    """Compile a single QASM circuit with the FPQAC (Atomique) compiler."""
    bench_type = _parse_benchmark_type(benchmark_file)
    filename = os.path.join("data/benchmarks", benchmark_file)


    circuit = QuantumCircuit.from_qasm_file(filename)
    nqubits = circuit.num_qubits

    metrics = _compile_one(filename, bench_type, nqubits, timeout)

    data = pd.DataFrame(columns=[
        "benchmark",
        "nqubits",
        "total_fidelity",
        "execution_time",
        "compilation_time",
        "n_1q_gate",
        "n_2q_gate",
    ])

    benchmark = os.path.basename(benchmark_file)
    data.loc[len(data)] = [
        benchmark.split(".")[0],
        metrics["nqubits"],
        metrics["total_fidelity"],
        metrics["execution_time"],
        metrics["compilation_time"],
        metrics["n_1q_gate"],
        metrics["n_2q_gate"],
    ]

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    if not os.path.isfile(output_file):
        data.to_csv(output_file, index=False)
    else:
        data.to_csv(output_file, mode="a", header=False, index=False)
