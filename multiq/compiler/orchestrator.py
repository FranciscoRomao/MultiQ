from zac.ds.architecture import Architecture

import networkx as nx
import logging

from multiq.configuration import MultiQConfig
from multiq.types import Movement, row_compatible, column_compatible, TileMovement

from .tile import Tile
from .builder import InstructionBuilder
from .placement import PlacementOptimiser

logger = logging.getLogger("multiq")


class Orchestrator:
    def __init__(self, arch: Architecture, config: MultiQConfig):
        self.architecture = arch
        self.config: MultiQConfig = config

        # start with placeholders for the tiles. They are created in set_program()
        self.tiles: list[list[Tile | None]] = [
            [None for _ in range(self.config.grid_cols)] for _ in range(self.config.grid_rows)]
        self.instr_builder = InstructionBuilder()
        self.tiles_to_place = []

        # all operations on all tiles are measured according to this global time
        self.global_time = 0.0
        self.aod_end_time = 0.0  # finish time of currently executing instruction on AoD
        self.rydberg_end_time = 0.0  # finish time of the current/last rydberg operation

        # currently active tiles. Should never refer to "None" tiles
        # (r,c) indices of the active tiles. It refers to the top-left corner of the tile
        self.active_tiles: list[tuple[int, int]] = []

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

        # write_initial_instruction() returns end_time. Global schedule waits till last tile is finished
        self.global_time = max(
            [self.instr_builder.write_initial_instruction(t) for t in active_tile_objs])

        layer: int = 0
        while len(self.active_tiles) > 0:
            self.route_layer(layer)
            layer += 1

        for t_row in self.tiles:
            for t_col in t_row:
                if t_col:
                    t_col.flatten_rearrangment_instruction()

    def route_layer(self, layer: int):
        graphs: list[tuple[int, int, nx.Graph, list]] = []

        for (r_idx, c_idx) in self.active_tiles:
            tile = self.tiles[r_idx][c_idx]
            assert (tile)

            if layer >= len(tile.gate_scheduling):
                self.active_tiles.remove((r_idx, c_idx))
                logger.info(
                    f"Removing tile_id ({r_idx}, {c_idx}) as it has finished")
                continue
            graph, moves = tile.nx_interference_graph(layer)
            if graph:  # Ensure graph is not None
                graphs.append((r_idx, c_idx, graph, moves))

        if len(graphs) == 0:
            return

        # we now shadow the old graphs list with the combined graph
        graph, global_moves = self.combine_nx_graphs(
            graphs, layer, is_forward_move=True)

        while graph.number_of_nodes() > 0:
            comp_graph = nx.complement(graph)
            indp_nodes = max(nx.find_cliques(comp_graph), key=len, default=[])
            logger.info(
                f"There are {len(indp_nodes)} indp nodes of {len(comp_graph.nodes)}. Removing them.")
            indp_moves_per_tile = {(r_idx, c_idx): []
                                   for (r_idx, c_idx) in self.active_tiles}

            # partition the independent set by tile
            for i_node in indp_nodes:
                tile_move: TileMovement = global_moves[i_node]
                indp_moves_per_tile[(tile_move.row_idx, tile_move.col_idx)].append(
                    tile_move.movement)

            tile_reverse_indices = {
                (row_idx, col_idx): len(self.tiles[row_idx][col_idx].result_json["instructions"]) for (row_idx, col_idx) in self.active_tiles}
            self.process_movement(layer, indp_moves_per_tile)
            logger.info("Processed movements")
            self.aod_assignment(tile_reverse_indices)
            graph.remove_nodes_from(indp_nodes)

        # add gate layers
        rydberg_instrs = self.process_gates(layer)
        self.rydberg_assignment(rydberg_instrs)
        graphs.clear()

        # gather reverse movements
        graphs: list[tuple[int, int, nx.Graph, list]] = []
        global_moves: list[TileMovement] = []

        for (r_idx, c_idx) in self.active_tiles:
            tile = self.tiles[r_idx][c_idx]

            graph, moves = tile.nx_reverse_interference_graph(layer)
            if graph:
                graphs.append((r_idx, c_idx, graph, moves))

        # shadow graphs list again
        combined_graph, global_moves = self.combine_nx_graphs(
            graphs, layer, is_forward_move=False)
        while combined_graph.number_of_nodes() > 0:
            comp_graph = nx.complement(combined_graph)
            indp_nodes = max(nx.find_cliques(comp_graph), key=len, default=[])
            indp_moves_per_tile = {(r_idx, c_idx): []
                                   for (r_idx, c_idx) in self.active_tiles}

            for i_node in indp_nodes:
                (row_idx, col_idx, movement) = global_moves[i_node]
                indp_moves_per_tile[(row_idx, col_idx)].append(
                    movement)

            tile_reverse_indices = {
                (row_idx, col_idx): len(self.tiles[row_idx][col_idx].result_json["instructions"]) for (row_idx, col_idx) in self.active_tiles}

            self.process_rev_movement(layer, indp_moves_per_tile)
            self.aod_assignment(tile_reverse_indices)
            combined_graph.remove_nodes_from(indp_nodes)

    def combine_nx_graphs(self, graphs: list[tuple[int, int, nx.Graph, list[Movement]]], layer: int, is_forward_move: bool) -> tuple[nx.Graph, list[TileMovement]]:
        """ Take a list of (tile_id, conflict graph, movement list) and combine it into a single graph """
        graph_data: nx.Graph = [g for _, _, g, _ in graphs]
        if not graph_data:
            return nx.Graph(), []

        # nodes become [0,...,len(g_1),...,len(g_2),...]
        combined_graph = nx.disjoint_union_all(graph_data)
        # combined_graph's nodes index into this list
        global_move_data: list[TileMovement] = []

        for r_idx, c_idx, _, moves_for_tile in graphs:
            for move in moves_for_tile:
                global_move_data.append(TileMovement(r_idx, c_idx, move))

        for i, tm1 in enumerate(global_move_data):
            for j, tm2 in enumerate(global_move_data):
                if i >= j:  # Avoid self-loops and duplicate checks
                    continue

                r_idx_1, c_idx_1, mov1 = tm1.row_idx, tm1.col_idx, tm1.movement
                r_idx_2, c_idx_2, mov2 = tm2.row_idx, tm2.col_idx, tm2.movement

                if r_idx_1 == r_idx_2 and c_idx_1 != c_idx_2:
                    if not row_compatible(mov1, mov2):
                        combined_graph.add_edge(i, j)
                if c_idx_1 == c_idx_2 and r_idx_1 != r_idx_2:
                    if not column_compatible(mov1, mov2):
                        combined_graph.add_edge(i, j)
                if r_idx_1 != r_idx_2 and c_idx_1 != c_idx_2:
                    if not self.diagonal_compatible(tm1, tm2, layer, is_forward_move):
                        combined_graph.add_edge(i, j)

        return combined_graph, global_move_data

    def global_movement(self, r_idx, c_idx, m: Movement) -> Movement:
        """ Convert a tile-local movement into a QPU-global movement """
        y_offset = c_idx * self.config.physical_grid_width
        x_offset = r_idx * self.config.physical_grid_width
        return Movement(m.qubit_index, m.start_x + x_offset, m.end_x + x_offset, m.start_y + y_offset, m.end_y + y_offset)

    def diagonal_compatible(self, tm1: TileMovement, tm2: TileMovement, layer: int, is_forward_move: bool) -> bool:
        """ Check if two movements (from different, diagonal tiles) are compatible
            with the other ones on the QPU.
        Returns True if compatible, False if there's a conflict.
        """
        epsilon = 1e-9  # For floating point comparisons

        # 1. Get global start coordinates for tm1 and tm2 movements
        global_m1 = self.global_movement(
            tm1.row_idx, tm1.col_idx, tm1.movement)
        global_m2 = self.global_movement(
            tm2.row_idx, tm2.col_idx, tm2.movement)

        # 2. Identify intersection points (these are in global coordinates)
        # Intersection 1: X from m1's start, Y from m2's start
        intersect1_gx, intersect1_gy = global_m1.start_x, global_m2.start_y
        # Intersection 2: X from m2's start, Y from m1's start
        intersect2_gx, intersect2_gy = global_m2.start_x, global_m1.start_y

        intersections_to_check = [
            (intersect1_gx, intersect1_gy), (intersect2_gx, intersect2_gy)]

        # Determine the correct mapping index based on the movement phase
        mapping_idx = 2 * layer if is_forward_move else 2 * layer + 1

        for gx, gy in intersections_to_check:
            # 3a. Find which tile (target_tile_r, target_tile_c) contains this global point (gx, gy)
            for r_target in range(self.config.grid_rows):
                for c_target in range(self.config.grid_cols):
                    target_tile = self.tiles[r_target][c_target]
                    if target_tile is None:
                        continue

                    # Calculate tile's origin in global coordinates (consistent with global_movement)
                    tile_origin_global_x = r_target * self.config.physical_grid_width
                    tile_origin_global_y = c_target * self.config.physical_grid_width

                    # Convert global intersection point to local coordinates within this target_tile
                    local_x_in_target = gx - tile_origin_global_x
                    local_y_in_target = gy - tile_origin_global_y

                    arch = target_tile.architecture

                    # Check if the local coordinates are within the tile's architecture boundaries
                    if not (arch.arch_range[0][0] <= local_x_in_target < arch.arch_range[1][0] and
                            arch.arch_range[0][1] <= local_y_in_target < arch.arch_range[1][1]):
                        continue  # Intersection is not in this tile

                    # 3b. Check qubit_mapping for the target_tile at the determined mapping_idx
                    if mapping_idx >= len(target_tile.qubit_mapping) or \
                       target_tile.qubit_mapping[mapping_idx] is None:
                        # Mapping not defined for this tile at this stage, so no conflict from it.
                        continue

                    qubit_physical_locations = target_tile.qubit_mapping[mapping_idx]
                    for _, q_slm_pos_tuple in enumerate(qubit_physical_locations):
                        if q_slm_pos_tuple is None:  # Qubit not mapped
                            continue

                        q_local_x, q_local_y = target_tile.architecture.exact_SLM_location(
                            q_slm_pos_tuple[0], q_slm_pos_tuple[1], q_slm_pos_tuple[2]
                        )
                        if abs(q_local_x - local_x_in_target) < epsilon and \
                           abs(q_local_y - local_y_in_target) < epsilon:
                            return False  # Conflict: qubit found at intersection
        return True

    def process_movement(self, layer: int, indp_moves_per_tile: dict[tuple[int, int], list[Movement]]):
        # process the instructions on the tile level
        for (r_idx, c_idx) in self.active_tiles:
            tile = self.tiles[r_idx][c_idx]
            assert (tile)

            tile_moves = indp_moves_per_tile[(r_idx, c_idx)]
            qubits = {move.qubit_index for move in tile_moves}
            tile.process_movement_layer(
                qubits, tile.qubit_mapping[2 * layer], tile.qubit_mapping[2 * layer + 1])

    def process_rev_movement(self, layer: int, indp_moves_per_tile: dict[tuple[int, int], list[Movement]]):
        # process the instructions on the tile level

        for (r_idx, c_idx) in self.active_tiles:
            tile = self.tiles[r_idx][c_idx]
            assert (tile)

            if tile.qubit_mapping[2 * layer + 2] is None:
                tile.construct_reverse_layer(
                    # None
                    len(tile.result_json["instructions"]), tile.qubit_mapping[2 * layer], tile.qubit_mapping[2 * layer + 2])
            else:
                tile_moves = indp_moves_per_tile[(r_idx, c_idx)]
                qubits = {move.qubit_index for move in tile_moves}
                tile.process_movement_layer(
                    qubits, tile.qubit_mapping[2 * layer + 1], tile.qubit_mapping[2 * layer + 2])

    def aod_assignment(self, instr_start_indices: dict[tuple[int, int], int]):
        """ 
            This is the central scheduler for each batch of operations across the multiple tiles.
        """

        # AoD assignment phase
        # 1. query each tile for begin time time_s_i of instruction id_layer_start (get_begin_time)
        # 2. start_time = max({time_s_i | tiles}, aod_end_time)
        # 3. aod_assignment for each tile with unified start_time
        # 4. end_time = max({time_e_i | tiles})

        # Annoyingly, we need to calculate the durations first. This is because
        # get_duration updates the relative begin and end times of the subinstructions
        # as a side effect.
        # durations = [[] for _ in range(len(self.active_tiles))]

        durations = {(r, c): [] for (r, c) in self.active_tiles}

        for (r_idx, c_idx) in self.active_tiles:
            tile = self.tiles[r_idx][c_idx]
            assert (tile)

            instr_id_start = instr_start_indices[(r_idx, c_idx)]
            # get durations of move operations
            for idx in range(instr_id_start, len(tile.result_json["instructions"])):
                instr = tile.result_json["instructions"][idx]
                if instr["type"] != "rearrangeJob":
                    # we have reached the gate operations
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

        global_start_time = max(max(start_times), self.aod_end_time)

        for (r_idx, c_idx) in self.active_tiles:
            tile = self.tiles[r_idx][c_idx]
            assert (tile)

            for duration, idx in durations[(r_idx, c_idx)]:
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

    def rydberg_assignment(self, ryd_instr_start_indices: dict[tuple[int, int], int]):
        global_earliest_start = 0.0
        global_end_time = 0.0

        # find out the earliest time the global pulse can start
        for (r_idx, c_idx), start_idx in ryd_instr_start_indices.items():
            tile = self.tiles[r_idx][c_idx]
            assert (tile)

            dep = tile.result_json["instructions"][start_idx]["dependency"]
            rydb_begin_time = tile.get_begin_time(start_idx, dep)
            global_earliest_start = max(global_earliest_start, rydb_begin_time)

        global_end_time = global_earliest_start + self.architecture.time_rydberg
        # update global rydberg busy time
        self.rydberg_end_time = global_end_time

        # assign times to instructions
        for (r_idx, c_idx), start_idx in ryd_instr_start_indices.items():
            tile = self.tiles[r_idx][c_idx]
            assert (tile)

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
        gate_instrs = {(r, c): 0 for (r, c) in self.active_tiles}
        for (r_idx, c_idx) in self.active_tiles:
            tile = self.tiles[r_idx][c_idx]
            assert (tile)
            initial_indx = tile.process_gate_layer(
                layer, tile.qubit_mapping[2 * layer + 1])
            if initial_indx:
                gate_instrs[(r_idx, c_idx)] = initial_indx

        return gate_instrs

    # def parse_setting(self, setting: dict):
    #     self.config = MultiQConfig.from_config(setting)

    def compile(self):
        # gate shceduling and placement are done per-tile with no cross-tile considerations
        for tile in self.tiles_to_place:
            if tile is None:
                continue
            # gate scheduling with graph colouring
            tile.scheduling()
            tile.collect_reuse_qubit()
            tile.place_qubit_initial()
            tile.place_qubit_intermedeiate()

        # Only once we have scheduling info, do we place on the tile grid
        optim = PlacementOptimiser(self.config, self.tiles_to_place)
        self.tiles = optim.optimise_placement()

        # Routing must be done globally
        self.route()

        logger.info("Total runtimes:")
        for i, row in enumerate(self.tiles):
            for j, tile in enumerate(row):
                if tile:
                    logger.info(
                        f"Tile ({tile.source_name}) at ({i},{j}): {tile.result_json["runtime"]} ms")

    def set_programs(self, source_files: list[str]):
        if len(source_files) > self.config.grid_rows * self.config.grid_cols:
            logger.warning(
                f"{len(source_files)} source files provided but grid only has {self.config.grid_rows * self.config.grid_cols} spaces.")

        self.tiles_to_place.clear()

        for source in source_files:
            tile = Tile(self.config)
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
            tile.load_program(source)
            self.tiles_to_place.append(tile)
