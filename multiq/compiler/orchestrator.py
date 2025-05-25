from zac.scheduler.scheduler import Scheduler_mixin
from zac.placer.placer import Placer_mixin
from zac.animator.animator import Animator
from zac.verifier.verifier import Verifier_mixin
from zac.ds.architecture import Architecture
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import maximum_bipartite_matching

import matplotlib.pyplot as plt
import qiskit.qasm2 as qasm2
import networkx as nx

import time
import logging

from multiq.configuration import MultiQConfig
from multiq.router import Movement, Router_mixin

from .tile import ZacTile
from .builder import InstructionBuilder

logger = logging.getLogger("multiq")


class Orchestrator:
    def __init__(self, arch: Architecture):
        self.architecture = arch
        self.tiles: list[ZacTile] = []
        self.config: MultiQConfig = None
        self.instr_builder = InstructionBuilder()

        # all operations on all tiles are measured according to this global time
        self.global_time = 0.0
        self.aod_end_time = 0.0  # finish time of currently executing instruction on AoD
        self.rydberg_end_time = 0.0  # finish time of the current/last rydberg operation

        self.active_tiles: list[int] = []  # indices of the active tiles

    def route(self):
        """ Routes all movements, gate ops, rydberg ops across all of the tiles. """

        # Append all tiles which have instructions to the active list
        for tile_id, tile in enumerate(self.tiles):
            if len(tile.gate_scheduling) > 0:
                self.active_tiles.append(tile_id)
                tile.prepare_routing()

        logger.info(f"There are {len(self.active_tiles)} active tiles")

        # write_initial_instruction() returns end_time. Global schedule waits till last tile is finished
        self.global_time = max(
            [self.instr_builder.write_initial_instruction(t) for t in self.tiles])

        layer: int = 0
        while len(self.active_tiles) > 0:
            self.route_layer(layer)
            layer += 1

        for t in self.tiles:
            t.flatten_rearrangment_instruction()

    def route_layer(self, layer: int):
        graphs: list[(int, list, list)] = []
        for tile_id in self.active_tiles:
            tile = self.tiles[tile_id]
            if layer >= len(tile.gate_scheduling):
                self.active_tiles.remove(tile_id)
                logger.info(f"Removing tile_id {tile_id} as it has finished")
                continue
            graph, moves = tile.nx_interference_graph(layer)
            graphs.append((tile_id, graph, moves))

        if len(graphs) == 0:
            return

        graph, global_moves = self.combine_nx_graphs(graphs)

        #fig = plt.figure()
        #nx.draw(graph, ax=fig.add_subplot(), with_labels=True)
        #fig.savefig(f"graph_layer_{layer}_before_removals.png")


        while graph.number_of_nodes() > 0:
            comp_graph = nx.complement(graph)
            indp_nodes = max(nx.find_cliques(comp_graph), key=len, default=[])
            graph.remove_nodes_from(indp_nodes)

            print(f"Indp nodes for this iteration of layer {layer} are {indp_nodes}")

            indp_moves_per_tile = [[] for _ in range(len(self.tiles))]

            # partition the independent set by tile
            for i_node in indp_nodes:
                (tile_id, movement) = global_moves[i_node]
                indp_moves_per_tile[tile_id].append(movement)

            print(f"Independent moves for this iteration of layer {layer} are {indp_moves_per_tile}")

            tile_start_idices = {
                id: len(self.tiles[id].result_json["instructions"]) for id in self.active_tiles}
            self.process_movement(layer, indp_moves_per_tile)
            self.aod_assignment(tile_start_idices)

        # add gate layers
        rydberg_instrs = self.process_gates(layer)
        self.rydberg_assignment(rydberg_instrs)
        graphs.clear()


        # gather reverse movements
        for tile_id in self.active_tiles:
            tile = self.tiles[tile_id]
            graph, moves = tile.nx_reverse_interference_graph(layer)
            if graph is not None:
                graphs.append((tile_id, graph, moves))
        graph, global_moves = self.combine_nx_graphs(graphs)

        while graph.number_of_nodes() > 0:
            comp_graph = nx.complement(graph)
            indp_nodes = max(nx.find_cliques(comp_graph), key=len, default=[])

            indp_moves_per_tile = [[] for _ in range(len(self.tiles))]
            for i_node in indp_nodes:
                (tile_id, movement) = global_moves[i_node]
                indp_moves_per_tile[tile_id].append(movement)
                
            tile_reverse_idices = {id: len(self.tiles[id].result_json["instructions"]) for id in self.active_tiles}
            self.process_rev_movement(layer, indp_moves_per_tile)
            self.aod_assignment(tile_reverse_idices)
            graph.remove_nodes_from(indp_nodes)

    def combine_nx_graphs(self, graphs: list[tuple[int, nx.Graph, list[Movement]]]) -> tuple[nx.Graph, list[tuple[int, Movement]]]:
        """ Take a list of (tile_id, conflict graph, movement list) and combine it into a single graph """
        graph_data = [g for _, g, _ in graphs]
        # nodes become [0,...,len(g_1),...,len(g_2),...]
        combined_graph = nx.disjoint_union_all(graph_data)
        # combined_graph's nodes index into this list
        global_move_data = []

        for tile_id, _, moves_for_tile in graphs:
            for move in moves_for_tile:
                global_move_data.append((tile_id, move))

        for i, (tile_id, mov) in enumerate(global_move_data):
          for j, (tile_id2, mov2) in enumerate(global_move_data):
              if tile_id != tile_id2:
                  if not self.tilewise_compatible(mov, mov2):
                      combined_graph.add_edge(i, j)

        return combined_graph, global_move_data

    # Across multiple tiles, only moves that share row coords can be done in parallel
    def tilewise_compatible(self, a: Movement, b: Movement) -> bool:
        # a,b must be from different tiles

        # must be same start row
        if a.start_y != b.start_y:
            return False
        # must be same finish row
        if a.end_y != b.end_y:
            return False

        return True

    def process_movement(self, layer: int, indp_moves_per_tile: list[list[Movement]]):
        # process the instructions on the tile level

        tile_instr_start_indices = [0 for _ in range(len(self.active_tiles))]

        for tile_id in self.active_tiles:
            tile = self.tiles[tile_id]

            tile_moves = indp_moves_per_tile[tile_id]
            qubits = {move.qubit_index for move in tile_moves}
            id = tile.process_movement_layer(
                qubits, tile.qubit_mapping[2 * layer], tile.qubit_mapping[2 * layer + 1])
            tile_instr_start_indices[tile_id] = id

        return tile_instr_start_indices

    def process_rev_movement(self, layer: int, indp_moves_per_tile: list[list[Movement]]):
        # process the instructions on the tile level

        tile_instr_start_indices = [0 for _ in range(len(self.active_tiles))]

        for tile_id in self.active_tiles:
            tile = self.tiles[tile_id]

            if tile.qubit_mapping[2 * layer + 2] is None:
                tile.construct_reverse_layer(
                    # None
                    tile_instr_start_indices[tile_id], tile.qubit_mapping[2 * layer], tile.qubit_mapping[2 * layer + 2])
            else:
                tile_moves = indp_moves_per_tile[tile_id]
                qubits = {move.qubit_index for move in tile_moves}
                id = tile.process_movement_layer(
                    qubits, tile.qubit_mapping[2 * layer + 1], tile.qubit_mapping[2 * layer + 2])
                tile_instr_start_indices[tile_id] = id

        return tile_instr_start_indices

    def aod_assignment(self, instr_start_indices: dict[int, int]):
        """ 
            This is the central scheduler for each batch of operations across the multiple tiles.
        """

        # AoD assignment phase
        # 1. query each tile for begin time time_s_i of instruction id_layer_start (get_begin_time)
        # 2. start_time = max({time_s_i | tiles}, aod_end_time)
        # 3. aod_assignment for each tile with unified start_time
        # 4. end_time = max({time_e_i | tiles})

        start_times = []
        for id, idx in instr_start_indices.items():
            instr = self.tiles[id].result_json["instructions"][idx]
            time_st_i = self.tiles[id].get_begin_time(idx, instr["dependency"])
            start_times.append(time_st_i)

        global_start_time = max(max(start_times), self.aod_end_time)

        for id in self.active_tiles:
            tile = self.tiles[id]
            instr_id_start = instr_start_indices[id]
            durations = []

            # get durations of move operations
            for idx in range(instr_id_start, len(tile.result_json["instructions"])):
                instr = tile.result_json["instructions"][idx]
                if instr["type"] != "rearrangeJob":
                    # we have reached the gate operations
                    break
                durations.append((tile.get_duration(instr), idx))

            for duration, idx in durations:
                instr = tile.result_json["instructions"][idx]

                begin_time = global_start_time
                end_time = global_start_time + duration

                instr["dependency"]["aod"] = -1
                instr["begin_time"] = begin_time
                instr["end_time"] = end_time
                instr["aod_id"] = 0

                # add begin_time offset to the sub-intructions
                for detail_inst in instr["insts"]:
                    detail_inst["begin_time"] += begin_time
                    detail_inst["end_time"] += begin_time

                # update global tile runtime statistic
                tile.result_json["runtime"] = max(
                    tile.result_json["runtime"], end_time)

                self.aod_end_time = max(self.aod_end_time, end_time)


    def rydberg_assignment(self, ryd_instr_start_indices: dict[int, int]):
        global_earliest_start = 0.0
        global_end_time = 0.0

        # find out the earliest time the global pulse can start
        for id, start_idx in ryd_instr_start_indices.items():
            tile = self.tiles[id]
            dep = tile.result_json["instructions"][start_idx]["dependency"]
            rydb_begin_time = tile.get_begin_time(start_idx, dep)
            global_earliest_start = max(global_earliest_start, rydb_begin_time)

        global_end_time = global_earliest_start + self.architecture.time_rydberg
        # update global rydberg busy time
        self.rydberg_end_time = global_end_time

        # assign times to instructions
        for id, start_idx in ryd_instr_start_indices.items():
            tile = self.tiles[id]
            # use this counter for sequential 1q gate applications in the gate layer
            local_start_time = global_end_time

            for idx in range(start_idx, len(tile.result_json["instructions"])):
                instr = tile.result_json["instructions"][idx]
                if instr["type"] == "rearrangeJob":
                    # we have reached the end of the gate layer
                    break
                if instr["type"] == "rydberg":
                    # there should only be one of these in the layer
                    instr["begin_time"] = global_earliest_start
                    instr["end_time"] = global_end_time
                    # update runtime stat
                    tile.result_json["runtime"] = max(
                        tile.result_json["runtime"], global_end_time)
                else:
                    # fill in 1q gates if there are any. These operations don't need to be synchronised.
                    instr["begin_time"] = local_start_time
                    local_end_time = local_start_time + \
                        len(instr["gates"]) * tile.architecture.time_1qGate
                    instr["end_time"] = local_end_time
                    tile.result_json["runtime"] = max(
                        tile.result_json["runtime"], local_end_time)
                    # update local start time
                    local_start_time = local_end_time

    def process_gates(self, layer: int):

        gate_instrs = {}

        for tile_id in self.active_tiles:
            tile = self.tiles[tile_id]
            initial_indx = tile.process_gate_layer(
                layer, tile.qubit_mapping[2 * layer + 1])
            if initial_indx is not None:
                gate_instrs[tile_id] = initial_indx

        return gate_instrs

    def process_reverse_movement(self, layer: int, tile_start_indices: list[int], indp_moves_per_tile: list[list[Movement]]):
        for tile_id in self.active_tiles:
            tile = self.tiles[tile_id]
            tile.construct_reverse_layer(
                tile_start_indices[tile_id], tile.qubit_mapping[2 * layer + 1], tile.qubit_mapping[2 * layer + 2])

    # def parse_setting(self, setting: dict):
    #     self.config = MultiQConfig.from_config(setting)

    def compile(self):
        # gate shceduling and placement are done per-tile with no cross-tile considerations
        for tile in self.tiles:
            # gate scheduling with graph colouring
            tile.scheduling()
            # NOTE: turn back on when schedling works!
            # if tile.reuse:
            #    tile.collect_reuse_qubit()
            # else:
            tile.reuse_qubit = [set()
                                for _ in range(len(tile.gate_scheduling))]
            tile.place_qubit_initial()
            tile.place_qubit_intermedeiate()

        # Routing must be done globally
        self.route()

        logger.info("Total runtimes:")
        for tile in self.tiles:
            logger.info(f"{tile.result_json["runtime"]} ms")

    def set_programs(self, source_files: list[str]):
        for source_file in source_files:
            tile = ZacTile(self.config)
            zac_settings = {
                "routing_strategy": "maximalis",
                "scheduling": "asap",
                "trivial_placement": False,
                "dynamic_placement": True,
                "use_window": True,
                "window_size": 1000,
                "reuse": True
            }
            tile.parse_setting(zac_settings)
            tile.set_architecture(self.architecture)
            tile.load_program(source_file)
            self.tiles.append(tile)
