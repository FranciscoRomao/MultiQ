import os
#import qiskit
#import sys
import re

valid_benchmark_suites = ["MQTBench", "QASMBench", "Supermarq", "QOSLib"]

def collect_files_in_directory(directory, nqbits: tuple[int, int]):
    files = []

    for filename in os.listdir(directory):
        if filename.endswith(".qasm") or filename.endswith(".qasm3"):
            match = re.search(r'n(\d+)', filename)
            if match:
                qubits = int(match.group(1))
                if qubits >= nqbits[0] and qubits <= nqbits[1]:
                    files.append(os.path.join(directory, filename))

    return files

def collect_files(base_dir, level1, level2, nqbits: tuple[int, int], additional_levels: list[str] = []):
    files = []
    level1_path = os.path.join(base_dir, level1)

    if os.path.exists(os.path.join(level1_path, level2)):
        level2_path = os.path.join(level1_path, level2)
    else:
        return []

    if len(additional_levels) > 0:
        level2_path = os.path.join(level2_path, *additional_levels)

    if os.path.exists(level2_path):
        
        for root, dirs, filenames in os.walk(level2_path):
            #if len(additional_levels) == 0:
            files = files + collect_files_in_directory(root, nqbits)
            #else:
                #level_path = os.path.join(root, *additional_levels)
                #if os.path.exists(level_path):
                    #files = files + collect_files_in_directory(level_path, nqbits)
                #else:
                    #raise ValueError("Wrong benchmark parameter")
    return files

def load_qasm_files(benchname: str, nqbits: tuple[int, int] = (2, 1000), benchmark_suites: list[str] = valid_benchmark_suites, optional_args: list[str] = []):
    if not isinstance(benchname, str) or len(benchname) == 0:
        raise ValueError("Benchmark name is not valid")

    if not isinstance(nqbits, tuple):
        raise ValueError("No range was given. Usage: (lower_limit, upper_limit)")
    if not (isinstance(nqbits[0], int) and isinstance(nqbits[1], int)):
        raise ValueError("Range is not integer")
    if nqbits[0] < 2:
        raise ValueError("Number of qubits must be greater than 2")

    if not isinstance(benchmark_suites, list):
        raise ValueError("Expected list of benchmark suite names")
    for b in benchmark_suites:
        if not isinstance(b, str) or b not in valid_benchmark_suites:
            raise ValueError("Benchmark suite names must be string and valid")

    files_to_return = []

    for benchmark_suite in benchmark_suites:
        files_to_return = files_to_return + collect_files("benchmarks", benchmark_suite, benchname, nqbits, optional_args)

    return files_to_return


#benchname = sys.argv[1]
#lower_limit = int(sys.argv[2])
#upper_limit = int(sys.argv[3])
#benchmark_suites = ["MQTBench", "QASMBench", "QOSLib", "Supermarq"]
#optional = sys.argv[4:]

#load_qasm_files(benchname, (lower_limit, upper_limit), benchmark_suites, optional)