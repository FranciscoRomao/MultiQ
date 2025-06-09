from dataclasses import dataclass, field
import typing



# AoD movement for a specific qubit
class Movement(typing.NamedTuple):
    qubit_index: int
    start_x: int
    end_x: int
    start_y: int
    end_y: int

class GridCoord(typing.NamedTuple):
    x: int
    y: int

class TileMovement(typing.NamedTuple):
    row_idx: int
    col_idx: int
    movement: Movement

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
