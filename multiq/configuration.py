from dataclasses import dataclass
from typing import List, Optional
import yaml
import logging

logger = logging.getLogger("multiq")
                           
@dataclass
class MultiQConfig:
    # QPU Settings
    entanglement_height: int# = 15 # um
    qpu_width: int# = 80 # um
    qpu_height: int# = 40 # um
    zone_separation: int# = 10 # um
    entanglement_site_separation: list[int]# = [12, 10] # um
    storage_site_separation: list[int]# = [10, 10] # um
    aod_minimum_separation: int# = 2
    time_rydberg: float# = 0.36 # usAdd commentMore actions
    time_atom_transfer: int# = 15 # us
    time_1qGate: float# = 0.625 # us
    grid_cols: int# = 2 # Number of grid cells horizontally
    grid_rows: int# = 1  # Number of QPU rows for tiles
   
    # Planner Settings
    util_weight: float# = 0.05 #This is not used, we simply do (1 - perf_weight) for utility weight
    perf_weight: float# = 0.95
    tmp_arch_file: str# = 'zac_config/tmp_architecture.json'
    layer_split_window: int# = 2 # Defines the lookahead window for execution layer splitting in the planner
    storage_zone_rows: int# = None #This is calculated later in the planner
    zone_centering: list[int]# = True # If True, the planner will center the zones in the grid_row

    # Placer Settings
    dynamic_placement: bool# = True
    trivial_placement: bool# = False
    use_window: bool# = True
    window_size: int# = 1000
    enable_verification: bool# = True
    l2: bool# = False
    physical_cell_width_um: float# = 10.0  # physical width of one grid_col cell
    physical_cell_height_um: float# = 50.0 # physical height of one grid_row cell

    # Scheduler Settings
    scheduling_strategy: str# = "asap"
    reuse: bool# = True
    resyn: bool# = True
    
    # Router Settings
    routing_strategy: str# = "maximalis_sort"
    has_dependency: bool# = True

    # Animator Settings
    r1q_time: float# = 12.0 #us. Duration of an entire row 1q application using AoD lasers.Add commentMore actions
    arch_padding: int# = 1

    def __post_init__(self):
        if self.scheduling_strategy not in ["asap", "graph_coloring"]:
             logging.error(f"Invalid scheduling_strategy: {self.scheduling_strategy}. Must be 'asap' or 'graph_coloring'.")
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
                config_dict = yaml.safe_load(f)
                if not isinstance(config_dict, dict):
                    logging.error(f"Invalid configuration format in '{filepath}': Expected a dictionary.")
                    raise ValueError("YAML file content must be a dictionary.")
                return cls.from_config(config_dict)
        
        except FileNotFoundError:
            logging.warning(f"Configuration file '{filepath}' not found. Using default values.")
            return cls() # Return default config if file not found
        except yaml.YAMLError as e: # Catch YAML-specific parsing errors
            logging.error(f"Error parsing YAML in '{filepath}': {e}")
            raise # Re-raise to indicate a serious configuration error
        except Exception as e:
            logging.error(f"An unexpected error occurred while loading config from '{filepath}': {e}")
            raise
