
from multiq.configuration import MultiQConfig
from .tile import Tile

from multiq.types import Movement, TileMovement

def global_movement(config: MultiQConfig, tile_anchor_r: int, tile_anchor_c: int, m: Movement) -> Movement:
    """ Convert a tile-local movement to QPU-global physical coordinates. """
    x_offset = tile_anchor_c * config.physical_cell_width_um
    y_offset = tile_anchor_r * config.physical_cell_height_um

    return Movement(m.qubit_index, m.start_x + x_offset, m.end_x + x_offset, m.start_y + y_offset, m.end_y + y_offset)

# Moves in different tiles can run in parallel only if they share row coordinates.
def row_compatible(a: Movement, b: Movement) -> bool:
    if a.start_y != b.start_y:
        return False
    if a.end_y != b.end_y:
        return False

    return True

def column_compatible(a: Movement, b: Movement) -> bool:
    if a.start_x != b.start_x:
        return False
    if a.end_x != b.end_x:
        return False
    
    return True

def diagonal_compatible(config: MultiQConfig, tiles: list[list[Tile | None]] , tm1: TileMovement, tm2: TileMovement, layer: int, is_forward_move: bool) -> bool:
    """ Return False if two moves from diagonal tiles conflict with another qubit on the QPU. """
    epsilon = 1e-9

    global_m1 = global_movement(config,
        tm1.row_idx, tm1.col_idx, tm1.movement)
    global_m2 = global_movement(config,
        tm2.row_idx, tm2.col_idx, tm2.movement)

    # Crossing points of the two moves' start rows and columns.
    intersect1_gx, intersect1_gy = global_m1.start_x, global_m2.start_y
    intersect2_gx, intersect2_gy = global_m2.start_x, global_m1.start_y

    intersections_to_check = [
        (intersect1_gx, intersect1_gy), (intersect2_gx, intersect2_gy)]

    # Mappings alternate forward and backward per layer.
    mapping_idx = 2 * layer if is_forward_move else 2 * layer + 1

    for gx, gy in intersections_to_check:
        for r_target in range(config.grid_rows):
            for c_target in range(config.grid_cols):
                target_tile = tiles[r_target][c_target]
                if not target_tile:
                    # Skips empty cells and the falsy _OCCUPIED marker of wide tiles.
                    continue

                tile_origin_global_x = c_target * config.physical_cell_width_um
                tile_origin_global_y = r_target * config.physical_cell_height_um

                local_x_in_target = gx - tile_origin_global_x
                local_y_in_target = gy - tile_origin_global_y

                arch = target_tile.architecture

                if not (arch.arch_range[0][0] <= local_x_in_target < arch.arch_range[1][0] and
                        arch.arch_range[0][1] <= local_y_in_target < arch.arch_range[1][1]):
                    continue

                if mapping_idx >= len(target_tile.qubit_mapping) or \
                   target_tile.qubit_mapping[mapping_idx] is None:
                    continue

                qubit_physical_locations = target_tile.qubit_mapping[mapping_idx]
                for _, q_slm_pos_tuple in enumerate(qubit_physical_locations):
                    if q_slm_pos_tuple is None:
                        continue

                    q_local_x, q_local_y = target_tile.architecture.exact_SLM_location(
                        q_slm_pos_tuple[0], q_slm_pos_tuple[1], q_slm_pos_tuple[2]
                    )
                    if abs(q_local_x - local_x_in_target) < epsilon and \
                       abs(q_local_y - local_y_in_target) < epsilon:
                        return False
    return True
