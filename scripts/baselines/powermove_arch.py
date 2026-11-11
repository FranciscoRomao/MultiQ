import json
import math


def load_general_arch(arch_spec_path: str) -> dict:
    with open(arch_spec_path, "r") as f:
        return json.load(f)


def _sep_xy(site_seperation) -> tuple:
    if isinstance(site_seperation, (list, tuple)):
        return site_seperation[0], site_seperation[1]
    return site_seperation, site_seperation


def general_arch_to_powermove_target(arch: dict) -> dict:
    """Map a ZAC-style architecture spec to PowerMove's parameters, sizing the grid from the fixed entanglement zone capacity."""
    entangling_sites = sum(
        slm["r"] * slm["c"]
        for zone in arch["entanglement_zones"]
        for slm in zone["slms"]
    )
    grid_side = math.ceil(math.sqrt(entangling_sites))

    fidelity = arch["operation_fidelity"]
    duration = arch["operation_duration"]
    coherence_time = float(arch["qubit_spec"]["T"])

    # PowerMove reads site separations and transfer time from module globals, so take them from the same spec.
    entangle_slm = arch["entanglement_zones"][0]["slms"][0]
    x_sep, y_sep = _sep_xy(entangle_slm["site_seperation"])
    storage_slm = arch["storage_zones"][0]["slms"][0]
    _, storage_y_sep = _sep_xy(storage_slm["site_seperation"])

    return {
        "grid_rows": grid_side,
        "grid_cols": grid_side,
        "entangling_sites": entangling_sites,
        "num_aods": len(arch["aods"]),
        "fidelity_2q_gate": fidelity["two_qubit_gate"],
        "fidelity_1q_gate": fidelity["single_qubit_gate"],
        "fidelity_atom_transfer": fidelity["atom_transfer"],
        "coherence_time": coherence_time,
        "time_1q_gate": duration["1qGate"],
        "x_sep": x_sep,
        "y_sep": y_sep,
        "storage_y_sep": storage_y_sep,
        "mus_per_frm": duration["atom_transfer"],
    }


def apply_target(target: dict, mvqc_module) -> None:
    """Overwrite PowerMove's module-level hardware constants, since it does not take them as arguments."""
    mvqc_module.Fidelity_2Q_Gate = target["fidelity_2q_gate"]
    mvqc_module.Fidelity_1Q_Gate = target["fidelity_1q_gate"]
    mvqc_module.Fidelity_Atom_Transfer = target["fidelity_atom_transfer"]
    mvqc_module.Coherence_Time = target["coherence_time"]
    mvqc_module.Time_1Q_Gate = target["time_1q_gate"]
    mvqc_module.X_SEP = target["x_sep"]
    mvqc_module.Y_SEP = target["y_sep"]
    mvqc_module.Storage_Y_SEP = target["storage_y_sep"]
    mvqc_module.MUS_PER_FRM = target["mus_per_frm"]
