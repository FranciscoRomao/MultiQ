from .tile import Tile
from multiq.configuration import MultiQConfig

import logging

logger = logging.getLogger("multiq")


class InstructionBuilder:
    """ Build global instructions for the orchestrator. """

    def __init__(self, config: MultiQConfig):
        self.config = config

    def write_initial_instruction(self, tiles: list[list[Tile | None]]):
        for row_idx, row in enumerate(tiles):
            for col_idx, tile in enumerate(row):
                if not tile:
                    continue

                tile.result_json["instructions"].clear()
                tile.result_json["instructions"].append({
                    "type": "init",
                    "id": 0,
                    "begin_time": 0,
                    "end_time": 0,
                    # qubit_mapping entries are (aod_idx, row, col).
                    "init_locs": [[i, tile.qubit_mapping[0][i][0], tile.qubit_mapping[0][i][1], tile.qubit_mapping[0][i][2]]
                                  for i in range(tile.n_q)]
                }
                )

        return self.row_1q_init_gates(tiles)

    def row_1q_init_gates(self, tiles: list[list[Tile | None]]):
        """ Apply 1q gates one storage row at a time with the AOD laser. """

        r1q_time = self.config.r1q_time
        end_time = 0.0

        for _, row in enumerate(tiles):
            for _, tile in enumerate(row):
                if tile:
                    # All tiles share this value, but some grid slots can be empty.
                    storage_zone_rows = tile.config.storage_zone_rows
                    break

        for tile_row in range(storage_zone_rows):
            pulse_applied = False
            for i, row in enumerate(tiles):
                for j, tile in enumerate(row):
                    if not tile:
                        continue

                    row_mapping = [
                        mapping for mapping in tile.qubit_mapping[0]]

                    qubits_in_row = {idx for idx, mapping in enumerate(
                        tile.qubit_mapping[0]) if mapping[1] == tile_row}

                    set_qubit_dependency = set()
                    inst_idx = len(tile.result_json['instructions'])

                    list_1q_gate = [
                            gate_1q for gate_1q in tile.dict_g_1q_parent[-1] if gate_1q[1] in qubits_in_row]

                    result_gate = []
                    for gate_info in list_1q_gate:
                        set_qubit_dependency.add(
                            tile.qubit_dependency[gate_info[1]])
                        tile.qubit_dependency[gate_info[1]] = inst_idx
                        result_gate.append({
                            "name": gate_info[0],
                            "q": gate_info[1],
                            "params": gate_info[2] if len(gate_info) > 2 else None
                        })

                    dependency = {"qubit": []}
                    dependency["qubit"] = list(set_qubit_dependency)

                    if len(result_gate) > 0:
                        tile.write_row1q_gate_instruction(
                            tile_row, inst_idx, result_gate, dependency, row_mapping)
                        tile.result_json['instructions'][-1]["begin_time"] = end_time
                        tile.result_json['instructions'][-1]["end_time"] = end_time + r1q_time
                        pulse_applied = True

            if pulse_applied:
                end_time += r1q_time

        return end_time


    def row_1q_gate_instruction(self, tiles: list[list[Tile | None]], layer: int, begin_time: float):
        """ Apply 1q gates one storage row at a time with the AOD laser. """

        r1q_time = self.config.r1q_time
        end_time = begin_time

        for _, row in enumerate(tiles):
            for _, tile in enumerate(row):
                if tile:
                    # All tiles share this value, but some grid slots can be empty.
                    storage_zone_rows = tile.config.storage_zone_rows
                    break

        for tile_row in range(storage_zone_rows):
            pulse_applied = False
            for i, row in enumerate(tiles):
                for j, tile in enumerate(row):
                    if not tile or layer >= len(tile.gate_1q_scheduling):
                        continue

                    row_mapping = [
                        mapping for mapping in tile.qubit_mapping[2 * layer]]

                    qubits_in_row = {idx for idx, mapping in enumerate(
                        tile.qubit_mapping[2 * layer]) if mapping[1] == tile_row}

                    set_qubit_dependency = set()
                    inst_idx = len(tile.result_json['instructions'])

                    list_1q_gate = filter(
                            lambda g: g[1] in qubits_in_row, tile.gate_1q_scheduling[layer])

                    result_gate = []
                    for gate_info in list_1q_gate:
                        set_qubit_dependency.add(
                            tile.qubit_dependency[gate_info[1]])
                        tile.qubit_dependency[gate_info[1]] = inst_idx
                        result_gate.append({
                            "name": gate_info[0],
                            "q": gate_info[1],
                            "params": gate_info[2] if len(gate_info) > 2 else None
                        })

                    dependency = {"qubit": []}
                    dependency["qubit"] = list(set_qubit_dependency)

                    if len(result_gate) > 0:
                        tile.write_row1q_gate_instruction(
                            tile_row, inst_idx, result_gate, dependency, row_mapping)
                        tile.result_json['instructions'][-1]["begin_time"] = end_time
                        tile.result_json['instructions'][-1]["end_time"] = end_time + r1q_time
                        pulse_applied = True

            if pulse_applied:
                end_time += r1q_time

        return end_time
