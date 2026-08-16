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
    """
    Reduce a ZAC-style architecture spec (e.g. config/zac/general_arch.json) to the
    handful of parameters PowerMove's model actually understands: a single square
    interaction-zone grid (Row x Row) with a virtually unbounded storage area below
    it, a count of independent AODs, the fidelity/coherence constants, and the
    site separations/transfer duration used to score a compiled circuit.

    PowerMove has no notion of multiple SLMs or zone shape/aspect ratio - only
    total entangling-zone capacity carries over, not layout. Since MultiQ/ZAC
    both place circuits within general_arch's real, fixed device footprint
    regardless of circuit size, Row is derived from that fixed capacity rather
    than sized per-circuit (as PowerMove's own test scripts do via
    ceil(sqrt(n))) - otherwise PowerMove would trivially always fit any circuit,
    which would make the comparison unfair. Site separations (x_sep/y_sep/
    storage_y_sep) and the atom-transfer duration DO carry over, via
    apply_target overwriting PowerMove's hardcoded X_SEP/Y_SEP/Storage_Y_SEP/
    MUS_PER_FRM globals - otherwise PowerMove would silently compute movement
    distances and transfer durations against its own built-in geometry instead
    of the device spec ZAC/QMAP actually compile against.
    """
    entangling_sites = sum(
        slm["r"] * slm["c"]
        for zone in arch["entanglement_zones"]
        for slm in zone["slms"]
    )
    grid_side = math.ceil(math.sqrt(entangling_sites))

    fidelity = arch["operation_fidelity"]
    duration = arch["operation_duration"]
    coherence_time = float(arch["qubit_spec"]["T"])

    # PowerMove's own movement-distance/transfer-duration model is driven by module-
    # level constants (X_SEP, Y_SEP, Storage_Y_SEP, MUS_PER_FRM) rather than any
    # architecture argument, so pull the real site separations and transfer duration
    # out of the same general_arch spec ZAC/QMAP compile against, instead of letting
    # PowerMove fall back on its own hardcoded (and physically unrelated) defaults.
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
    """
    Patch PowerMove's module-level fidelity/coherence constants in place.

    PowerMove hardcodes these as globals in mvqc_multi_aod.py (and enola.py,
    mvqc.py) rather than accepting them as arguments, so the only way to point it
    at a specific device model is to overwrite the globals before calling in.
    """
    mvqc_module.Fidelity_2Q_Gate = target["fidelity_2q_gate"]
    mvqc_module.Fidelity_1Q_Gate = target["fidelity_1q_gate"]
    mvqc_module.Fidelity_Atom_Transfer = target["fidelity_atom_transfer"]
    mvqc_module.Coherence_Time = target["coherence_time"]
    mvqc_module.Time_1Q_Gate = target["time_1q_gate"]
    mvqc_module.X_SEP = target["x_sep"]
    mvqc_module.Y_SEP = target["y_sep"]
    mvqc_module.Storage_Y_SEP = target["storage_y_sep"]
    mvqc_module.MUS_PER_FRM = target["mus_per_frm"]
