import logging
import random
import math

import networkx as nx

from .tile import Tile
from .movement import row_compatible, column_compatible, diagonal_compatible, global_movement

from multiq.types import Movement, TileMovement
from multiq.configuration import MultiQConfig

logger = logging.getLogger("multiq")


class PlacementOptimiser:
    def __init__(self, config: MultiQConfig,  tiles_to_place: list[Tile]):
        """ Create a new tile placement optimiser.

        Args:
            grid_rows (int): Grid rows.
            grid_cols (int): Grid columns.
            tiles_to_place (list[Tile]): The tiles to place. Must not contain any None objects.
        """
        self.config = config
        self.grid_cols = config.grid_cols
        self.grid_rows = config.grid_rows
        self.tiles_to_place = tiles_to_place

    def _get_tile_width_in_cells(self, tile: Tile | None) -> int:
        if tile is None:
            return 1          
        return max(1, tile.width)

    def _can_place_tile(self, placement: list[list[Tile | None]], tile: Tile, r_root: int, c_root: int) -> bool:
        """Checks if a tile can be placed at (r_root, c_root) without overlaps."""
        tile_w = self._get_tile_width_in_cells(tile)

        if not (0 <= r_root < self.grid_rows):  # Row bounds
            return False
        if not (0 <= c_root < self.grid_cols and c_root + tile_w <= self.grid_cols):  # Column bounds
            return False

        for c_offset in range(tile_w):
            if placement[r_root][c_root + c_offset] is not None:
                return False  # Collision
        return True

    def _place_tile(self, placement: list[list[Tile | None]], tile: Tile, r_root: int, c_root: int):
        """Places a tile at (r_root, c_root), marking its full extent."""
        tile_w = self._get_tile_width_in_cells(tile)
        placement[r_root][c_root] = tile
        # Mark subsequent cells covered by this tile as None
        for c_offset in range(1, tile_w):
            if c_root + c_offset < self.grid_cols:
                placement[r_root][c_root + c_offset] = None

    def _clear_cells_for_tile(self, placement: list[list[Tile | None]], r_root: int, c_root: int, tile_w: int):
        """Clears all cells that would be occupied by a tile of width tile_w at (r_root, c_root)."""
        if not (0 <= r_root < self.grid_rows):
            return
        for c_offset in range(tile_w):
            if 0 <= c_root + c_offset < self.grid_cols:
                placement[r_root][c_root + c_offset] = None

    def count_inter_tile_conflicts(
        self,
        placement,
        # move_graphs: list of (anchor_r, anchor_c, tile_h_cells, tile_w_cells, intra_tile_graph, list_of_local_moves)
        move_graphs: list[tuple[int, int, int, int, nx.Graph, list[Movement]]],
        layer: int
    ) -> int:
        """
        Counts potential inter-tile movement conflicts based on placement.
        Assumes Movement objects contain local coordinates.
        """
        if not move_graphs:
            return 0

        # Stores (global_node_idx, r_anchor, c_anchor, h_cells, w_cells, local_movement_obj)
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

                # Skip if moves are from the same tile
                if r1_anchor == r2_anchor and c1_anchor == c2_anchor:
                    continue

                # Translate local movements to global physical coordinates
                # Assumes tile's local (0,0) physical origin corresponds to the
                # global physical origin of its anchor cell (r_anchor, c_anchor).
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
                # Check row conflict: Do their row spans (in grid cells) overlap?
                if max(r1_anchor, r2_anchor) < min(r1_anchor + h1_cells, r2_anchor + h2_cells):
                    if not row_compatible(g_mov1, g_mov2): 
                        current_pair_conflict = True
                
                # Check column conflict: Do their column spans (in grid cells) overlap?
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
        """
        Calculates a contention score for a given placement. Considers all layers of movements.
        Placement stores tiles at their top-left anchor.
        """
        total_contention_score = 0.0
        max_layers = 0

        # get the maximum number of layers across all tiles in this placement
        for r_idx, row_tiles in enumerate(placement):
            for c_idx, tile in enumerate(row_tiles):
                if tile and tile.gate_scheduling:
                    max_layers = max(max_layers, len(tile.gate_scheduling)) # tile is at its anchor

        if max_layers == 0:
            return 0.0  # no layers => no contention

        for layer_to_evaluate in range(max_layers):
            # (anchor_r, anchor_c, h_cells, w_cells, intra_tile_graph, list_of_local_moves)
            graphs_for_this_layer: list[tuple[int, int, int, int, nx.Graph, list[Movement]]] = []
            for r_idx, row_tiles in enumerate(placement):
                for c_idx, tile in enumerate(row_tiles):
                    if tile: # tile is at its anchor (r_idx, c_idx)
                        if tile.gate_scheduling and layer_to_evaluate < len(tile.gate_scheduling):
                            # nx_interference_graph should NOT take coord_offset.
                            # It returns local moves.
                            graph, local_moves = tile.nx_interference_graph(layer_to_evaluate)
                            if graph is not None and local_moves:
                                # Pass tile's anchor (r_idx, c_idx) and its dimensions in cells
                                # tile.height is assumed to be 1 cell for QPU rows.
                                # tile.width is width in cells.
                                graphs_for_this_layer.append(
                                    (r_idx, c_idx, tile.height, tile.width, graph, local_moves))

            if graphs_for_this_layer:
                layer_contention = self.count_inter_tile_conflicts(placement,
                    graphs_for_this_layer, layer_to_evaluate)
                total_contention_score += float(layer_contention)

        return total_contention_score

    def generate_initial_placement(self) -> list[list[Tile | None]]:
        """
        Generates an initial placement using a First Fit Decreasing (FFD) heuristic.
        This is a common and effective approach for bin packing problems.
        """
        current_placement: list[list[Tile | None]] = [
            [None for _ in range(self.grid_cols)] for _ in range(self.grid_rows)
        ]

        # Sort tiles in descending order of their width (in grid cells).
        tiles_to_assign = sorted(
            self.tiles_to_place,
            key=lambda t: self._get_tile_width_in_cells(t),
            reverse=True
        )

        num_actually_placed = 0
        for tile in tiles_to_assign:
            placed_this_tile = False
            # Try to place the tile in the first available spot
            for r_idx in range(self.grid_rows):
                for c_idx in range(self.grid_cols):
                    if self._can_place_tile(current_placement, tile, r_idx, c_idx):
                        self._place_tile(current_placement, tile, r_idx, c_idx)
                        # Store anchor coordinates in the tile object for later reference.
                        tile.r_coord = r_idx
                        tile.c_coord = c_idx
                        placed_this_tile = True
                        num_actually_placed += 1
                        break  # Move to the next tile
                if placed_this_tile:
                    break  # Move to the next tile

            if not placed_this_tile:
                logger.warning(
                    f"Could not place tile ({tile.source_name}, width_cells: {self._get_tile_width_in_cells(tile)}).")

        if num_actually_placed < len(self.tiles_to_place):
            logger.warning(
                f"Initial placement: Only placed {num_actually_placed}/{len(self.tiles_to_place)} tiles due to space constraints.")
        return current_placement

    def get_neighbour_placement(self, current_placement: list[list[Tile | None]]) -> list[list[Tile | None]]:
        """Generates a neighbour placement by swapping two items (tiles or None)."""
        new_placement = [row[:]
                         for row in current_placement]  # Start with a copy

        # List of dicts: {'r': r, 'c': c, 'tile': tile_obj_or_None, 'w': width}
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
                else:  # It's a None cell, representing an empty slot of width 1
                    candidate_items_for_swap.append(
                        {'r': r_idx, 'c': c_idx, 'tile': None, 'w': 1})
                    c_idx += 1

        if len(candidate_items_for_swap) < 2:
            return new_placement  # Not enough distinct items to swap

        # Pick two distinct items to try and swap
        idx1, idx2 = random.sample(range(len(candidate_items_for_swap)), 2)

        item1_data = candidate_items_for_swap[idx1]
        item2_data = candidate_items_for_swap[idx2]

        r1, c1, tile1, w1 = item1_data['r'], item1_data['c'], item1_data['tile'], item1_data['w']
        r2, c2, tile2, w2 = item2_data['r'], item2_data['c'], item2_data['tile'], item2_data['w']

        # Create a temporary board state where both items' original spots are fully cleared
        # Use a copy of new_placement for checks
        board_after_clearing_both = [row[:] for row in new_placement]
        self._clear_cells_for_tile(board_after_clearing_both, r1, c1, w1)
        self._clear_cells_for_tile(board_after_clearing_both, r2, c2, w2)

        # Check if tile1 can be placed at item2's original location (r2, c2)
        check1_possible = (tile1 is None) or self._can_place_tile(
            board_after_clearing_both, tile1, r2, c2)

        if not check1_possible:
            # Swap invalid, return original copy
            return [row[:] for row in current_placement]

        # If check1 is possible, simulate placing tile1 for the next check
        board_for_check2 = [row[:] for row in board_after_clearing_both]
        if tile1:
            self._place_tile(board_for_check2, tile1, r2, c2)

        # Check if tile2 can be placed at item1's original location (r1, c1)
        check2_possible = (tile2 is None) or self._can_place_tile(
            board_for_check2, tile2, r1, c1)

        if check2_possible:  # Both moves are valid, apply to new_placement
            # Perform the swap on the actual new_placement (which started as a copy of current_placement)
            self._clear_cells_for_tile(new_placement, r1, c1, w1)
            self._clear_cells_for_tile(new_placement, r2, c2, w2)
            if tile2:
                self._place_tile(new_placement, tile2, r1, c1)
                tile2.r_coord, tile2.c_coord = r1, c1 # Update tile's own anchor
            if tile1:
                self._place_tile(new_placement, tile1, r2, c2)
                tile1.r_coord, tile1.c_coord = r2, c2 # Update tile's own anchor

            return new_placement
        else:
            # Swap is not fully valid, return a copy of the original state
            return [row[:] for row in current_placement]

    def optimise_placement(self, iterations: int = 1000, initial_temp: float = 10.0, cooling_rate: float = 0.995) -> list[list[Tile | None]]:
        """
        Optimises tile placement using Simulated Annealing. Assumes tiles in self.tiles_to_place are already scheduled.
        """

        if not self.tiles_to_place:
            logger.info("No tiles provided to PlacementOptimiser.")
            return [[None for _ in range(self.grid_cols)] for _ in range(self.grid_rows)]

        current_placement = self.generate_initial_placement()
        current_contention = self.calculate_contention(current_placement)

        best_placement = [row[:] for row in current_placement]
        best_contention = current_contention

        temp = initial_temp

        logger.info(
            f"Starting placement optimisation. Initial contention: {current_contention:.2f} (target {len(self.tiles_to_place)} tiles)")

        for i in range(iterations):
            # Pass a copy of current_placement to get_neighbour_placement,
            # so current_placement is only updated if the move is accepted.
            neighbour_p = self.get_neighbour_placement(current_placement)
            contention = self.calculate_contention(neighbour_p)

            acceptance_probability = 0.0
            if contention < current_contention:
                acceptance_probability = 1.0
            elif temp > 1e-6:  # to avoid division by zero or extreme values
                delta_energy = contention - current_contention
                acceptance_probability = math.exp(-delta_energy / temp)

            if random.random() < acceptance_probability:
                current_placement = neighbour_p  # Accept the new placement
                current_contention = contention
                if current_contention < best_contention:
                    best_placement = [row[:]
                                      # Store a copy
                                      for row in current_placement]
                    best_contention = current_contention

            temp *= cooling_rate
            if i > 0 and i % (iterations // 20) == 0:
                # log progress periodically
                logger.info(
                    f"Placement optimiser iteration {i}: Temp={temp:.4f}, current contention={current_contention:.2f}, best contention={best_contention:.2f}")

        logger.info(
            f"Finished placement optimisation. Best contention: {best_contention:.2f}")
        return best_placement
