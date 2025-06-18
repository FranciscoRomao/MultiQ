import logging
import argparse
import time

from tools.gen_benchmarks import gen_random_NA_circuits

logger = logging.getLogger("multiq")

def main():
    argp = argparse.ArgumentParser(
        prog="Generate Circuits",
        description="Random circuit generator"
    )
    argp.add_argument("-q", "--qubits", nargs="+", help="Number of qubits of the circuit", required=True, type=int)
    argp.add_argument("-d", "--depth", nargs="+", help="Depth of the circuit", required=True, type=int)
    argp.add_argument("-o", "--output", nargs="+", help="Output directory for the generated circuits", required=False, type=str, default=["./circuits/"])
    argp.add_argument("-s", "--seed", nargs="+", help="Random seed for circuit generation", required=False, type=int, default=[(time.time()*1000)])

    args = argp.parse_args()
    
    qubits = int(args.qubits[0])
    depth = int(args.depth[0])
    output = args.output[0]
    seed = int(args.seed[0])

    gen_random_NA_circuits(circuit_sizes=[qubits], depths=[depth], output_folder=output, seed=seed, regen=False, ncircuits_per_size=1)

if __name__ == "__main__":
    main()