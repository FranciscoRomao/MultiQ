from dataclasses import dataclass

@dataclass
class MultiQConfig:
    # Placer Settings
    trivial_placement: bool = False
    dynamic_placement: bool = True
    use_window: bool = True
    window_size: int = 1000
    # Scheduler Settings
    scheduling_strategy: str = "asap"
    # Router Settings
    routing_strategy: str = "maximalis_sort"
    # General Settings
    enable_verification: bool = True
    l2: bool = False
    reuse: bool = True
    resyn: bool = True
    has_dependency: bool = True

    # QPU configuration
    grid_cols: int = 16 # Number of grid cells horizontally
    grid_rows: int = 2  # Number of QPU rows for tiles
    physical_cell_width_um: float = 10.0  # physical width of one grid_col cell
    physical_cell_height_um: float = 50.0 # physical height of one grid_row cell

    def __post_init__(self):
        if self.scheduling_strategy not in ["asap", "graph_coloring"]:
             raise ValueError(f"Unknown scheduling_strategy: {self.scheduling_strategy}")

    @classmethod
    def from_config(cls, config_dict: dict) -> 'MultiQConfig':
        # Filter out keys not present in the dataclass to avoid TypeError
        # Get field names from the dataclass itself
        field_names = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_config_dict = {
            k: v for k, v in config_dict.items() if k in field_names
        }
        return cls(**filtered_config_dict)


    @classmethod
    def from_config_file(cls, filepath) -> 'MultiQConfig':
        try:
            with open(filepath, 'r') as f:
                config_dict = filepath.load(f)
                return cls.from_config(config_dict)
        except FileNotFoundError:
            print(f"Warning: Configuration file '{filepath}' not found. Using default values.")
            return cls() # Return default config if file not found
