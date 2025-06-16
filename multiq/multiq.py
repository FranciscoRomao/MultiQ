import logging
import json

import zac.zac as zac

from multiq.compiler.orchestrator import Orchestrator
from multiq.animator.animator import Animator
from multiq.configuration import MultiQConfig

logger = logging.getLogger("multiq")

class MultiQ:
    def __init__(self):
        self.print_configuration()
        self.tiles = []
        with open("zac_config/toy_architecture.json", "r") as f:
            arch = zac.Architecture(json.load(f))
            arch.preprocessing()
            self.arch = arch

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
        
        conf = MultiQConfig()
        
        compiler = Orchestrator(self.arch, conf)
        compiler.set_programs(input_files)
        compiler.compile()
        compiler.write_output("./results")
        
        anim = Animator(conf, conf.grid_rows, conf.grid_cols)
        anim.multi_animate(compiler.tiles, "test.mp4")

        
        
        






