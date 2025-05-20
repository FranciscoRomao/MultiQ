
from zac.ds.architecture import Architecture

from .tile import ZacTile

# build (global) instructions and append them to responsible tile
class InstructionBuilder:
    def __init__(self):
        self.instructions = []
        self.current_id = 0

    def write_initial_instruction(self, tile: ZacTile):
        end_time = 0.0
        tile.result_json["instructions"].clear()
        tile.result_json["instructions"].append(
            {
                "type": "init",
                "id": 0,
                "begin_time": 0,
                "end_time": 0,
                # (qubit, aod_idx=0, row, col)
                "init_locs": [[i, tile.qubit_mapping[0][i][0], tile.qubit_mapping[0][i][1], tile.qubit_mapping[0][i][2]]
                              for i in range(tile.n_q)]
            }
        )

        # process single-qubit gates
        set_qubit_dependency = set()
        inst_idx = len(tile.result_json['instructions'])
        list_1q_gate = [gate_1q for gate_1q in tile.dict_g_1q_parent[-1]]
        result_gate = []

        for gate_info in list_1q_gate:
            # collect qubit dependency
            set_qubit_dependency.add(tile.qubit_dependency[gate_info[1]])
            tile.qubit_dependency[gate_info[1]] = inst_idx
            result_gate.append({
                "name": gate_info[0],
                "q": gate_info[1]
            })

        dependency = {"qubit": []}
        dependency["qubit"] = list(set_qubit_dependency)

        if len(result_gate) > 0:
            end_time = tile.architecture.time_1qGate * len(result_gate)
            self.write_1q_gate_instruction(tile,
                                           inst_idx, result_gate, dependency, tile.qubit_mapping[0])
            tile.result_json['instructions'][-1]["begin_time"] = 0
            tile.result_json['instructions'][-1]["end_time"] = (
                # due to sequential execution
                end_time
            )

        return end_time

    def write_1q_gate_instruction(self, tile: ZacTile, inst_idx: int, result_gate: list, dependency: dict, gate_mapping: list):
        locs = []
        for gate in result_gate:
            locs.append((gate["q"], gate_mapping[gate["q"]][0],
                        gate_mapping[gate["q"]][1], gate_mapping[gate["q"]][2]))

        tile.result_json['instructions'].append(
            {
                "type": "1qGate",
                "unitary": "u3",
                "id": inst_idx,
                "locs": locs,
                "gates": result_gate,
                "dependency": dependency
            }
        )
