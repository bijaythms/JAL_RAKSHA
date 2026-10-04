"""Manual-simulation parameter resolution with per-field provenance:
USER > REGION_PRESET > DEFAULT(formula). The provenance table is shown in
the UI and embedded in reports - nothing is silently assumed."""
from . import india

_DEFAULTS = dict(
    dam_material="Landslide debris", breach_time_hr=1.5,
    valley_width_m=90.0, bed_slope=0.02, manning_n=0.045,
    spreading_factor=2.5, base_flow_m3s=50.0, inflow_m3s=50.0,
    dam_crest_len_m=115.0,
)

def resolve_manual_params(user):
    lat, lon = float(user["lat"]), float(user["lon"])
    region = india.region_for(lat, lon)
    preset = {
        "dam_material": region.material_prior,
        "breach_time_hr": region.breach_time_typical_hr,
        "valley_width_m": region.valley_width_m,
        "bed_slope": region.bed_slope,
        "manning_n": region.manning_n,
        "spreading_factor": region.spreading_factor,
        "base_flow_m3s": region.base_flow_m3s,
        "inflow_m3s": region.base_flow_m3s,
        "dam_crest_len_m": max(region.valley_width_m * 1.2, 60.0),
    }
    params, provenance = {}, {}

    for f in ("dam_material", "scenario", "breach_time_hr", "valley_width_m",
              "bed_slope", "manning_n", "spreading_factor", "base_flow_m3s",
              "inflow_m3s", "dam_crest_len_m", "breach_width_m",
              "lake_area_m2", "with_uncertainty"):
        if user.get(f) is not None:
            params[f] = user[f]; provenance[f] = "USER"
        elif f in preset:
            params[f] = preset[f]; provenance[f] = "REGION_PRESET"
        elif f in _DEFAULTS:
            params[f] = _DEFAULTS[f]; provenance[f] = "DEFAULT"
        elif f == "with_uncertainty":
            params[f] = True; provenance[f] = "DEFAULT"

    params["stored_volume_m3"] = float(user["stored_volume_m3"])
    provenance["stored_volume_m3"] = "USER"
    params["dam_height_m"] = float(user["dam_height_m"])
    provenance["dam_height_m"] = "USER"

    if user.get("breach_depth_m") is not None:
        params["breach_depth_m"] = float(user["breach_depth_m"])
        provenance["breach_depth_m"] = "USER"
    else:
        params["breach_depth_m"] = round(params["dam_height_m"] * 0.75, 1)
        provenance["breach_depth_m"] = "DEFAULT (0.75 x dam height)"

    if user.get("lake_area_m2") is not None:
        params["lake_area_m2"] = float(user["lake_area_m2"])
        provenance["lake_area_m2"] = "USER"
    else:
        params["lake_area_m2"] = round(
            params["stored_volume_m3"] /
            max(0.5 * params["dam_height_m"], 1.0), 0)
        provenance["lake_area_m2"] = "DEFAULT (V/(0.5*H) wedge approximation)"

    if user.get("breach_width_m") is None:
        params["breach_width_m"] = round(
            max(params["dam_crest_len_m"] * 0.4, 10.0), 1)
        provenance["breach_width_m"] = "DEFAULT (0.40 x crest length)"

    valid = ("Earth", "Rock", "Landslide debris", "Sediment", "Ice/debris",
             "Mixed", "Unknown", "Concrete", "Masonry")
    if params["dam_material"] not in valid:
        params["dam_material"] = "Unknown"
        provenance["dam_material"] = "DEFAULT (invalid material entered)"

    return {"params": params, "provenance": provenance,
            "region": {"key": region.key, "name": region.name,
                       "notes": region.notes,
                       "mobilization_min": region.mobilization_min}}
