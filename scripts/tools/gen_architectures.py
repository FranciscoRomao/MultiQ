import json
import math


def generate_scaled_arch(demand, base_arch_path="config/zac/general_arch.json",
                          out_arch_path=None, target_utilization=0.95,
                          scale_entanglement=True):
    """Scale the storage zone (and optionally the entanglement zone) by k = sqrt(target_capacity / old_capacity)."""
    with open(base_arch_path) as f:
        arch = json.load(f)

    storage_slm = arch["storage_zones"][0]["slms"][0]
    old_r, old_c = storage_slm["r"], storage_slm["c"]
    old_capacity = old_r * old_c
    target_capacity = demand / target_utilization
    k = math.sqrt(target_capacity / old_capacity)

    def scale_point(point):
        return [v * k for v in point]

    def to_int(value):
        if isinstance(value, list):
            return [to_int(v) for v in value]
        return int(round(value))

    new_r = max(2, round(old_r * k))
    new_c = max(2, round(old_c * k))
    while new_r * new_c < demand:
        new_c += 1
    old_dim_x, old_dim_y = arch["storage_zones"][0]["dimenstion"]
    storage_slm["r"] = new_r
    storage_slm["c"] = new_c

    ent_zone = arch["entanglement_zones"][0]

    if scale_entanglement:
        storage_slm["location"] = scale_point(storage_slm["location"])
        arch["storage_zones"][0]["offset"] = scale_point(arch["storage_zones"][0]["offset"])
        arch["storage_zones"][0]["dimenstion"] = scale_point(arch["storage_zones"][0]["dimenstion"])

        for slm in ent_zone["slms"]:
            slm["r"] = max(1, round(slm["r"] * k))
            slm["c"] = max(1, round(slm["c"] * k))
            slm["location"] = scale_point(slm["location"])
        ent_zone["offset"] = scale_point(ent_zone["offset"])
        ent_zone["dimension"] = scale_point(ent_zone["dimension"])

        arch["arch_range"] = [scale_point(arch["arch_range"][0]), scale_point(arch["arch_range"][1])]
        arch["rydberg_range"] = [[scale_point(arch["rydberg_range"][0][0]), scale_point(arch["rydberg_range"][0][1])]]
    else:
        # Only the storage zone scales, and offsets are derived from the template since it has some built-in padding.
        new_dim_x = old_dim_x * (new_c - 1) / (old_c - 1)
        new_dim_y = old_dim_y * (new_r - 1) / (old_r - 1)
        arch["storage_zones"][0]["dimenstion"] = [new_dim_x, new_dim_y]

        delta_y = new_dim_y - old_dim_y
        ent_dim_x, ent_dim_y = ent_zone["dimension"]
        old_ent_location_y = ent_zone["slms"][0]["location"][1]
        for slm in ent_zone["slms"]:
            slm["location"][1] += delta_y
        new_ent_location_y = old_ent_location_y + delta_y

        old_range = arch["arch_range"]
        old_max_x, old_max_y = old_range[1]
        zone_gap = old_ent_location_y - old_dim_y
        pad_x = old_max_x - max(old_dim_x, ent_dim_x)
        pad_y = old_max_y - (old_dim_y + zone_gap + ent_dim_y)

        new_max_x = max(new_dim_x, ent_dim_x) + pad_x
        new_max_y = new_dim_y + zone_gap + ent_dim_y + pad_y
        arch["arch_range"] = [old_range[0], [new_max_x, new_max_y]]
        arch["rydberg_range"] = [[[arch["rydberg_range"][0][0][0], new_ent_location_y], [new_max_x, new_max_y]]]

    # ZAP's router uses these as integer grid coordinates.
    for slm in arch["storage_zones"][0]["slms"]:
        slm["location"] = to_int(slm["location"])
    arch["storage_zones"][0]["offset"] = to_int(arch["storage_zones"][0]["offset"])
    arch["storage_zones"][0]["dimenstion"] = to_int(arch["storage_zones"][0]["dimenstion"])
    for slm in ent_zone["slms"]:
        slm["location"] = to_int(slm["location"])
    ent_zone["offset"] = to_int(ent_zone["offset"])
    ent_zone["dimension"] = to_int(ent_zone["dimension"])
    arch["arch_range"] = to_int(arch["arch_range"])
    arch["rydberg_range"] = to_int(arch["rydberg_range"])

    if out_arch_path:
        with open(out_arch_path, "w") as f:
            json.dump(arch, f, indent=1)

    return arch, new_r, new_c


