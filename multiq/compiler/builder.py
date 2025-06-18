
from zac.ds.architecture import Architecture

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
                    # qubit_mapping format: qubit |-> (aod_idx=0, row, col)
                    "init_locs": [[i, tile.qubit_mapping[0][i][0], tile.qubit_mapping[0][i][1], tile.qubit_mapping[0][i][2]]
                                  for i in range(tile.n_q)]
                }
                )

        return self.row_1q_gate_instruction(tiles)

    def row_1q_gate_instruction(self, tiles: list[list[Tile | None]]):
        """ Instead of applying 1q gates serially, apply a whole row at a time using AoD laser. """

        r1q_time = self.config.r1q_time
        end_time = 0.0

        for i in range(len(tiles)):
            for j in range(len(tiles[i])):
                if tiles[i][j] is not None:
                    #It is the same for all tiles, but if we set more tile spaces (grid_cols x grid_rows)
                    # than the input circuits we need to find the first non-empty tile to get this information
                    storage_zone_rows = tiles[i][j].config.storage_zone_rows
                    break

        # process the gates per tile row so that we can use row-based 1q gate application
        for tile_row in range(storage_zone_rows):
            pulse_applied = False
            for _, row in enumerate(tiles):
                for _, tile in enumerate(row):
                    if not tile:
                        continue

                    qubits_in_row: set[int] = set()
                    for quidx, map in enumerate(tile.qubit_mapping):
                        if map:
                            if map[0][1] == tile_row:
                                qubits_in_row.add(quidx)

                    set_qubit_dependency = set()
                    inst_idx = len(tile.result_json['instructions'])

                    list_1q_gate = [
                        gate_1q for gate_1q in tile.dict_g_1q_parent[-1] if gate_1q[1] in qubits_in_row]

                    result_gate = []
                    for gate_info in list_1q_gate:
                        # collect qubit dependency
                        set_qubit_dependency.add(
                            tile.qubit_dependency[gate_info[1]])
                        tile.qubit_dependency[gate_info[1]] = inst_idx
                        result_gate.append({
                            "name": gate_info[0],
                            "q": gate_info[1]
                        })

                    dependency = {"qubit": []}
                    dependency["qubit"] = list(set_qubit_dependency)

                    if len(result_gate) > 0:
                        tile.write_row1q_gate_instruction(
                            tile_row, inst_idx, result_gate, dependency, tile.qubit_mapping[0])
                        tile.result_json['instructions'][-1]["begin_time"] = end_time
                        tile.result_json['instructions'][-1]["end_time"] = end_time + r1q_time
                        pulse_applied = True

            if pulse_applied:
                end_time += r1q_time

        return end_time
