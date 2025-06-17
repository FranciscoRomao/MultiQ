from dataclasses import dataclass

@dataclass
class MultiQConfig:
    # Planner Settings
    default_architecture: str = "toy_architecture.json"
    util_weight: float = 0.05
    perf_weight: float = 0.95
    entanglement_height = 60 # um
    qpu_settings = {'width':80,
                    'height':40,
                    'zone_separation': 10,
                    'entanglement_height': 20,
                    'arch_padding': 5,
                    'entanglement_site_separation': [12,10],
                    'storage_site_separation': [3,3],
                    'aod_minimum_separation': 2,}
    tmp_arch_file = 'zac_config/tmp_architecture.json'
    layer_split_window = 2 # Defines the lookahead window for execution layer splitting in the planner

    r1q_time = 12.0 #us. Duration of an entire row 1q application using AoD lasers.Add commentMore actions
    storage_zone_rows = None #This is calculated later in the planner

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
    arch_padding: int = 1

    time_rydberg: float = 0.36 # usAdd commentMore actions
    time_atom_transfer = 15 # us
    time_1qGate = 0.625 # us

    # QPU configuration
    grid_cols: int = 2 # Number of grid cells horizontally
    grid_rows: int = 1  # Number of QPU rows for tiles
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
