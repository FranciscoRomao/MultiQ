import logging
import json

import qiskit.qasm2
import zac.zac as zac

from .animator import Animator

logger = logging.getLogger("multiq")

class Tile():
    def __init__(self, instructions):
        self.instructions = instructions


class MultiQ():
    def __init__(self):
        self.print_configuration()
        self.init_zac()
        self.tiles = []


    def compare_tiles(self):
        tile_a = self.tiles[0]
        tile_b = self.tiles[1]


    def print_configuration(self):
        logger.info("MultiQ config settings goes here...")


    def init_zac(self):
        with open("/home/dan/dev/quantum/multiq/zac_config/multiq_architecture.json", "r") as f:
            arch = zac.Architecture(json.load(f))
            arch.preprocessing()
            self.arch = arch

        zac_settings = {
            "routing_strategy": "maximalis",
            "scheduling": "asap",
            "trivial_placement": False,
            "dynamic_placement": True,
            "use_window": True,
            "window_size": 1000,
            "reuse": True
        }
        self.zac = zac.ZAC()
        self.zac.parse_setting(zac_settings)
        self.zac.set_architecture(arch)

    def set_inputs(self, input_files: list[str]):
        codes = []
        for input in input_files:
            self.zac.set_program(input)
            code_dict = self.zac.solve(save_file=False)
            codes.append(code_dict)

            #t = Tile(code_dict["instructions"])
            #self.tiles.append(t)

            #print("Tile is ", code_dict["instructions"])
            #self.zac.animate(code_dict, output = f"{input}.mp4")
        
        anim = Animator(self.arch)
        anim.multi_animate(codes, "test.mp4")

        
        
        






