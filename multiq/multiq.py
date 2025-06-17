import logging
import json

import zac.zac as zac
from multiq.compiler.planner import Planner
from multiq.compiler.orchestrator import Orchestrator
from multiq.animator.animator import Animator
from multiq.configuration import MultiQConfig

logger = logging.getLogger("multiq")

class MultiQ:
    def __init__(self):
        self.print_configuration()
        self.tiles = []
        self.config = MultiQConfig()

    def print_configuration(self):
        logger.info("MultiQ config settings goes here...")

    # TODO: remove, unused
    def init_zac(self):
        zac_settings = {
            "routing_strategy": "maximalis",
            "scheduling": "asap",
            "trivial_placement": False,
            "dynamic_placement": True,
            "use_window": True,
            "window_size": 1000,
            "reuse": True
        }
        
        zacc = zac.ZAC()
        zacc.parse_setting(zac_settings)
        zacc.set_architecture(self.arch)

        return zacc

    def set_inputs(self, input_files: list[str]):

        self.planner = Planner(self.config)
        self.planner.set_input_circuits(input_files, optimization_level=3)
        self.tiles = self.planner.set_best_architectures()

        compiler = Orchestrator(self.config)
        compiler.set_programs(self.tiles)
        compiler.compile()
        compiler.write_output("./results")
        
        anim = Animator(self.config, self.config.grid_rows, self.config.grid_cols)
        anim.multi_animate(compiler.tiles, "test.mp4")

        
        
        






