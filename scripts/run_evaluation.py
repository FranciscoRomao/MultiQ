from baselines.zac_runner import run_zac_single_benchmarks
#from baselines.pachinqo_runner import run_pachiqo_single_benchmarks
from baselines.multiq_runner import run_multiq_planner_eval
import logging

# Set up logging only for multiq messages
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')
logging.getLogger("qiskit").setLevel(logging.WARNING)

#run_zac_single_benchmarks()

#run_pachiqo_single_benchmarks()

run_multiq_planner_eval()