import logging

from multiq.compiler.planner import Planner
from multiq.compiler.orchestrator import Orchestrator
from multiq.animator.animator import Animator
from multiq.configuration import MultiQConfig
from multiq.compiler.scheduler import CircuitSASelector

logger = logging.getLogger("multiq")

class MultiQ:
    def __init__(self):
        self.config = MultiQConfig.from_config_file("config.yaml")

    def set_inputs(self, input_files: list[str]):
        
        self.planner = Planner(self.config)
        self.planner.set_input_circuits(input_files, optimization_level=3)
        tiles = self.planner.set_best_architectures()

        self.selector = CircuitSASelector(self.config)

        # There is a bug on the selector where the cost starts to be negative at some point,
        # although it should not be possible it doesnt seem to affect the results.
        # There is no time now to fix it, I will leave it for later.
        self.bins = self.selector.select(tiles)
        
        logger.info("Bundled tiles:")
        for i, result in enumerate(self.bins):
            logger.info(f"Result bin {i}: {result}")
        
        for idx, bin in enumerate(self.bins):
            logger.info(f"Starting compilation for bin {idx} with {len(bin)} tiles")
            logger.info("-" * 50)
            compiler = Orchestrator(self.config)
            compiler.set_programs(bin)
            compiler.compile()
            compiler.write_output(f"./results_bin{idx}")
        
            anim = Animator(self.config, self.config.grid_rows, self.config.grid_cols)
            anim.multi_animate(compiler.tiles, f"test_bin{idx}.mp4")

'''
paths = [
    "circuits/random0_8.qasm",
    "circuits/random1_8.qasm",
    "circuits/random0_10.qasm",
    "circuits/random1_10.qasm",
    "circuits/random0_12.qasm",
    "circuits/random1_12.qasm"]

circuits = [os.path.join(os.path.dirname(__file__), path) for path in paths]
transpiled = [transpile(QuantumCircuit.from_qasm_file(circuit), optimization_level=0, basis_gates=['u3', 'rz', 'rzz', 'cz']) for circuit in circuits]

#dag0 = circuit_to_dag(transpiled0_o3)
#dag1 = circuit_to_dag(transpiled1_o3)

#dag0.draw(filename="dag0.png")
#dag1.draw(filename="dag1.png")

#transpiled0_o3.draw(output='mpl', filename="transpiled0.png")
#transpiled1_o3.draw(output='mpl', filename="transpiled1.png")

#merged_circuits = merge_circuits([transpiled0_o3, transpiled1_o3])
#dag_merged = circuit_to_dag(merged_circuits)
#dag_merged.draw(filename="merged_dag.png")
#merged_circuits.draw(output='mpl', filename="merged_circuit.png")

#circuits: List[QuantumCircuit],
#merge_circuits: Callable,
#split_circuit_into_layers: Callable,
#circuit_layer_cost: Callable,
#window: int = 5,
#verbose: bool = True,

default_params = {
    'initial_temperature': 1000.0,
    'final_temperature': 0.1,
    'cooling_rate': 0.95,
    'max_iterations': 1000,
    'max_iterations_per_temp': 100,
    'swap_distance_limit': 5,
    'swap_attempts': 20,
    'multi_circuit_prob': 0.3}

self.config = MultiQConfig.from_config_file("config.yaml")

planner = Planner()

selector = CircuitSASelector(**default_params)

out = selector.select(
    initial_circuits=circuits, merge_circuits=merge_circuits,
    split_circuit_into_layers=split_circuit_into_layers,
    circuit_layer_cost=circuit_layer_cost,
    window=5,  # Window size for layer splitting
    verbose=True)
'''
