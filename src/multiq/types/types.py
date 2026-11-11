import typing


class Movement(typing.NamedTuple):
    qubit_index: int
    # Tile-local or global geometric coordinates.
    start_x: float
    end_x: float
    start_y: float
    end_y: float

class TileMovement(typing.NamedTuple):
    row_idx: int
    col_idx: int
    movement: Movement
 