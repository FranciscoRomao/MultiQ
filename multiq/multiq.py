import logging

from multiq.compiler.planner import Planner
from multiq.compiler.orchestrator import Orchestrator
from multiq.animator.animator import Animator
from multiq.configuration import MultiQConfig

logger = logging.getLogger("multiq")

class MultiQ:
    def __init__(self):
        self.config = MultiQConfig.from_config_file("config.yaml")

    def set_inputs(self, input_files: list[str]):
        
        self.planner = Planner(self.config)
        self.planner.set_input_circuits(input_files, optimization_level=3)
        tiles = self.planner.set_best_architectures()

        compiler = Orchestrator(self.config)
        compiler.set_programs(tiles)
        compiler.compile()
        compiler.write_output("./results")
        
        anim = Animator(self.config, self.config.grid_rows, self.config.grid_cols)
        anim.multi_animate(compiler.tiles, "animation.mp4")