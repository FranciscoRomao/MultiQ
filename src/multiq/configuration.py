from dataclasses import dataclass
import yaml
import logging

logger = logging.getLogger("multiq")
                           
@dataclass
class MultiQConfig:
    # QPU Settings
    entanglement_height: int  # um
    qpu_width: int  # um
    qpu_height: int  # um
    zone_separation: int  # um
    entanglement_site_separation: list[int]  # um
    storage_site_separation: list[int]  # um
    aod_minimum_separation: int
    time_1qGate: float  # us
    grid_cols: int
    grid_rows: int
    
    fidelity_2q_gate: float
    fidelity_1q_gate: float
    fidelity_atom_transfer: float
    time_coherence: float
    time_atom_transfer: float
    time_rydberg: float
    time_1q_gate: float

    # Planner Settings
    perf_weight: float
    tmp_arch_file: str
    layer_split_window: int
    storage_zone_rows: int  # set by the planner
    storage_zone_cols: int  # set by the planner
    zone_centering: list[int]

    perf_weight_selector: float
    # Bundler Settings
    selection_algorithm: str  # "fifo" or "sa"
    initial_temperature: float
    final_temperature: float
    cooling_rate: float
    max_iterations: int
    max_iterations_per_temp: int

    # Placer Settings
    dynamic_placement: bool
    trivial_placement: bool
    use_window: bool
    window_size: int
    enable_verification: bool
    multiq_check: bool
    l2: bool
    physical_cell_width_um: float
    physical_cell_height_um: float

    # Scheduler Settings
    scheduling_strategy: str
    reuse: bool
    resyn: bool
    
    no_row1q_gates: bool
    
    # Router Settings
    routing_strategy: str
    has_dependency: bool
    num_aods: int

    # Animator Settings
    r1q_time: float  # us, duration of a full-row 1q gate
    arch_padding: int
    animation: bool = False

    # Results Settings
    results_dir: str = "results/multiq"

    def __post_init__(self):
        if self.scheduling_strategy not in ["asap", "graph_coloring"]:
             logging.error(f"Invalid scheduling_strategy: {self.scheduling_strategy}. Must be 'asap' or 'graph_coloring'.")
             raise ValueError(f"Unknown scheduling_strategy: {self.scheduling_strategy}")

    @classmethod
    def from_config(cls, config_dict: dict) -> 'MultiQConfig':
        field_names = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_config_dict = {
            k: v for k, v in config_dict.items() if k in field_names
        }
        return cls(**filtered_config_dict)
    
    @classmethod
    def from_config_file(cls, filepath) -> 'MultiQConfig':
        try:
            with open(filepath, 'r') as f:
                config_dict = yaml.safe_load(f)
                if not isinstance(config_dict, dict):
                    logging.error(f"Invalid configuration format in '{filepath}': Expected a dictionary.")
                    raise ValueError("YAML file content must be a dictionary.")
                return cls.from_config(config_dict)
        
        except FileNotFoundError:
            logging.warning(f"Configuration file '{filepath}' not found. Using default values.")
            return cls()
        except yaml.YAMLError as e:
            logging.error(f"Error parsing YAML in '{filepath}': {e}")
            raise
        except Exception as e:
            logging.error(f"An unexpected error occurred while loading config from '{filepath}': {e}")
            raise
