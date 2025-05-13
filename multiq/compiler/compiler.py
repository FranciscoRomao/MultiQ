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
from multiq.router.router import Router_mixin, Movement
from .tile import ZacTile

logger = logging.getLogger("multiq")


class Compiler():
    """class to solve QLS problem."""

    def __init__(self, arch: Architecture):
        self.architecture = arch
        self.tiles: ZacTile = []
        self.config: MultiQConfig = None

        # global aod
        self.aod_end_time = [(0, i) for i in range(len(arch.dict_AOD))]
        self.aod_dependency = [0 for i in range(len(arch.dict_AOD))]

        self.global_instructions = []
        self.global_runtime = 0

        self.global_aod_end_time = [(0, i) for i in range(len(arch.dict_AOD))]
        self.global_aod_dependency = [0 for i in range(len(arch.dict_AOD))]

        self.global_qubit_dependency = {}
        self.global_site_dependency = {}
        self.global_rydberg_dependency = [0 for i in range(
            len(self.architecture.entanglement_zone))]

    def route_global_layer(self, layer_id: int):
        pass

    def route_global_batch(self):
        for t in self.tiles:
            t.prepare_routing()

        layer: int = 0
        # interference graph for each individual tile at a specific layer
        while any([len(t.gate_scheduling) > 0 for t in self.tiles]):

            graphs: list[(int, list, list)] = []
            for tile_id, tile in enumerate(self.tiles):
                if layer >= len(tile.gate_scheduling):
                    continue
                graph, moves = tile.nx_interference_graph(layer)
                graphs.append((tile_id, graph, moves))
                tile.gate_scheduling.pop(0)

            if len(graphs) == 0:
                break

            graph, global_moves = self.combine_nx_graphs(graphs)

            while graph.number_of_nodes() > 0:
                indp_nodes = nx.maximal_independent_set(graph)
                indp_moves_per_tile = [[] for _ in range(len(self.tiles))]

                # partition the independent set by tile
                for i_node in indp_nodes:
                    (tile_id, movement) = global_moves[i_node]
                    indp_moves_per_tile[tile_id].append(movement)

                # process the instructions on the tile level
                for tile_id, tile in enumerate(self.tiles):
                    tile_moves = indp_moves_per_tile[tile_id]
                    qubits = {move.qubit_index for move in tile_moves}
                    tile.process_movement_layer(
                        qubits, tile.qubit_mapping[2 * layer], tile.qubit_mapping[2 * layer + 1])

                graph.remove_nodes_from(indp_nodes)

            for t in self.tiles:
                t.process_gate_layer(layer, t.qubit_mapping[2 * layer + 1])
            layer += 1

        print("The tiles are")
        for t in self.tiles:
            print(t.result_json["instructions"])
            print("===")

    def combine_graphs(self, graphs: list[(int, list, list)]):
        combined_nodes = []
        combined_edges = []

        tile = 0
        for id, nodes, edges in graphs:
            n_nodes = len(nodes)  # number of movements in one tile
            combined_nodes.extend([(id, *n) for n in nodes])
            # An edge is a pair of indices. Need to adjust new indices for each subgraph
            combined_edges.extend([(i + tile, j + tile) for i, j in edges])
            tile += n_nodes

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

        if a_x1 != b_x1:
            return False
        if a_x2 != b_x2:
            return False

        return True

    def global_aod_timing_assignment(self):
        pass

    def global_get_begin_time(self):
        pass

    # def parse_setting(self, setting: dict):
    #     self.config = MultiQConfig.from_config(setting)

    def set_architecture_spec_path(self, path: str):
        self.result_json['architecture_spec_path'] = path

    # def set_initial_mapping(self, mapping):
    #    # todo: check if the given mapping is valid
    #    self.given_initial_mapping = mapping

    def compile(self):
        # gate shceduling and placement are done per-tile with no cross-tile considerations
        for tile in self.tiles:
            # gate scheduling with graph colouring
            tile.scheduling()
            if tile.reuse:
                tile.collect_reuse_qubit()
            else:
                tile.reuse_qubit = [set()
                                    for _ in range(len(self.gate_scheduling))]
            tile.place_qubit_initial()
            tile.place_qubit_intermedeiate()

        # Routing must be done globally
        self.route_global_batch()

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
