"""Evacuation-clock model.
T_warn = arrival - now; T_need = mobilization (regional) + terrain-penalized
walking to the corridor fringe (LOWER bound, no roads).
GREEN>=1.6, AMBER>=1.2, RED<1.2 => vertical evacuation."""
import math
from . import geo
from .india import region_for

V0_WALK = 1.2
HEAD_START_FACTOR = 1.2
GREEN_FACTOR = 1.6


def safe_ground_distance(asset_lat, asset_lon, nodes, halfwidths):
    pts = [[n["lat"], n["lon"]] for n in nodes]
    d, ch, vi = geo.point_polyline_distance(asset_lat, asset_lon, pts)
    hw = halfwidths[vi]
    return max(hw - d, 50.0)


def travel_time_min(dist_m, bed_slope):
    grade = min(bed_slope * 2.0, 0.6)
    v = V0_WALK / (1.0 + 3.0 * grade)
    return dist_m / v / 60.0


def evacuation_state(asset_lat, asset_lon, nodes, halfwidths, arrival_min,
                     t_now, bed_slope, mobilization_min):
    if arrival_min is None:
        return {"status": "SAFE", "reason": "front never reaches this asset"}
    t_warn = arrival_min - t_now
    if t_warn < 0:
        return {"status": "IMPACTED", "reason": "flood front has arrived",
                "t_warn_min": round(t_warn, 1)}
    dist = safe_ground_distance(asset_lat, asset_lon, nodes, halfwidths)
    t_travel = travel_time_min(dist, bed_slope)
    t_need = mobilization_min + t_travel
    ratio = t_warn / max(t_need, 1e-6)
    if ratio >= GREEN_FACTOR:
        status, action = "GREEN", (f"Evacuate within {t_warn:.0f} min - "
                                   "comfortable margin")
    elif ratio >= HEAD_START_FACTOR:
        status, action = "AMBER", (f"START NOW - {t_warn:.0f} min left, "
                                   f"need ~{t_need:.0f} min")
    else:
        status, action = "RED", (f"INSUFFICIENT TIME - {t_warn:.0f} min left "
                                 f"vs ~{t_need:.0f} min needed: move to high "
                                 "ground / upper floors VERTICALLY")
    return {"status": status, "t_warn_min": round(t_warn, 1),
            "t_needed_min": round(t_need, 1), "ratio": round(ratio, 2),
            "walk_to_safety_m": round(dist, 0), "action": action}


def build_evacuation_overlay(visual_payload, nodes, params, lat, lon):
    preset = region_for(lat, lon)
    halfwidths = [n["flood_width_m"] / 2.0 for n in nodes]
    settlements = [e for e in (visual_payload or {}).get("impact", [])
                   if e.get("population")]
    clocks = []
    for s in settlements:
        st = evacuation_state(s["lat"], s["lon"], nodes, halfwidths,
                              s.get("arrival_min"), 0.0,
                              params.get("bed_slope", preset.bed_slope),
                              preset.mobilization_min)
        radius_m = 300 + 40 * math.sqrt(s["population"] or 1)
        clocks.append({
            "name": s["name"], "lat": s["lat"], "lon": s["lon"],
            "population": s["population"],
            "arrival_min": s.get("arrival_min"),
            "ring_radius_m": round(radius_m, 0),
            "t_needed_min": st.get("t_needed_min"),
            "walk_to_safety_m": st.get("walk_to_safety_m"),
            "status_at_zero": st["status"],
            "region_mobilization_min": preset.mobilization_min})
    return {
        "clocks": clocks, "region": preset.key, "region_name": preset.name,
        "mobilization_min": preset.mobilization_min,
        "method": ("T_evac = mobilization (regional) + terrain-penalized "
                   "walking to corridor fringe; feasibility ratio "
                   "T_warn/T_need, GREEN>=1.6, AMBER>=1.2, RED<1.2 => "
                   "vertical evacuation"),
        "limitations": [
            "No road network - travel time is a conservative walking lower "
            "bound.",
            "Mobilization time is a regional constant.",
            "Safe ground = outside the modeled corridor; slope-failure zones "
            "extend the real hazard."]}
