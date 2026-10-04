"""Exposure (exact corridor tests, single nearest-node lookup, agriculture
included - consistent with the visual engine), TDRI with REAL renormalized
weight-perturbation sensitivity, documented confidence rubric, exports."""
import csv, io, json
from . import geo
from .hydraulics import BANDS
from .impact_models import building_damage_fraction, agri_loss_fraction


def classify_depth(d):
    for thr, lbl in BANDS:
        if d <= thr:
            return lbl
    return BANDS[-1][1]


def assess_exposure(inundation, assets):
    nodes = inundation.get("nodes")
    if not nodes or not assets:
        return _empty_exposure()
    pts = [[n["lat"], n["lon"]] for n in nodes]
    pop = bld = liv = 0
    settlements, dist, crit, agri = [], {}, [], []
    for a in assets:
        d, ch, vi = geo.point_polyline_distance(a.lat, a.lon, pts)
        channel_hw = nodes[vi]["flood_width_m"] / 2.0
        flood_reach_w = max(channel_hw, 3500.0)
        if d > flood_reach_w:
            continue
        node = nodes[vi]
        node_depth = node["max_depth_m"] if d <= channel_hw else max(0.3, round(node["max_depth_m"] * max(0.1, 1.0 - 0.75 * (d - channel_hw) / max(flood_reach_w - channel_hw, 1.0)), 2))
        band = classify_depth(node_depth)
        pop += a.population or 0; bld += a.buildings or 0; liv += a.livestock or 0
        dist[band] = dist.get(band, 0) + (a.population or 0)
        if a.kind == "settlement":
            settlements.append({"name": a.name, "population": a.population,
                                "buildings": a.buildings,
                                "max_depth_m": node["max_depth_m"],
                                "arrival_min": node["arrival_min"]})
        elif a.kind == "infrastructure":
            crit.append({"name": a.name,
                         "type": json.loads(a.attributes or "{}").get("type", ""),
                         "depth_m": node["max_depth_m"]})
        elif a.kind == "agriculture":
            attrs = json.loads(a.attributes or "{}")
            defaulted = "area_ha" not in attrs
            ha = float(attrs.get("area_ha", 1.0))
            agri.append({"name": a.name, "area_ha": ha,
                         "crop": attrs.get("crop", "default"),
                         "max_depth_m": node["max_depth_m"],
                         "arrival_min": node["arrival_min"],
                         "defaulted_area": defaulted})
    return {
        "total_population_exposed": pop, "buildings_exposed": bld,
        "livestock_exposed": liv, "settlements_affected": len(settlements),
        "settlements": sorted(settlements, key=lambda s: -s["population"]),
        "critical_infra_affected": crit,
        "agriculture_affected": agri,
        "agri_ha_affected": round(sum(x["area_ha"] for x in agri), 1),
        "population_by_depth_band": dist,
        "method": "Exact point-to-centerline corridor test; depth/arrival "
                  "from nearest hydraulic node"}


def _empty_exposure():
    return {"total_population_exposed": 0, "buildings_exposed": 0,
            "livestock_exposed": 0, "settlements_affected": 0,
            "settlements": [], "critical_infra_affected": [],
            "agriculture_affected": [], "agri_ha_affected": 0.0,
            "population_by_depth_band": {}, "method": "no assets or no nodes"}


_TDRI_WEIGHTS = {
    "volume": 0.20, "geometry": 0.15, "hydraulic": 0.20,
    "population": 0.25, "infrastructure": 0.10, "lead_time": 0.10,
}
_MATERIAL_EROD = {"Earth": 1.0, "Landslide debris": 0.9, "Sediment": 0.85,
                  "Mixed": 0.7, "Ice/debris": 0.6, "Rock": 0.3,
                  "Concrete": 0.2, "Masonry": 0.25, "Unknown": 0.6}


def calculate_tdri(sim, expo):
    prm = sim["params"]; res = sim["results"]
    first_arr = res["inundation"].get("first_arrival_min")
    f = {
        "volume": min(100, 100 * (prm["stored_volume_m3"] / 25e6) ** 0.5),
        "geometry": min(100, prm["dam_height_m"] *
                        _MATERIAL_EROD.get(prm.get("dam_material", "Unknown"), 0.6)),
        "hydraulic": min(100, res["breach"]["peak_Q_m3s"] / 5000 * 100),
        "population": min(100, expo["total_population_exposed"] / 5000 * 100),
        "infrastructure": min(100, len(expo["critical_infra_affected"]) / 15 * 100),
        "lead_time": 100 if first_arr is None else max(0, 100 - first_arr / 0.9),
    }

    def score(weights):
        s = sum(weights.values())
        return sum(weights[k] / s * f[k] for k in f)

    base = score(_TDRI_WEIGHTS)
    lo = hi = base
    for k in _TDRI_WEIGHTS:
        for m in (0.8, 1.2):
            w2 = dict(_TDRI_WEIGHTS); w2[k] = _TDRI_WEIGHTS[k] * m
            sc = score(w2)
            lo, hi = min(lo, sc), max(hi, sc)
    band = ("EXTREME" if base >= 75 else "HIGH" if base >= 55 else
            "MODERATE" if base >= 35 else "LOW")
    action = {"EXTREME": "Immediate evacuation; air reconnaissance; 24x7 monitoring",
              "HIGH": "Precautionary evacuation of low-lying settlements; alert SDRF",
              "MODERATE": "Intensified monitoring; prepare evacuation plans",
              "LOW": "Routine surveillance"}[band]
    return {"tdri": round(base, 1), "range": [round(lo, 1), round(hi, 1)],
            "band": band, "recommended_action": action,
            "factors": {k: round(v, 1) for k, v in f.items()},
            "weights": _TDRI_WEIGHTS,
            "method": "Weighted multi-criteria index. Range = min/max over "
                      "all one-at-a-time +/-20% weight perturbations, "
                      "renormalized to sum 1."}


_CONF_RUBRIC = [
    ("base", 40, "Base for physics-based modelling"),
    ("dem_hypsometry", 15, "Measured DEM hypsometry feeding the breach engine"),
    ("user_centerline", 10, "User-validated downstream centerline (>= 5 pts)"),
    ("asset_layer", 10, "Local exposure asset layer (>= 5 assets)"),
    ("monte_carlo", 10, "Monte Carlo uncertainty ensemble"),
    ("verified_field_reports", 5, ">= 1 field-verified damage report"),
]


def compute_confidence(has_uncertainty, incident, n_assets, n_verified):
    c, parts = 0.0, []
    for key, pts, desc in _CONF_RUBRIC:
        if key == "base":
            c += pts; parts.append(f"{desc} (+{pts})"); continue
        ok = {"dem_hypsometry": bool(incident.dem_upload_id),
              "user_centerline": len(json.loads(incident.centerline or "[]")) >= 5,
              "asset_layer": n_assets >= 5,
              "monte_carlo": bool(has_uncertainty),
              "verified_field_reports": n_verified >= 1}[key]
        if ok:
            c += pts; parts.append(f"{desc} (+{pts})")
        else:
            parts.append(f"Missing: {desc.lower()} (+0)")
    return {"confidence_pct": round(min(c, 90.0), 1), "provenance": parts,
            "rubric": {k: p for k, p, _ in _CONF_RUBRIC},
            "note": "Confidence reflects data provenance and model depth only. "
                    "Even at maximum confidence, natural-dam breach prediction "
                    "remains highly uncertain."}


def exposure_csv(expo):
    buf = io.StringIO(); w = csv.writer(buf)
    w.writerow(["settlement", "population", "buildings", "max_depth_m",
                "arrival_min"])
    for s in expo.get("settlements", []):
        w.writerow([s["name"], s["population"], s["buildings"],
                    s["max_depth_m"],
                    s["arrival_min"] if s["arrival_min"] is not None else ""])
    return buf.getvalue()


def nodes_csv(inun):
    buf = io.StringIO(); w = csv.writer(buf)
    w.writerow(["chainage_m", "lat", "lon", "peak_Q_m3s", "max_depth_m",
                "flood_width_m", "arrival_min"])
    for n in inun["nodes"]:
        w.writerow([n["chainage_m"], n["lat"], n["lon"], n["peak_Q_m3s"],
                    n["max_depth_m"], n["flood_width_m"],
                    n["arrival_min"] if n["arrival_min"] is not None else ""])
    return buf.getvalue()


def flood_geojson(inun):
    ring = inun.get("max_extent_ring") or []
    feats = []
    if ring:
        coords = [[p[1], p[0]] for p in ring] + [[ring[0][1], ring[0][0]]]
        feats.append({"type": "Feature",
                      "properties": {"kind": "max_extent",
                                     "area_km2": inun["max_area_km2"]},
                      "geometry": {"type": "Polygon", "coordinates": [coords]}})
    for s in inun.get("snapshots", []):
        coords = [[p[1], p[0]] for p in s["ring"]] +                  [[s["ring"][0][1], s["ring"][0][0]]]
        feats.append({"type": "Feature",
                      "properties": {"kind": "snapshot",
                                     "time_min": s["time_min"]},
                      "geometry": {"type": "Polygon", "coordinates": [coords]}})
    return {"type": "FeatureCollection", "features": feats}
