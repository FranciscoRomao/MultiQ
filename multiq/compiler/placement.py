import logging
import random
import math
import copy

from zac.ds.architecture import Architecture
import networkx as nx

from .tile import ZacTile
from multiq.types import Movement, row_compatible, column_compatible


logger = logging.getLogger("multiq")


class PlacementOptimiser:
    def __init__(self, grid_rows: int, grid_cols: int, tiles_to_place: list[ZacTile]):
        """ Create a new tile placement optimiser.

        Args:
            grid_rows (int): Grid rows.
            grid_cols (int): Grid columns.
            tiles_to_place (list[ZacTile]): The tiles to place. Must not contain any None objects.
        """
        self.grid_rows = grid_rows
        self.grid_cols = grid_cols

        self.tiles_to_place = tiles_to_place
        self.empty_slot_count = grid_rows * \
            grid_cols - len(self.tiles_to_place)

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

    def calculate_contention(self, placement: list[list[ZacTile | None]]) -> float:
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
                        graph, moves = tile.nx_interference_graph(layer_to_evaluate)
                        if graph is not None and moves:
                            # (tile_grid_row, tile_grid_col, intra_tile_graph, list_of_tile_moves)
                            graphs_for_this_layer.append((r_idx, c_idx, graph, moves))

            if graphs_for_this_layer:
                layer_contention = self.count_inter_tile_conflicts(graphs_for_this_layer)
                total_contention_score += float(layer_contention)
        
        return total_contention_score

    def generate_initial_placement(self) -> list[list[ZacTile | None]]:
        """Generates an initial placement (e.g., random or sequential fill)."""
        grid_slots = []
        for r in range(self.grid_rows):
            for c in range(self.grid_cols):
                grid_slots.append((r, c))

        random.shuffle(grid_slots)  # random order for filling slots

        current_placement: list[list[ZacTile | None]] = [
            [None for _ in range(self.grid_cols)] for _ in range(self.grid_rows)
        ]

        tiles_to_assign = list(self.tiles_to_place)  # copy

        for i in range(len(tiles_to_assign)):
            if i < len(grid_slots):
                r, c = grid_slots[i]
                current_placement[r][c] = tiles_to_assign[i]
            else:
                logger.warning(
                    "More tiles than available grid slots during placement generation.")
                break

        return current_placement

    def get_neighbour_placement(self, current_placement: list[list[ZacTile | None]]) -> list[list[ZacTile | None]]:
        """Generates a neighbour placement by swapping two items (tiles or None)."""
        new_placement = [
            # Shallow copy rows, tile objects are references
            row[:] for row in current_placement]

        # Pick two distinct random cells in the grid
        r1, c1 = random.randrange(
            self.grid_rows), random.randrange(self.grid_cols)
        r2, c2 = random.randrange(
            self.grid_rows), random.randrange(self.grid_cols)
        while r1 == r2 and c1 == c2:  # Ensure they are different cells
            r2, c2 = random.randrange(
                self.grid_rows), random.randrange(self.grid_cols)

        # Swap the contents of these two cells
        new_placement[r1][c1], new_placement[r2][c2] = new_placement[r2][c2], new_placement[r1][c1]

        return new_placement

    def optimise_placement(self, iterations: int = 1000, initial_temp: float = 10.0, cooling_rate: float = 0.995) -> list[list[ZacTile | None]]:
        """
        Optimises tile placement using Simulated Annealing. Assumes tiles in self.tiles_to_place are already scheduled.
        """

        if not self.tiles_to_place:
            logger.info("No tiles to place.")
            return [[None for _ in range(self.grid_cols)] for _ in range(self.grid_rows)]

        if len(self.tiles_to_place) > self.grid_rows * self.grid_cols:
            logger.warning(
                "More tiles to place than grid capacity. Placing a subset.")

        current_placement = self.generate_initial_placement()
        current_contention = self.calculate_contention(current_placement)

        best_placement = [row[:] for row in current_placement]
        best_contention = current_contention

        temp = initial_temp

        logger.info(
            f"Starting placement optimisation. Initial contention: {current_contention:.2f} (for {len(self.tiles_to_place)} tiles)")

        for i in range(iterations):
            placement = self.get_neighbour_placement(
                current_placement)
            contention = self.calculate_contention(placement)

            acceptance_probability = 0.0
            if contention < current_contention:
                acceptance_probability = 1.0
            elif temp > 1e-6:  # to avoid division by zero or extreme values
                delta_energy = contention - current_contention
                acceptance_probability = math.exp(-delta_energy / temp)

            if random.random() < acceptance_probability:
                current_placement = placement
                current_contention = contention
                if current_contention < best_contention:
                    best_placement = [row[:] for row in current_placement]
                    best_contention = current_contention

            temp *= cooling_rate
            if i > 0 and i % (iterations // 20) == 0:
                # log progress periodically
                logger.info(
                    f"Placement optimiser Iteration {i}: Temp={temp:.4f}, Current contention={current_contention:.2f}, Best contention={best_contention:.2f}")

        logger.info(
            f"Finished placement optimisation. Best contention: {best_contention:.2f}")
        return best_placement
