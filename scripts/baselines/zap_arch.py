import json


def load_general_arch(arch_spec_path: str) -> dict:
    with open(arch_spec_path, "r") as f:
        return json.load(f)


def general_arch_to_zap_arch(arch: dict) -> dict:
    """Convert a ZAC-style architecture spec to ZAP's schema, which only renames a few keys and drops the AOD fields."""
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
