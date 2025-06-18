import logging
import argparse

from multiq.multiq import MultiQ

logger = logging.getLogger("multiq")

def main():
    logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)
    argp = argparse.ArgumentParser(
        prog="MultiQ",
        description="Neutral Atom Compiler"
    )
    argp.add_argument("-i", "--input", nargs="+", help="The QASM circuits to be compiled.", required=True, type=str)

    args = argp.parse_args()
    mq = MultiQ()
    mq.set_inputs(args.input)

if __name__ == "__main__":
    main()