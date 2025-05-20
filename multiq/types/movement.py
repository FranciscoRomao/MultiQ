from dataclasses import dataclass, field
import typing

# AoD movement for a specific qubit
class Movement(typing.NamedTuple):
    qubit_index: int
    start_x: int
    end_x: int
    start_y: int
    end_y: int

