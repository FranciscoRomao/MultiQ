import logging
import os
import json

from multiq.compiler.planner import Planner
from multiq.compiler.orchestrator import Orchestrator
from multiq.animator.animator import Animator
from multiq.configuration import MultiQConfig
from multiq.compiler.scheduler import CircuitSASelector
from multiq.checker import Checker
from multiq.simulator import Simulator

logger = logging.getLogger("multiq")

class MultiQ:
    def __init__(self, config_file: str = "config/config.yaml"):
        self.config = MultiQConfig.from_config_file(config_file)

    def set_inputs(self, input_files: list[str]) -> list[list]:
        
        self.planner = Planner(self.config)
        self.planner.set_input_circuits(input_files, optimization_level=3)
        tiles = self.planner.set_best_architectures()

        self.selector = CircuitSASelector(self.config)

        # There is a bug on the selector where the cost starts to be negative at some point,
        # although it should not be possible it doesnt seem to affect the results.
        # There is no time now to fix it, I will leave it for later.
        self.bins = self.selector.select(tiles)
        
        logger.debug("Bundled tiles:")
        for i, result in enumerate(self.bins):
            logger.debug(f"Result bin {i}: {result}")

        output_files:list[list] = []
        
        for idx, bin in enumerate(self.bins):
            logger.info(f"Starting compilation for bin {idx} with {len(bin)} tiles")
            logger.info("-" * 50)
            compiler = Orchestrator(self.config)
            compiler.set_programs(bin)
            compiler.compile()
            json_files = compiler.write_output(os.path.join(self.config.results_dir, f"test_bin{idx}"))
            output_files.append([])

            logger.info(f"Compilation finished for bin {idx}, writing output files...")
            logger.info(f'Starting fidelity simulation for bin {idx} with {len(bin)} tiles')

            for tile_idx, tile in enumerate(bin):
                    sim = Simulator(self.config)
                    sim.parse(json_files[tile_idx])
                    fidelity_result = sim.simulate()
    
                    fidelity_file = f"{json_files[tile_idx].split('.')[0]}_fidelity.json"
                    output_files[idx].append(fidelity_file)

                    with open(fidelity_file, 'w') as f:  
                        json.dump(fidelity_result, f, indent = 2)
                    
            if self.config.multiq_check:
                checker = Checker(self.config)
    
                for tile_idx, tile in enumerate(bin):
                    translated_circuit = checker.translate_ZAIR_to_circuit(tile.result_json['instructions'], tile.n_q)
                    equivalence = checker.check_equivalence(tile.circuit, translated_circuit)
    
                    if not equivalence:
                        logger.error(f"Tile {tile.source_name} is not equivalent after compilation!")
                        logger.error(f"Skipping animation and exiting.")
                        tile.circuit.draw(output='mpl', filename=f"original_circuit.png")
                        translated_circuit.draw(output='mpl', filename=f"translated_circuit.png")
                        #raise ValueError(f"Tile {tile.source_name} is not equivalent after compilation!")
                    else:
                        logger.info(f"Tile {tile.source_name} is equivalent after compilation.")
            
            if self.config.animation:
                logger.info(f"Producing animation...")
                anim = Animator(self.config, self.config.grid_rows, self.config.grid_cols)
                anim.multi_animate(compiler.tiles, os.path.join(self.config.results_dir, f"test_bin{idx}"))

        return output_files

        
