import logging
import random
import math

import networkx as nx

from .tile import Tile
from multiq.types import Movement, row_compatible, column_compatible
from multiq.configuration import MultiQConfig

logger = logging.getLogger("multiq")

class PlacementOptimiser:
    def __init__(self, config: MultiQConfig,  tiles_to_place: list[Tile]):
        """ Create a new tile placement optimiser.

        Args:
            grid_rows (int): Grid rows.
            grid_cols (int): Grid columns.
            tiles_to_place (list[ZacTile]): The tiles to place. Must not contain any None objects.
        """
        self.config = config
        self.grid_cols = config.grid_cols
        self.grid_rows = config.grid_rows # Use grid_rows from config
        
        # Filter out tiles with non-positive width, though _get_tile_grid_width handles 0.
        self.tiles_to_place = [t for t in tiles_to_place if hasattr(t, 'tile_width')]
        if len(self.tiles_to_place) < len(tiles_to_place):
            logger.warning("Some tiles were missing 'tile_width' attribute and were excluded from placement.")

    def _get_tile_grid_width(self, tile: Tile | None) -> int:
        if tile is None:
            return 1 # An empty slot conceptually takes 1 grid column
        # tile.tile_width is assumed to be the number of grid columns it occupies.
        # Ensure it's at least 1.
        return max(1, tile.tile_width if hasattr(tile, 'tile_width') else 1)

    def _can_place_tile(self, placement: list[list[Tile | None]], tile: Tile, r_root: int, c_root: int) -> bool:
        """Checks if a tile can be placed at (r_root, c_root) without overlaps."""
        tile_w = self._get_tile_grid_width(tile)

        if not (0 <= r_root < self.grid_rows): # Row bounds
            return False
        if not (0 <= c_root < self.grid_cols and c_root + tile_w <= self.grid_cols): # Column bounds
            return False

        for c_offset in range(tile_w):
            if placement[r_root][c_root + c_offset] is not None:
                return False # Collision
        return True

    def _place_tile(self, placement: list[list[Tile | None]], tile: Tile, r_root: int, c_root: int):
        """Places a tile at (r_root, c_root), marking its full extent."""
        tile_w = self._get_tile_grid_width(tile)
        placement[r_root][c_root] = tile
        for c_offset in range(1, tile_w): # Mark subsequent cells covered by this tile as None
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
        move_graphs: list[tuple[int, int, nx.Graph, list[Movement]]]
    ) -> int:
        """
        Counts potential inter-tile movement conflicts based on placement.
        move_graphs: list of (tile_row_idx, tile_col_idx, intra_tile_graph, list_of_tile_moves)
        """
        if not move_graphs:
            return 0

        all_moves_details = []
        node_offset = 0
        for r_idx, c_idx, graph, moves in move_graphs:
            for i, move_obj in enumerate(moves):
                # (global_node_idx, tile_r, tile_c, movement_obj)
                all_moves_details.append(
                    (node_offset + i, r_idx, c_idx, move_obj))
            node_offset += graph.number_of_nodes()

        inter_tile_conflict_count = 0
        for i in range(len(all_moves_details)):
            _global_idx1, r_idx_1, c_idx_1, mov1 = all_moves_details[i]
            for j in range(i + 1, len(all_moves_details)):
                _global_idx2, r_idx_2, c_idx_2, mov2 = all_moves_details[j]

                # Skip if moves are from the same tile
                if r_idx_1 == r_idx_2 and c_idx_1 == c_idx_2:
                    continue

                conflict = False
                # Check row conflict: same grid row, different tiles
                if r_idx_1 == r_idx_2:  # c_idx_1 != c_idx_2 is implied by prev check
                    conflict |= not row_compatible(mov1, mov2)
                # Check column conflict: same grid col, different tiles
                elif c_idx_1 == c_idx_2:  # r_idx_1 != r_idx_2 is again implied
                    conflict |= not column_compatible(mov1, mov2)

                inter_tile_conflict_count += (1 if conflict else 0)

        return inter_tile_conflict_count

    def calculate_contention(self, placement: list[list[Tile | None]]) -> float:
        """
        Calculates a contention score for a given placement. Considers all layers of movements.
        """
        total_contention_score = 0.0
        max_layers = 0

        # get the maximum number of layers across all tiles in this placement
        for r_idx, row_tiles in enumerate(placement):
            for c_idx, tile in enumerate(row_tiles):
                if tile and tile.gate_scheduling:
                    max_layers = max(max_layers, len(tile.gate_scheduling))
        
        if max_layers == 0:
            return 0.0 # no layers => no contention

        for layer_to_evaluate in range(max_layers):
            graphs_for_this_layer: list[tuple[int, int, nx.Graph, list[Movement]]] = []
            for r_idx, row_tiles in enumerate(placement):
                for c_idx, tile in enumerate(row_tiles):
                    if tile and tile.gate_scheduling and layer_to_evaluate < len(tile.gate_scheduling):
                        # Calculate the physical offset of the tile's origin in the global grid
                        # Assuming physical_col_width also applies to row height for square physical cells,
                        # or that coordinates are effectively grid-based if physical_col_width is 1.

                        offset_x = c_idx * self.config.physical_grid_width
                        # offset_y = r_idx * self.config.physical_col_width # Or use a specific physical_row_height from config if available
                        coord_offset_val = (offset_x, 0.0)

                        graph, moves = tile.nx_interference_graph(layer_to_evaluate, coord_offset=coord_offset_val)
                        if graph is not None and moves:
                            # (tile_grid_row, tile_grid_col, intra_tile_graph, list_of_tile_moves)
                            graphs_for_this_layer.append((r_idx, c_idx, graph, moves))

            if graphs_for_this_layer:
                layer_contention = self.count_inter_tile_conflicts(graphs_for_this_layer)
                total_contention_score += float(layer_contention)
        
        return total_contention_score

    def generate_initial_placement(self) -> list[list[Tile | None]]:
        """Generates an initial placement (i.e. random fill)."""
        current_placement: list[list[Tile | None]] = [
            [None for _ in range(self.grid_cols)] for _ in range(self.grid_rows)
        ]

        tiles_to_assign = list(self.tiles_to_place)
        random.shuffle(tiles_to_assign) # Also shuffle tiles for more randomness

        num_actually_placed = 0
        for tile_to_be_placed in tiles_to_assign:
            placed_this_tile = False
            
            # Find all valid root positions for the current tile_to_be_placed
            # A valid root (r_idx, c_idx) is one where current_placement[r_idx][c_idx] is None,
            # and the entire span of tile_to_be_placed fits into None cells.
            possible_valid_starts_for_this_tile = []
            for r_idx in range(self.grid_rows):
                c_idx = 0
                while c_idx < self.grid_cols:
                    # If current_placement[r_idx][c_idx] is None, it's a candidate root.
                    # _can_place_tile will verify if the whole span is also None.
                    if current_placement[r_idx][c_idx] is None:
                        if self._can_place_tile(current_placement, tile_to_be_placed, r_idx, c_idx):
                            possible_valid_starts_for_this_tile.append((r_idx, c_idx))
                        c_idx += 1 # Move to the next column to check as a potential root
                    else:
                        # This cell is occupied by an existing tile's root. Skip its entire span.
                        existing_tile_width = self._get_tile_grid_width(current_placement[r_idx][c_idx])
                        c_idx += existing_tile_width
            
            random.shuffle(possible_valid_starts_for_this_tile)

            if possible_valid_starts_for_this_tile:
                r_start, c_start = possible_valid_starts_for_this_tile[0] # Pick the first valid shuffled start
                self._place_tile(current_placement, tile_to_be_placed, r_start, c_start)
                placed_this_tile = True
                num_actually_placed += 1
            
            if not placed_this_tile:
                logger.warning(
                    f"Could not place tile (ID/Name: {tile_to_be_placed.result_json.get('name', 'N/A')}, width: {self._get_tile_grid_width(tile_to_be_placed)}) in initial random placement.")
        
        if num_actually_placed < len(self.tiles_to_place):
             logger.warning(
                f"Initial placement: Placed {num_actually_placed}/{len(self.tiles_to_place)} tiles due to space constraints or ordering.")
        return current_placement

    def get_neighbour_placement(self, current_placement: list[list[Tile | None]]) -> list[list[Tile | None]]:
        """Generates a neighbour placement by swapping two items (tiles or None)."""
        new_placement = [row[:] for row in current_placement] # Start with a copy

        candidate_items_for_swap = [] # List of dicts: {'r': r, 'c': c, 'tile': tile_obj_or_None, 'w': width}
        for r_idx in range(self.grid_rows):
            c_idx = 0
            while c_idx < self.grid_cols:
                cell_content = new_placement[r_idx][c_idx]
                if isinstance(cell_content, Tile):
                    width = self._get_tile_grid_width(cell_content)
                    candidate_items_for_swap.append({'r': r_idx, 'c': c_idx, 'tile': cell_content, 'w': width})
                    c_idx += width
                else: # It's a None cell, representing an empty slot of width 1
                    candidate_items_for_swap.append({'r': r_idx, 'c': c_idx, 'tile': None, 'w': 1})
                    c_idx += 1
        
        if len(candidate_items_for_swap) < 2:
            return new_placement # Not enough distinct items to swap

        # Pick two distinct items to try and swap
        idx1, idx2 = random.sample(range(len(candidate_items_for_swap)), 2)
        
        item1_data = candidate_items_for_swap[idx1]
        item2_data = candidate_items_for_swap[idx2]

        r1, c1, tile1, w1 = item1_data['r'], item1_data['c'], item1_data['tile'], item1_data['w']
        r2, c2, tile2, w2 = item2_data['r'], item2_data['c'], item2_data['tile'], item2_data['w']

        # Create a temporary board state where both items' original spots are fully cleared
        board_after_clearing_both = [row[:] for row in new_placement] # Use a copy of new_placement for checks
        self._clear_cells_for_tile(board_after_clearing_both, r1, c1, w1)
        self._clear_cells_for_tile(board_after_clearing_both, r2, c2, w2)

        # Check if tile1 can be placed at item2's original location (r2, c2)
        check1_possible = (tile1 is None) or self._can_place_tile(board_after_clearing_both, tile1, r2, c2)

        if not check1_possible:
            return [row[:] for row in current_placement] # Swap invalid, return original copy

        # If check1 is possible, simulate placing tile1 for the next check
        board_for_check2 = [row[:] for row in board_after_clearing_both]
        if tile1:
            self._place_tile(board_for_check2, tile1, r2, c2)

        # Check if tile2 can be placed at item1's original location (r1, c1)
        check2_possible = (tile2 is None) or self._can_place_tile(board_for_check2, tile2, r1, c1)

        if check2_possible: # Both moves are valid, apply to new_placement
            # Perform the swap on the actual new_placement (which started as a copy of current_placement)
            self._clear_cells_for_tile(new_placement, r1, c1, w1) 
            self._clear_cells_for_tile(new_placement, r2, c2, w2)
            if tile2: self._place_tile(new_placement, tile2, r1, c1)
            if tile1: self._place_tile(new_placement, tile1, r2, c2)
            return new_placement
        else:
            # Swap is not fully valid, return a copy of the original state
            return [row[:] for row in current_placement]

    def optimise_placement(self, iterations: int = 1000, initial_temp: float = 10.0, cooling_rate: float = 0.995) -> list[list[Tile | None]]:
        """
        Optimises tile placement using Simulated Annealing. Assumes tiles in self.tiles_to_place are already scheduled.
        """

        if not self.tiles_to_place:
            logger.info("No valid tiles to place (e.g. all have zero or undefined width).")
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
                current_placement = neighbour_p # Accept the new placement
                current_contention = contention
                if current_contention < best_contention:
                    best_placement = [row[:] for row in current_placement] # Store a copy
                    best_contention = current_contention

            temp *= cooling_rate
            if i > 0 and i % (iterations // 20) == 0:
                # log progress periodically
                logger.info(
                    f"Placement optimiser iteration {i}: Temp={temp:.4f}, current contention={current_contention:.2f}, best contention={best_contention:.2f}")

        logger.info(
            f"Finished placement optimisation. Best contention: {best_contention:.2f}")
        return best_placement