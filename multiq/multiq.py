import logging

from multiq.compiler.planner import Planner
from multiq.compiler.orchestrator import Orchestrator
from multiq.animator.animator import Animator
from multiq.configuration import MultiQConfig
from multiq.compiler.compatiblity_selector import CircuitSASelector

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
        self.bins = self.selector.select(tiles=self.tiles)
        
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
