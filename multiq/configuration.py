from dataclasses import dataclass

@dataclass
class MultiQConfig:
    # Planner Settings
    default_architecture: str = "default_architecture.json"
    util_weight: float = 0.05 # This is currently unused, we simply do (1 - perf_weight) for utility
    perf_weight: float = 0.95
    tmp_arch_file = 'zac_config/tmp_architecture.json'
    layer_split_window = 2 # Defines the lookahead window for execution layer splitting in the planner

    # Placer Settings
    trivial_placement: bool = False
    grid_cols:int = 1
    grid_rows:int = 1
    dynamic_placement: bool = True
    use_window: bool = True
    window_size: int = 1000
    physical_cell_width_um: float = 10.0  # physical width of one grid_col cell
    physical_cell_height_um: float = 50.0 # physical height of one grid_row cell
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
    time_rydberg: float = 0.36 # us
    time_atom_transfer = 15 # us
    time_rydberg = 0.36 # us
    time_1qGate = 0.625 # us
    qpu_settings = {
        'name': 'default_qpu',
        'height': 100, # um
        'width': 100, # um
        #'arch_range': [100, 100], #width, height (um)
        'entanglement_height': 20, # um
        'zone_separation': 10,
        'entanglement_site_separation': [12, 10], # [x, y] separation in um
        'storage_site_separation': [3,3], # [x, y] separation in um
        'aod_minimum_separation': 2, # um
    }

    # Animation Settings
    arch_padding = 1

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
