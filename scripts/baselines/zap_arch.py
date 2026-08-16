import json


def load_general_arch(arch_spec_path: str) -> dict:
    with open(arch_spec_path, "r") as f:
        return json.load(f)


def general_arch_to_zap_arch(arch: dict) -> dict:
    """
    Translate a ZAC-style architecture spec (e.g. config/zac/general_arch.json) into
    the JSON schema ZAP's Zap/Router/Simulator/Placer classes read directly.

    ZAP's own architecture/default.json already uses the exact same storage_zones/
    entanglement_zones/slms nesting (id/site_seperation/r/c/location) as general_arch,
    so zone geometry carries over unchanged - this is a field-rename, not an
    approximation, same as the qmap conversion. Only two keys are spelled
    differently: qubit_spec["T2"] (ZAP) vs ["T"] (general_arch), and
    operation_duration["2qGate"] (ZAP) vs ["rydberg"] (general_arch).
    operation_fidelity uses identical key names in both schemas.

    ZAP has no notion of a discrete AOD count or arch_range/rydberg_range bounding
    boxes - movement/placement heuristics are governed entirely by its own
    ``routing`` knobs, not a hardware AOD list - so those general_arch fields are
    simply dropped rather than mapped onto anything.
    """
    duration = arch["operation_duration"]

    return {
        "name": arch["name"],
        "operation_duration": {
            "2qGate": duration["rydberg"],
            "1qGate": duration["1qGate"],
            "atom_transfer": duration["atom_transfer"],
        },
        "operation_fidelity": dict(arch["operation_fidelity"]),
        "qubit_spec": {"T2": float(arch["qubit_spec"]["T"])},
        "storage_zones": arch["storage_zones"],
        "entanglement_zones": arch["entanglement_zones"],
    }
