import logging
import math
import os
import json
import heapq
import time
from multiprocessing import get_context

import networkx as nx

from multiq.configuration import MultiQConfig

from .tile import Tile
from .builder import InstructionBuilder
from .placement import PlacementOptimiser
from .movement import Movement, row_compatible, column_compatible, diagonal_compatible, TileMovement, global_movement

logger = logging.getLogger("multiq")


def _schedule_and_place_tile(tile: Tile) -> Tile:
    """ Per-tile scheduling and placement, which only touches the tile itself so it can run in a worker process. """
    tile.scheduling()
    tile.collect_reuse_qubit()
    tile.place_qubit_initial()
    tile.place_qubit_intermedeiate()
    # Uses arch_range[1][0] like CircuitSelector._simple_fit_check, and floor so rounding never overfills a bin.
    tile.width = max(1, math.floor(
        tile.architecture.arch_range[1][0] / tile.config.physical_cell_width_um))
    true_height = tile.architecture.arch_range[1][1] - tile.architecture.arch_range[0][1]
    tile.height = max(1, math.floor(true_height / tile.config.physical_cell_height_um))
    return tile


class Orchestrator:
    def __init__(self, config: MultiQConfig):
        self.config: MultiQConfig = config

        self.tiles: list[list[Tile | None]] = [
            [None for _ in range(self.config.grid_cols)] for _ in range(self.config.grid_rows)]
        self.instr_builder = InstructionBuilder(self.config)
        self.tiles_to_place = []

        self.global_time = 0.0
        self.aod_end_time = 0.0

        self.aod_end_times = [(0.0, i) for i in range(self.config.num_aods)]
        self.aod_dependency = [0 for _ in range(self.config.num_aods)]

        self.rydberg_end_time = 0.0

        # Anchor (top-left) cells of tiles that still have layers to route.
        self.active_tiles: list[tuple[int, int]] = []

        self.timing: dict[str, float] = {}

    def route(self):
        """ Routes all movements, gate ops, rydberg ops across all of the tiles. """

        active_tile_objs = []
        for r_idx, row in enumerate(self.tiles):
            for c_idx, tile in enumerate(row):
                if tile and len(tile.gate_scheduling) > 0:
                    self.active_tiles.append((r_idx, c_idx))
                    tile.prepare_routing()
                    active_tile_objs.append(tile)

        logger.info(
            f"There are {len(self.active_tiles)} active tiles before routing.")

        self.global_time = self.instr_builder.write_initial_instruction(
            self.tiles)

        layer: int = 0
        while len(self.active_tiles) > 0:
            self.route_layer(layer)
            layer += 1

        for t_row in self.tiles:
            for t_col in t_row:
                if t_col:
                    t_col.flatten_rearrangment_instruction()

    def route_layer(self, layer: int):
        graphs_data_for_combine: list[tuple[int, int,
                                            int, int, nx.Graph, list[Movement]]] = []

        for (r_idx, c_idx) in list(self.active_tiles):
            tile = self.tiles[r_idx][c_idx]
            assert (tile is not None)

            tile_w_cells = tile.width
            tile_h_cells = tile.height
            if tile_w_cells <= 0 or tile_h_cells <= 0:
                logger.error(f"Tile at ({r_idx},{c_idx}) has invalid width/height attributes "
                             f"(width: {tile_w_cells}, height: {tile_h_cells}) during routing.")
                self.active_tiles.remove((r_idx, c_idx))
                continue

            if layer >= len(tile.gate_scheduling):
                self.active_tiles.remove((r_idx, c_idx))
                logger.info(
                    f"Removing tile_id ({r_idx}, {c_idx}) as it has finished")
                continue
            intra_tile_graph, local_moves = tile.nx_interference_graph(
                layer)
            if intra_tile_graph and local_moves:
                graphs_data_for_combine.append(
                    (r_idx, c_idx, tile_h_cells, tile_w_cells, intra_tile_graph, local_moves))

        if not graphs_data_for_combine:
            return

        graph, global_moves = self.combine_nx_graphs(
            graphs_data_for_combine, layer, is_forward_move=True)

        while graph.number_of_nodes() > 0:
            comp_graph = nx.complement(graph)
            indp_nodes = max(nx.find_cliques(comp_graph), key=len, default=[])
            indp_moves_per_tile = {(r_idx, c_idx): []
                                   for (r_idx, c_idx) in self.active_tiles}

            for i_node in indp_nodes:
                anchor_r, anchor_c, _, _, local_movement = global_moves[i_node]
                indp_moves_per_tile[(anchor_r, anchor_c)
                                    ].append(local_movement)

            tile_reverse_indices = {
                (row_idx, col_idx): len(self.tiles[row_idx][col_idx].result_json["instructions"]) for (row_idx, col_idx) in self.active_tiles}
            self.process_movement(layer, indp_moves_per_tile)
            self.aod_assignment(tile_reverse_indices)
            graph.remove_nodes_from(indp_nodes)

        rydberg_instrs = self.process_gates(layer)
        self.rydberg_assignment(rydberg_instrs)
        graphs_data_for_combine.clear()


        for (r_idx, c_idx) in self.active_tiles:
            tile = self.tiles[r_idx][c_idx]
            assert (tile)
            tile_h_cells = tile.height
            tile_w_cells = tile.width

            intra_tile_graph, local_moves = tile.nx_reverse_interference_graph(
                layer)
            if intra_tile_graph is not None and local_moves:
                graphs_data_for_combine.append(
                    (r_idx, c_idx, tile_h_cells, tile_w_cells, intra_tile_graph, local_moves))

        combined_graph, global_moves = self.combine_nx_graphs(
            graphs_data_for_combine, layer, is_forward_move=False)

        while combined_graph.number_of_nodes() > 0:
            comp_graph = nx.complement(combined_graph)
            indp_nodes = max(nx.find_cliques(comp_graph), key=len, default=[])
            indp_moves_per_tile = {(r_idx, c_idx): []
                                   for (r_idx, c_idx) in self.active_tiles}

            for i_node in indp_nodes:
                anchor_r, anchor_c, _h, _w, local_movement = global_moves[i_node]
                indp_moves_per_tile[(anchor_r, anchor_c)
                                    ].append(local_movement)

            tile_reverse_indices = {
                (row_idx, col_idx): len(self.tiles[row_idx][col_idx].result_json["instructions"]) for (row_idx, col_idx) in self.active_tiles}

            self.process_rev_movement(layer, indp_moves_per_tile)
            self.aod_assignment(tile_reverse_indices)
            combined_graph.remove_nodes_from(indp_nodes)

    def combine_nx_graphs(self,
                          graphs_input: list[tuple[int, int, int, int, nx.Graph, list[Movement]]],
                          layer: int,
                          is_forward_move: bool
                          ) -> tuple[nx.Graph, list[tuple[int, int, int, int, Movement]]]:
        """ Merge per-tile conflict graphs into one graph with inter-tile conflict edges. """
        graph_data = [g for _, _, _, _, g,
                      _ in graphs_input]
        if not graph_data:
            return nx.Graph(), []

        combined_graph = nx.disjoint_union_all(graph_data)
        # Node i of combined_graph is global_move_data[i].
        global_move_data: list[tuple[int, int, int, int, Movement]] = []
        for r_anchor, c_anchor, h_cells, w_cells, _, local_moves_for_tile in graphs_input:
            for local_move in local_moves_for_tile:
                global_move_data.append(
                    (r_anchor, c_anchor, h_cells, w_cells, local_move))

        for i, tm1 in enumerate(global_move_data):
            for j, tm2_data in enumerate(global_move_data):
                if i >= j:
                    continue

                r1_anchor, c1_anchor, h1_cells, w1_cells, local_mov1 = tm1
                r2_anchor, c2_anchor, h2_cells, w2_cells, local_mov2 = tm2_data

                if r1_anchor == r2_anchor and c1_anchor == c2_anchor:
                    continue

                g_mov1 = global_movement(
                    self.config, r1_anchor, c1_anchor, local_mov1)
                g_mov2 = global_movement(
                    self.config, r2_anchor, c2_anchor, local_mov2)

                if max(r1_anchor, r2_anchor) < min(r1_anchor + h1_cells, r2_anchor + h2_cells):
                    if not row_compatible(g_mov1, g_mov2):
                        combined_graph.add_edge(i, j)
                if max(c1_anchor, c2_anchor) < min(c1_anchor + w1_cells, c2_anchor + w2_cells):
                    if not column_compatible(g_mov1, g_mov2):
                        combined_graph.add_edge(i, j)

                if r1_anchor != r2_anchor and c1_anchor != c2_anchor:
                    tile_mov1_for_diag = TileMovement(
                        r1_anchor, c1_anchor, local_mov1)
                    tile_mov2_for_diag = TileMovement(
                        r2_anchor, c2_anchor, local_mov2)
                    if not diagonal_compatible(self.config, self.tiles, tile_mov1_for_diag, tile_mov2_for_diag, layer, is_forward_move):
                        combined_graph.add_edge(i, j)

        return combined_graph, global_move_data

    def process_movement(self, layer: int, indp_moves_per_tile: dict[tuple[int, int], list[Movement]]):
        for (r_idx, c_idx) in self.active_tiles:
            tile = self.tiles[r_idx][c_idx]
            assert (tile)

            tile_moves = indp_moves_per_tile[(r_idx, c_idx)]
            qubits = {move.qubit_index for move in tile_moves}
            tile.process_movement_layer(
                qubits, tile.qubit_mapping[2 * layer], tile.qubit_mapping[2 * layer + 1])

    def process_rev_movement(self, layer: int, indp_moves_per_tile: dict[tuple[int, int], list[Movement]]):
        for (r_idx, c_idx) in self.active_tiles:
            tile = self.tiles[r_idx][c_idx]
            assert (tile)

            if tile.qubit_mapping[2 * layer + 2] is None:
                tile.construct_reverse_layer(
                    len(tile.result_json["instructions"]), tile.qubit_mapping[2 * layer], tile.qubit_mapping[2 * layer + 2])
            else:
                tile_moves = indp_moves_per_tile[(r_idx, c_idx)]
                qubits = {move.qubit_index for move in tile_moves}
                tile.process_movement_layer(
                    qubits, tile.qubit_mapping[2 * layer + 1], tile.qubit_mapping[2 * layer + 2])

    def aod_assignment(self, instr_start_indices: dict[tuple[int, int], int]):
        """ Schedule one batch of moves across all tiles on the first free AOD. """

        # get_duration sets relative sub-instruction times as a side effect, so it runs first.

        durations = {(r, c): [] for (r, c) in self.active_tiles}

        for (r_idx, c_idx) in self.active_tiles:
            tile = self.tiles[r_idx][c_idx]
            assert (tile)

            instr_id_start = instr_start_indices[(r_idx, c_idx)]
            for idx in range(instr_id_start, len(tile.result_json["instructions"])):
                instr = tile.result_json["instructions"][idx]
                if instr["type"] != "rearrangeJob":
                    break
                durations[(r_idx, c_idx)].append(
                    (tile.get_duration(instr), idx))

        start_times = []
        for (r_idx, c_idx), idx in instr_start_indices.items():
            tile = self.tiles[r_idx][c_idx]
            assert (tile)
            instr = tile.result_json["instructions"][idx]
            time_st_i = tile.get_begin_time(idx, instr["dependency"])
            start_times.append(time_st_i)

        aod_end, aod_id = heapq.heappop(self.aod_end_times)
        global_start_time = max(max(start_times), aod_end)

        for (r_idx, c_idx) in self.active_tiles:
            tile = self.tiles[r_idx][c_idx]
            assert (tile)

            for duration, idx in durations[(r_idx, c_idx)]:
                instr = tile.result_json["instructions"][idx]

                begin_time = global_start_time
                end_time = global_start_time + duration

                instr["dependency"]["aod"] = self.aod_dependency[aod_id]
                self.aod_dependency[aod_id] = idx

                instr["begin_time"] = begin_time
                instr["end_time"] = end_time
                instr["aod_id"] = aod_id

                for detail_inst in instr["insts"]:
                    detail_inst["begin_time"] += begin_time
                    detail_inst["end_time"] += begin_time

                tile.result_json["runtime"] = max(
                    tile.result_json["runtime"], end_time)

                heapq.heappush(self.aod_end_times, (end_time, aod_id))

    def rydberg_assignment(self, ryd_instr_start_indices: dict[tuple[int, int], int]):
        global_earliest_start = 0.0
        global_end_time = 0.0

        for (r_idx, c_idx), start_idx in ryd_instr_start_indices.items():
            tile = self.tiles[r_idx][c_idx]
            assert (tile)

            dep = tile.result_json["instructions"][start_idx]["dependency"]
            rydb_begin_time = tile.get_begin_time(start_idx, dep)
            global_earliest_start = max(global_earliest_start, rydb_begin_time)

        global_end_time = global_earliest_start + self.config.time_rydberg
        self.rydberg_end_time = global_end_time

        for (r_idx, c_idx), start_idx in ryd_instr_start_indices.items():
            tile = self.tiles[r_idx][c_idx]
            assert (tile)

            local_start_time = global_end_time

            for idx in range(start_idx, len(tile.result_json["instructions"])):
                instr = tile.result_json["instructions"][idx]
                if instr["type"] == "rearrangeJob":
                    break
                if instr["type"] == "rydberg":
                    instr["begin_time"] = global_earliest_start
                    instr["end_time"] = global_end_time
                    tile.update_runtime(global_end_time)
                if instr["type"] == "row1qGate":
                    aod_begin, aod_id = heapq.heappop(self.aod_end_times)

                    # Row 1q gates occupy an AOD.
                    instr["begin_time"] += max(local_start_time, aod_begin)
                    local_start_time += instr["end_time"]
                    instr["end_time"] = local_start_time

                    heapq.heappush(self.aod_end_times, (local_start_time, aod_id))
                    self.aod_dependency[aod_id] = idx
                    tile.update_runtime(local_start_time)
                else:
                    # Individual 1q gates are not synchronised across tiles.
                    instr["begin_time"] = local_start_time
                    local_end_time = local_start_time + \
                        len(instr["gates"]) * tile.architecture.time_1qGate
                    instr["end_time"] = local_end_time
                    tile.update_runtime(local_end_time)
                    local_start_time = local_end_time

    def process_gates(self, layer: int):
        gate_instrs = {(r, c): 0 for (r, c) in self.active_tiles}
        for (r_idx, c_idx) in self.active_tiles:
            tile = self.tiles[r_idx][c_idx]
            assert (tile)
            initial_indx = tile.process_2q_gate_layer(
                layer, tile.qubit_mapping[2 * layer + 1])
            if self.config.no_row1q_gates:
                tile.process_1q_gate_layer(
                    layer, tile.qubit_mapping[2 * layer + 1])

            if initial_indx:
                gate_instrs[(r_idx, c_idx)] = initial_indx

        if not self.config.no_row1q_gates:
            self.instr_builder.row_1q_gate_instruction(
                self.tiles, layer, 0.0)  # start time is set in rydberg_assignment

        return gate_instrs

    def compile(self):
        scheduling_start = time.perf_counter()

        active_indices = [i for i, tile in enumerate(self.tiles_to_place) if tile is not None]
        active_tiles = [self.tiles_to_place[i] for i in active_indices]

        if len(active_tiles) <= 1:
            processed_tiles = [_schedule_and_place_tile(t) for t in active_tiles]
        else:
            with get_context("fork").Pool(processes=min(len(active_tiles), os.cpu_count() or 1)) as pool:
                processed_tiles = pool.map(_schedule_and_place_tile, active_tiles)

        for i, tile in zip(active_indices, processed_tiles):
            self.tiles_to_place[i] = tile
        self.timing["scheduling"] = time.perf_counter() - scheduling_start

        # Grid placement needs the scheduled tile sizes.
        placement_start = time.perf_counter()
        optim = PlacementOptimiser(self.config, self.tiles_to_place)
        self.tiles = optim.optimise_placement()
        self.timing["placement"] = time.perf_counter() - placement_start

        routing_start = time.perf_counter()
        self.route()
        self.timing["routing"] = time.perf_counter() - routing_start

        logger.info("Total runtimes:")
        for i, row in enumerate(self.tiles):
            for j, tile in enumerate(row):
                if tile:
                    logger.info(
                        f"Tile ({tile.source_name}) at ({i},{j}): {tile.result_json["runtime"]} ms")

    def set_programs(self, tiles: list[Tile]):
        if len(tiles) > self.config.grid_rows * self.config.grid_cols:
            logger.warning(
                f"{len(tiles)} tiles provided but grid only has {self.config.grid_rows * self.config.grid_cols} spaces.")

        self.tiles_to_place.clear()

        for tile in tiles:
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
            tile.load_program(tile.source_name)
            self.tiles_to_place.append(tile)

    def write_output(self, output_dir: str) -> list[str]:
        """ Write the output of each tile into the results directory """

        output_files = []

        for i, row in enumerate(self.tiles):
            for j, tile in enumerate(row):
                if tile:
                    filename = os.path.basename(tile.source_name)
                    filename = os.path.splitext(filename)[0] + ".json"
                    if not os.path.exists(output_dir):
                        os.makedirs(output_dir)

                    tile.result_json['tile_width'] = tile.architecture.arch_range[1][0]

                    with open(os.path.join(output_dir, filename), "w+") as f:
                        f.write(json.dumps(tile.result_json))

                    output_files.append(os.path.join(output_dir, filename))

        return output_files
