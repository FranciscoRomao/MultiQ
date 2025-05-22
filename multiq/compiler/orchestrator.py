from zac.scheduler.scheduler import Scheduler_mixin
from zac.placer.placer import Placer_mixin
from zac.animator.animator import Animator
from zac.verifier.verifier import Verifier_mixin
from zac.ds.architecture import Architecture
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import maximum_bipartite_matching

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
        self.rydberg_end_time = 0.0 # finish time of the current/last rydberg operation

        self.active_tiles: list[int] = [] # indices of the active tiles

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
        # interference graph for each individual tile at a specific layer
        while len(self.active_tiles) > 0:

            graphs: list[(int, list, list)] = []
            for tile_id in self.active_tiles:
                tile = self.tiles[tile_id]

                if layer >= len(tile.gate_scheduling):
                    self.active_tiles.remove(tile_id)
                    logger.info("Removing tile_id", tile_id, "from active tiles. It is now", self.active_tiles)
                    continue

                graph, moves = tile.nx_interference_graph(layer)
                graphs.append((tile_id, graph, moves))

            if len(graphs) == 0:
                break

            graph, global_moves = self.combine_nx_graphs(graphs)
            tile_instr_start_indices = [0 for _ in range(len(self.active_tiles))]

            tile_st = [len(t.result_json['instructions']) for t in self.tiles]

            while graph.number_of_nodes() > 0:
                indp_nodes = nx.maximal_independent_set(graph)
                indp_moves_per_tile = [[] for _ in range(len(self.tiles))]

                # partition the independent set by tile
                for i_node in indp_nodes:
                    (tile_id, movement) = global_moves[i_node]
                    indp_moves_per_tile[tile_id].append(movement)

                self.process_movement(layer, indp_moves_per_tile)
                graph.remove_nodes_from(indp_nodes)

            # add gate layers
            rydberg_instrs = self.process_gates(layer)

            graphs.clear()
            for tile_id in self.active_tiles:
                tile = self.tiles[tile_id]
                graph, moves = tile.nx_reverse_interference_graph(layer)
                if graph is not None:
                    graphs.append((tile_id, graph, moves))

            graph, global_moves = self.combine_nx_graphs(graphs)
            while graph.number_of_nodes() > 0:
                indp_nodes = nx.maximal_independent_set(graph)
                indp_moves_per_tile = [[] for _ in range(len(self.tiles))]
                for i_node in indp_nodes:
                    (tile_id, movement) = global_moves[i_node]
                    indp_moves_per_tile[tile_id].append(movement)

                self.process_rev_movement(layer, indp_moves_per_tile)
                graph.remove_nodes_from(indp_nodes)
                

            print("finished layer. Now assign aod...")
            # assign global aod resource
            self.aod_assignment(tile_st)
            self.rydberg_assignment(rydberg_instrs)

            layer += 1

        for t in self.tiles:
            t.flatten_rearrangment_instruction()

        print("The tiles are")
        for t in self.tiles:
            print(t.result_json["instructions"])
            print("===")

        
    def combine_graphs(self, graphs: list[(int, list, list)]):
        combined_nodes = []
        combined_edges = []

        tile_offset = 0
        for id, nodes, edges in graphs:
            n_nodes = len(nodes)  # number of movements in one tile
            combined_nodes.extend([(id, *n) for n in nodes])
            # An edge is a pair of indices. Need to adjust new indices for each subgraph
            combined_edges.extend([(i + tile_offset, j + tile_offset) for i, j in edges])
            tile_offset += n_nodes

        return combined_nodes, combined_edges

    def combine_nx_graphs(self, graphs: list[(int, nx.Graph, list[Movement])]) -> tuple[nx.Graph, list[(int, Movement)]]:
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
        a_x1, a_y1, a_x2, a_y2 = a.start_x, a.start_y, a.end_x, a.end_y
        b_x1, b_y1, b_x2, b_y2 = b.start_x, b.start_y, b.end_x, b.end_y

        # must be same start row
        if a_x1 != b_x1:
            return False
        # must be same finish row
        if a_x2 != b_x2:
            return False

        return True

    # move to builder.py soon
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
                tile.construct_reverse_layer(tile_instr_start_indices[tile_id], tile.qubit_mapping[2 * layer], tile.qubit_mapping[2 * layer + 2]) # None
            else:
                tile_moves = indp_moves_per_tile[tile_id]
                qubits = {move.qubit_index for move in tile_moves}
                id = tile.process_movement_layer(
                    qubits, tile.qubit_mapping[2 * layer + 1], tile.qubit_mapping[2 * layer + 2])
                tile_instr_start_indices[tile_id] = id

        return tile_instr_start_indices


    def aod_assignment(self, instr_start_indices: list[int]):
        """ 
            This is the central scheduler for each batch of operations across the multiple tiles.
        """
        global_end_time = 0.0

        for id in self.active_tiles:
            tile = self.tiles[id]
            global_end_time = max(global_end_time, tile.aod_assignment(instr_start_indices[id], self.aod_end_time))

        self.aod_end_time = global_end_time

    def rydberg_assignment(self, ryd_instr_start_indices: dict[int, int]):
        global_earliest_start = 0.0

        for id in self.active_tiles:
            tile = self.tiles[id]


    def process_gates(self, layer: int):

        gate_instrs = {}

        for tile_id in self.active_tiles:
            tile = self.tiles[tile_id]
            initial_indx = tile.process_gate_layer(layer, tile.qubit_mapping[2 * layer + 1])
            if initial_indx is not None:
                gate_instrs[tile_id] = initial_indx

        return gate_instrs
    

    def process_reverse_movement(self, layer: int, tile_start_indices: list[int], indp_moves_per_tile: list[list[Movement]]):
        for tile_id in self.active_tiles:
            tile = self.tiles[tile_id]
            tile.construct_reverse_layer(tile_start_indices[tile_id], tile.qubit_mapping[2 * layer + 1], tile.qubit_mapping[2 * layer + 2])


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

