
from zac.ds.architecture import Architecture

class InstructionBuilder:
    def __init__(self, arch: Architecture):
        self.instructions = []
        self.current_id = 0
        self.architecture = arch
        

    def write_initial_instruction(self, qubit_mapping, n_q):
        self.instructions.clear()
        self.instructions.append(
            {
                "type": "init",
                "id": 0,
                "begin_time": 0,
                "end_time": 0,
                "init_locs": [ [i, self.qubit_mapping[0][i][0], self.qubit_mapping[0][i][1], self.qubit_mapping[0][i][2]]
                 for i in range(self.n_q)]
            }
        )