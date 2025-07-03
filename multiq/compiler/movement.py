import typing

from multiq.configuration import MultiQConfig
from .tile import Tile

from multiq.types import Movement, TileMovement
   
def global_movement(config: MultiQConfig, tile_anchor_r: int, tile_anchor_c: int, m: Movement) -> Movement:
    """ 
    Convert a tile-local movement (physical coords within tile) into QPU-global physical coordinates.
    tile_anchor_r, tile_anchor_c are the grid cell indices of the tile's top-left corner.
    """
    x_offset = tile_anchor_c * config.physical_cell_width_um
    y_offset = tile_anchor_r * config.physical_cell_height_um

    return Movement(m.qubit_index, m.start_x + x_offset, m.end_x + x_offset, m.start_y + y_offset, m.end_y + y_offset)


# Across multiple tiles, only moves that share row coords can be done in parallel
def row_compatible(a: Movement, b: Movement) -> bool:
    # a,b must be from different tiles

    # must be same start col
    if a.start_y != b.start_y:
        return False
    # must be same finish col
    if a.end_y != b.end_y:
        return False

    return True

def column_compatible(a: Movement, b: Movement) -> bool:
    # a,b must be from different tiles

    # must start+end in same row
    if a.start_x != b.start_x:
        return False
    if a.end_x != b.end_x:
        return False
    
    return True

def diagonal_compatible(config: MultiQConfig, tiles: list[list[Tile | None]] , tm1: TileMovement, tm2: TileMovement, layer: int, is_forward_move: bool) -> bool:
    """ 
    Check if two movements (from different, diagonal tiles) are compatible with the other ones on the QPU.
    returns True if compatible, False if there's a conflict.
    """
    epsilon = 1e-9

    # 1. Get global start coordinates for tm1 and tm2 movements
    global_m1 = global_movement(config,
        tm1.row_idx, tm1.col_idx, tm1.movement)
    global_m2 = global_movement(config,
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
        for r_target in range(config.grid_rows):
            for c_target in range(config.grid_cols):
                target_tile = tiles[r_target][c_target]
                if target_tile is None:
                    continue

                # Calculate the target_tile's origin in global physical coordinates
                # r_target, c_target are grid cell indices for target_tile's anchor
                tile_origin_global_x = c_target * config.physical_cell_width_um
                tile_origin_global_y = r_target * config.physical_cell_height_um

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
