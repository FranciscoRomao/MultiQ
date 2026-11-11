import logging
import random
import math

import networkx as nx

from .tile import Tile
from .movement import row_compatible, column_compatible, diagonal_compatible

from multiq.types import Movement, TileMovement
from multiq.configuration import MultiQConfig

logger = logging.getLogger("multiq")


class _OccupiedMarker:
    """Falsy marker for grid cells covered by a wide tile but not holding its root."""
    def __bool__(self) -> bool:
        return False

    def __repr__(self) -> str:
        return "<occupied>"


_OCCUPIED = _OccupiedMarker()


class PlacementOptimiser:
    def __init__(self, config: MultiQConfig,  tiles_to_place: list[Tile]):
        """ tiles_to_place must not contain None. """
        self.config = config
        self.grid_cols = config.grid_cols
        self.grid_rows = config.grid_rows
        self.tiles_to_place = tiles_to_place

    def _get_tile_width_in_cells(self, tile: Tile | None) -> int:
        if tile is None:
            return 1          
        return max(1, tile.width)

    def _can_place_tile(self, placement: list[list[Tile | None]], tile: Tile, r_root: int, c_root: int) -> bool:
        tile_w = self._get_tile_width_in_cells(tile)

        if not (0 <= r_root < self.grid_rows):
            return False
        if not (0 <= c_root < self.grid_cols and c_root + tile_w <= self.grid_cols):
            return False

        for c_offset in range(tile_w):
            if placement[r_root][c_root + c_offset] is not None:
                return False
        return True

    def _place_tile(self, placement: list[list[Tile | None]], tile: Tile, r_root: int, c_root: int):
        tile_w = self._get_tile_width_in_cells(tile)
        placement[r_root][c_root] = tile
        for c_offset in range(1, tile_w):
            if c_root + c_offset < self.grid_cols:
                placement[r_root][c_root + c_offset] = _OCCUPIED

    def _clear_cells_for_tile(self, placement: list[list[Tile | None]], r_root: int, c_root: int, tile_w: int):
        if not (0 <= r_root < self.grid_rows):
            return
        for c_offset in range(tile_w):
            if 0 <= c_root + c_offset < self.grid_cols:
                placement[r_root][c_root + c_offset] = None

    def count_inter_tile_conflicts(
        self,
        placement,
        move_graphs: list[tuple[int, int, int, int, nx.Graph, list[Movement]]],
        layer: int
    ) -> int:
        """ Count inter-tile move conflicts, with moves given in tile-local coordinates. """
        if not move_graphs:
            return 0

        all_moves_details = [] 
        node_offset = 0
        for r_anchor, c_anchor, h_cells, w_cells, graph, local_moves in move_graphs:
            for i, local_move_obj in enumerate(local_moves):
                all_moves_details.append(
                    (node_offset + i, r_anchor, c_anchor, h_cells, w_cells, local_move_obj))
            node_offset += graph.number_of_nodes()

        inter_tile_conflict_count = 0
        for i in range(len(all_moves_details)):
            _global_idx1, r1_anchor, c1_anchor, h1_cells, w1_cells, local_mov1 = all_moves_details[i]
            for j in range(i + 1, len(all_moves_details)):
                _global_idx2, r2_anchor, c2_anchor, h2_cells, w2_cells, local_mov2 = all_moves_details[j]

                if r1_anchor == r2_anchor and c1_anchor == c2_anchor:
                    continue

                # A tile's local origin is the physical origin of its anchor cell.
                g_mov1 = Movement(
                    local_mov1.qubit_index,
                    local_mov1.start_x + c1_anchor * self.config.physical_cell_width_um,
                    local_mov1.end_x   + c1_anchor * self.config.physical_cell_width_um,
                    local_mov1.start_y + r1_anchor * self.config.physical_cell_height_um,
                    local_mov1.end_y   + r1_anchor * self.config.physical_cell_height_um
                )
                g_mov2 = Movement(
                    local_mov2.qubit_index,
                    local_mov2.start_x + c2_anchor * self.config.physical_cell_width_um,
                    local_mov2.end_x   + c2_anchor * self.config.physical_cell_width_um,
                    local_mov2.start_y + r2_anchor * self.config.physical_cell_height_um,
                    local_mov2.end_y   + r2_anchor * self.config.physical_cell_height_um
                )

                current_pair_conflict = False
                if max(r1_anchor, r2_anchor) < min(r1_anchor + h1_cells, r2_anchor + h2_cells):
                    if not row_compatible(g_mov1, g_mov2): 
                        current_pair_conflict = True
                
                if max(c1_anchor, c2_anchor) < min(c1_anchor + w1_cells, c2_anchor + w2_cells): 
                    if not column_compatible(g_mov1, g_mov2): 
                        current_pair_conflict = True

                tile_mov1_for_diag = TileMovement(
                    r1_anchor, c1_anchor, local_mov1)
                tile_mov2_for_diag = TileMovement(
                    r2_anchor, c2_anchor, local_mov2)
                if not diagonal_compatible(self.config, placement, tile_mov1_for_diag, tile_mov2_for_diag, layer, True):
                    current_pair_conflict = True

                inter_tile_conflict_count += (1 if current_pair_conflict else 0)

        return inter_tile_conflict_count

    def calculate_contention(self, placement: list[list[Tile | None]]) -> float:
        """ Number of inter-tile move conflicts summed over all layers. """
        total_contention_score = 0.0
        max_layers = 0

        for r_idx, row_tiles in enumerate(placement):
            for c_idx, tile in enumerate(row_tiles):
                if tile and tile.gate_scheduling:
                    max_layers = max(max_layers, len(tile.gate_scheduling))

        if max_layers == 0:
            return 0.0

        for layer_to_evaluate in range(max_layers):
            graphs_for_this_layer: list[tuple[int, int, int, int, nx.Graph, list[Movement]]] = []
            for r_idx, row_tiles in enumerate(placement):
                for c_idx, tile in enumerate(row_tiles):
                    if tile:
                        if tile.gate_scheduling and layer_to_evaluate < len(tile.gate_scheduling):
                            graph, local_moves = tile.nx_interference_graph(layer_to_evaluate)
                            if graph is not None and local_moves:
                                graphs_for_this_layer.append(
                                    (r_idx, c_idx, tile.height, tile.width, graph, local_moves))

            if graphs_for_this_layer:
                layer_contention = self.count_inter_tile_conflicts(placement,
                    graphs_for_this_layer, layer_to_evaluate)
                total_contention_score += float(layer_contention)

        return total_contention_score

    def generate_initial_placement(self) -> list[list[Tile | None]]:
        """ First Fit Decreasing placement by tile width. """
        current_placement: list[list[Tile | None]] = [
            [None for _ in range(self.grid_cols)] for _ in range(self.grid_rows)
        ]

        tiles_to_assign = sorted(
            self.tiles_to_place,
            key=lambda t: self._get_tile_width_in_cells(t),
            reverse=True
        )

        num_actually_placed = 0
        for tile in tiles_to_assign:
            placed_this_tile = False
            for r_idx in range(self.grid_rows):
                for c_idx in range(self.grid_cols):
                    if self._can_place_tile(current_placement, tile, r_idx, c_idx):
                        self._place_tile(current_placement, tile, r_idx, c_idx)
                        tile.r_coord = r_idx
                        tile.c_coord = c_idx
                        placed_this_tile = True
                        num_actually_placed += 1
                        break
                if placed_this_tile:
                    break

            if not placed_this_tile:
                logger.warning(
                    f"Could not place tile ({tile.source_name}, width_cells: {self._get_tile_width_in_cells(tile)}).")

        if num_actually_placed < len(self.tiles_to_place):
            logger.warning(
                f"Initial placement: Only placed {num_actually_placed}/{len(self.tiles_to_place)} tiles due to space constraints.")
        return current_placement

    def get_neighbour_placement(self, current_placement: list[list[Tile | None]]) -> list[list[Tile | None]]:
        """Swap two random tiles or empty cells if the result is valid."""
        new_placement = [row[:]
                         for row in current_placement]

        candidate_items_for_swap = []
        for r_idx in range(self.grid_rows):
            c_idx = 0
            while c_idx < self.grid_cols:
                cell_content = new_placement[r_idx][c_idx]
                if isinstance(cell_content, Tile):
                    width = self._get_tile_width_in_cells(cell_content)
                    candidate_items_for_swap.append(
                        {'r': r_idx, 'c': c_idx, 'tile': cell_content, 'w': width})
                    c_idx += width
                elif cell_content is None:
                    candidate_items_for_swap.append(
                        {'r': r_idx, 'c': c_idx, 'tile': None, 'w': 1})
                    c_idx += 1
                else:
                    # _OCCUPIED cells are covered by the root tile's entry.
                    c_idx += 1

        if len(candidate_items_for_swap) < 2:
            return new_placement

        idx1, idx2 = random.sample(range(len(candidate_items_for_swap)), 2)

        item1_data = candidate_items_for_swap[idx1]
        item2_data = candidate_items_for_swap[idx2]

        r1, c1, tile1, w1 = item1_data['r'], item1_data['c'], item1_data['tile'], item1_data['w']
        r2, c2, tile2, w2 = item2_data['r'], item2_data['c'], item2_data['tile'], item2_data['w']

        board_after_clearing_both = [row[:] for row in new_placement]
        self._clear_cells_for_tile(board_after_clearing_both, r1, c1, w1)
        self._clear_cells_for_tile(board_after_clearing_both, r2, c2, w2)

        check1_possible = (tile1 is None) or self._can_place_tile(
            board_after_clearing_both, tile1, r2, c2)

        if not check1_possible:
            return [row[:] for row in current_placement]

        board_for_check2 = [row[:] for row in board_after_clearing_both]
        if tile1:
            self._place_tile(board_for_check2, tile1, r2, c2)

        check2_possible = (tile2 is None) or self._can_place_tile(
            board_for_check2, tile2, r1, c1)

        if check2_possible:
            self._clear_cells_for_tile(new_placement, r1, c1, w1)
            self._clear_cells_for_tile(new_placement, r2, c2, w2)
            if tile2:
                self._place_tile(new_placement, tile2, r1, c1)
                tile2.r_coord, tile2.c_coord = r1, c1
            if tile1:
                self._place_tile(new_placement, tile1, r2, c2)
                tile1.r_coord, tile1.c_coord = r2, c2

            return new_placement
        else:
            return [row[:] for row in current_placement]

    def optimise_placement(self, iterations: int = 1000, initial_temp: float = 10.0, cooling_rate: float = 0.995) -> list[list[Tile | None]]:
        """ Simulated annealing over placements; tiles must already be scheduled. """

        if not self.tiles_to_place:
            logger.warning("No tiles provided to PlacementOptimiser.")
            return [[None for _ in range(self.grid_cols)] for _ in range(self.grid_rows)]

        current_placement = self.generate_initial_placement()
        current_contention = self.calculate_contention(current_placement)

        best_placement = [row[:] for row in current_placement]
        best_contention = current_contention

        # With one row, contention does not depend on horizontal order, so annealing cannot help.
        if self.grid_rows == 1:
            logger.info(
                f"Skipping placement SA at grid_rows=1 (contention is invariant to horizontal-only "
                f"reordering). Contention: {current_contention:.2f}")
            return best_placement

        temp = initial_temp

        logger.debug(
            f"Starting placement optimisation. Initial contention: {current_contention:.2f} (target {len(self.tiles_to_place)} tiles)")

        for i in range(iterations):
            neighbour_p = self.get_neighbour_placement(current_placement)
            contention = self.calculate_contention(neighbour_p)

            acceptance_probability = 0.0
            if contention < current_contention:
                acceptance_probability = 1.0
            elif temp > 1e-6:
                delta_energy = contention - current_contention
                acceptance_probability = math.exp(-delta_energy / temp)

            if random.random() < acceptance_probability:
                current_placement = neighbour_p
                current_contention = contention
                if current_contention < best_contention:
                    best_placement = [row[:]
                                      for row in current_placement]
                    best_contention = current_contention

            temp *= cooling_rate
            if i > 0 and i % (iterations // 20) == 0:
                logger.debug(
                    f"Placement optimiser iteration {i}: Temp={temp:.4f}, current contention={current_contention:.2f}, best contention={best_contention:.2f}")

        logger.info(
            f"Finished placement optimisation. Best contention: {best_contention:.2f}")
        return best_placement
