import typing


# AoD movement for a specific qubit
class Movement(typing.NamedTuple):
    qubit_index: int
    # these are either tile-local or global *geometric* coordinates
    start_x: float
    end_x: float
    start_y: float
    end_y: float

class TileMovement(typing.NamedTuple):
    # the row_idx,col_idx offset into the tiles data structure
    row_idx: int
    col_idx: int
    # the movement to be applied in this tile
    movement: Movement
 