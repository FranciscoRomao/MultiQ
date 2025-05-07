
from zac.ds.architecture import Architecture

class InstructionBuilder:
    def __init__(self, arch: Architecture):
        self.instructions = []
        self.current_id = 0
        self.architecture = arch
        