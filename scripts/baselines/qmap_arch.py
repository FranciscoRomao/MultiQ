import json


def load_general_arch(arch_spec_path: str) -> dict:
    with open(arch_spec_path, "r") as f:
        return json.load(f)


def _convert_slm(slm: dict) -> dict:
    converted = dict(slm)
    if "site_seperation" in converted:
        converted["site_separation"] = converted.pop("site_seperation")
    return converted


def _convert_zone(zone: dict) -> dict:
    converted = dict(zone)
    converted["slms"] = [_convert_slm(slm) for slm in zone["slms"]]
    if "dimenstion" in converted:
        converted["dimension"] = converted.pop("dimenstion")
    return converted


def general_arch_to_qmap_arch(arch: dict) -> dict:
    """
    Translate a ZAC-style architecture spec (e.g. config/zac/general_arch.json) into
    the JSON schema expected by mqt.qmap.na.zoned.ZonedNeutralAtomArchitecture.

    Both schemas describe the same thing (zones of SLM traps + AODs), so this is a
    field-rename, not an approximation like the PowerMove conversion: ZAC spells the
    inter-site spacing key "site_seperation" (typo) where qmap spells it
    "site_separation", one of ZAC's zone dicts has a "dimenstion" typo where qmap
    expects "dimension", and the two-qubit gate fidelity/duration entries are keyed
    "two_qubit_gate"/"rydberg" in ZAC vs "rydberg_gate" in qmap for both duration and
    fidelity.
    """
    duration = arch["operation_duration"]
    fidelity = arch["operation_fidelity"]

    return {
        "name": arch["name"],
        "operation_duration": {
            "rydberg_gate": duration["rydberg"],
            "single_qubit_gate": duration["1qGate"],
            "atom_transfer": duration["atom_transfer"],
        },
        "operation_fidelity": {
            "rydberg_gate": fidelity["two_qubit_gate"],
            "single_qubit_gate": fidelity["single_qubit_gate"],
            "atom_transfer": fidelity["atom_transfer"],
        },
        "qubit_spec": {"T": float(arch["qubit_spec"]["T"])},
        "storage_zones": [_convert_zone(zone) for zone in arch["storage_zones"]],
        "entanglement_zones": [_convert_zone(zone) for zone in arch["entanglement_zones"]],
        "aods": [_convert_slm(aod) for aod in arch["aods"]],
        "arch_range": arch["arch_range"],
        "rydberg_range": arch["rydberg_range"],
    }


def general_arch_to_qmap_json_string(arch_spec_path: str) -> str:
    arch = load_general_arch(arch_spec_path)
    return json.dumps(general_arch_to_qmap_arch(arch))
