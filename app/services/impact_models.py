"""Impact & hazard models for the visual simulation.

  Velocity v = Q/(B_eff y); dv = y*v (DEFRA FD2320 people-hazard proxy);
  Froude Fr = v/sqrt(g y); unit stream power w = rho g q S (Bagnold 1966);
  force per metre f = 0.5 rho Cd v^2 y, Cd=1.2 (bluff body);
  momentum flux M = rho Q v.

People classes (dv m2/s): LOW<0.5 (and y<0.75), MODERATE<1.2, HIGH<2.0,
EXTREME>=2.0 or y>=2.0. Building damage: JRC Asia residential anchors
(Huizinga et al. 2017), piecewise-linear. Agriculture: depth-band x crop
sensitivity x duration (FAO-style). Unit costs are PLACEHOLDERS.
"""
import math
import numpy as np
from . import geo
from .unit_costs import get_costs

RHO = 1000.0
G = 9.81
CD_BLUFF = 1.2

THRESHOLDS = {
    "people_hazard": {"low": 0.5, "moderate": 1.2, "high": 2.0,
                      "depth_extreme_m": 2.0},
    "building_damage_anchors": [(0.0, 0.00), (0.1, 0.05), (0.5, 0.20),
                                (1.0, 0.35), (1.5, 0.45), (2.0, 0.55),
                                (3.0, 0.65), (4.0, 0.70), (5.0, 0.75),
                                (6.0, 0.80)],
    "agri_loss": [((0.0, 0.25), 0.15), ((0.25, 0.5), 0.30), ((0.5, 1.0), 0.50),
                  ((1.0, 2.0), 0.70), ((2.0, 99.0), 0.85)],
    "unit_costs_inr": {"building": 600_000, "crop_per_ha": 120_000,
                       "livestock_per_head": 40_000},
}

_PEOPLE_CLS = THRESHOLDS["people_hazard"]
_BLD_ANCHORS = THRESHOLDS["building_damage_anchors"]
_AGRI_TABLE = THRESHOLDS["agri_loss"]


def _normal_depth(Q, B, n, S):
    return (Q * n / (max(B, 5.0) * math.sqrt(max(S, 1e-4)))) ** 0.6


def node_state(Q, B, n_man, S, spread, base_q):
    Q = max(float(Q), 0.0)
    if Q <= 1.0:
        return {"Q": 0.0, "y": 0.0, "v": 0.0, "dv": 0.0, "Fr": 0.0,
                "power_W_m2": 0.0, "force_kN_m": 0.0, "wet": False}
    y = _normal_depth(Q, B, n_man, S)
    B_eff = max(B + spread * y, 1.0)
    v = Q / (B_eff * y)
    dv = y * v
    Fr = v / math.sqrt(G * max(y, 1e-6))
    q = Q / max(B, 5.0)
    power = RHO * G * q * S
    force = 0.5 * RHO * CD_BLUFF * v * v * y / 1000.0
    return {"Q": round(Q, 1), "y": round(y, 2), "v": round(v, 2),
            "dv": round(dv, 2), "Fr": round(Fr, 2),
            "power_W_m2": round(power, 0),
            "force_kN_m": round(force, 1), "wet": Q > 2.0 * base_q}


def people_hazard_class(dv, depth):
    if depth >= _PEOPLE_CLS["depth_extreme_m"] or dv >= _PEOPLE_CLS["high"]:
        return "EXTREME"
    if dv >= _PEOPLE_CLS["moderate"]:
        return "HIGH"
    if dv >= _PEOPLE_CLS["low"] and depth < 0.75:
        return "MODERATE"
    return "LOW"


def building_damage_fraction(depth_m):
    a = _BLD_ANCHORS
    if depth_m <= a[0][0]:
        return a[0][1]
    if depth_m >= a[-1][0]:
        return a[-1][1]
    for i in range(1, len(a)):
        if depth_m <= a[i][0]:
            x0, y0 = a[i-1]; x1, y1 = a[i]
            return y0 + (y1 - y0) * (depth_m - x0) / (x1 - x0)
    return a[-1][1]


CROP_SENSITIVITY = {"orchard": 1.0, "vegetables": 0.9, "wheat": 0.8,
                    "paddy": 0.6, "maize": 0.85, "fodder": 0.5,
                    "default": 0.8}


def agri_loss_fraction(depth_m, duration_hr, crop="default"):
    base = 0.15
    for (lo, hi), frac in _AGRI_TABLE:
        if lo <= depth_m < hi:
            base = frac
            break
    sens = CROP_SENSITIVITY.get(str(crop).lower(), 0.8)
    dur_scale = min(1.3, max(0.6,
                  math.log1p(max(duration_hr, 1.0)) / math.log(1 + 48)))
    return round(min(base * (0.55 + 0.45 * sens) * dur_scale, 0.95), 2)


N_FRAMES = 14


def build_visual_simulation(breach, inun, params, assets, incident_id=None, region_key=None):
    t_ser = inun.get("t_series_min")
    q_ser = inun.get("node_Q_series")
    nodes = inun.get("nodes")
    if not (t_ser and q_ser and nodes):
        return None
    B = params.get("valley_width_m", 90.0)
    n_man = params.get("manning_n", 0.045)
    S = params.get("bed_slope", 0.02)
    spread = params.get("spreading_factor", 2.5)
    base_q = params.get("base_flow_m3s", 50.0)

    pts = [[nd["lat"], nd["lon"]] for nd in nodes]
    cum = geo.cumulative_distances(pts)
    n = len(nodes)
    bt = np.array(breach["time_min"]); bq = np.array(breach["Q_m3s"])
    order = np.argsort(bt)
    bt, bq = bt[order], bq[order]

    fi = np.unique(np.geomspace(max(1, len(t_ser) * 0.02),
                                len(t_ser) - 1, N_FRAMES).astype(int))
    if len(fi) < N_FRAMES:
        fi = np.unique(np.linspace(0, len(t_ser) - 1, N_FRAMES).astype(int))
    frames, seg_bearings = [], []
    for i in range(n - 1):
        seg_bearings.append(geo.bearing(pts[i][0], pts[i][1],
                                        pts[i+1][0], pts[i+1][1]))
    for f in fi:
        states = [node_state(q_ser[i][f], B, n_man, S, spread, base_q)
                  for i in range(n)]
        segs = []
        area_m2 = 0.0
        for i in range(n - 1):
            st = states[i]
            hw = max((B + spread * st["y"]) / 2.0, 3.0)
            L = cum[i+1] - cum[i]
            area_m2 += 2 * hw * L
            l1 = geo.destination(pts[i][0], pts[i][1], seg_bearings[i]-90, hw)
            r1 = geo.destination(pts[i][0], pts[i][1], seg_bearings[i]+90, hw)
            l2 = geo.destination(pts[i+1][0], pts[i+1][1], seg_bearings[i]-90, hw)
            r2 = geo.destination(pts[i+1][0], pts[i+1][1], seg_bearings[i]+90, hw)
            segs.append({"i": i, "y": st["y"], "v": st["v"], "dv": st["dv"],
                         "wet": st["wet"],
                         "ring": [[round(p[0], 5), round(p[1], 5)]
                                  for p in (l1, l2, r2, r1)]})
        wet_chain = [cum[i] for i in range(n) if states[i]["wet"]]
        front_km = round(max(wet_chain) / 1000.0, 2) if wet_chain else 0.0
        t_now = float(t_ser[f])
        q_dam = float(q_ser[0][f]) if f < len(q_ser[0]) else 0.0
        released = float(np.interp(t_now, bt, np.cumsum(
            np.concatenate([[0], 0.5 * (bq[1:] + bq[:-1]) * np.diff(bt)])) * 60.0))
        vmax = max((s["v"] for s in states), default=0.0)
        dvmax = max((s["dv"] for s in states), default=0.0)
        fmax = max((s["force_kN_m"] for s in states), default=0.0)
        v_at_dam = states[0]["v"]
        frames.append({
            "t_min": round(t_now, 1),
            "q_dam_m3s": round(q_dam, 1),
            "v_dam_ms": round(v_at_dam, 2),
            "momentum_flux_MN": round(RHO * q_dam * max(v_at_dam, 0.01) / 1e6, 2),
            "released_m3": round(released, 0),
            "pct_released": round(100.0 * released /
                                  max(breach.get("drained_volume_m3", 1.0), 1.0), 1),
            "front_km": front_km,
            "area_km2": round(area_m2 / 1e6, 2),
            "max_v_ms": round(vmax, 2), "max_dv": round(dvmax, 2),
            "max_force_kN_m": round(fmax, 1),
            "segments": segs})

    impact, totals = _impact_schedule(nodes, pts, assets, params,
                                      tmax=float(t_ser[-1]),
                                      incident_id=incident_id,
                                      region_key=region_key)
    econ_limit = ("Economic figures use PLACEHOLDER unit costs - replace with district Schedule of Rates."
                  if totals.get("unit_costs_flagged")
                  else f"Economic figures use configured unit costs ({totals.get('unit_costs_source')} override).")
    return {
        "frames": frames, "impact": impact, "totals": totals,
        "thresholds": THRESHOLDS,
        "method": ("Per-frame Manning depth & velocity from routed node "
                   "hydrographs; hazard metrics (dv, Fr, stream power, drag "
                   "force) per node per frame; JRC Asia depth-damage curve "
                   "(Huizinga 2017); DEFRA FD2320 people classes; FAO-style "
                   "agriculture loss table."),
        "limitations": [
            "Frame velocities are section-averaged (1D); local velocities "
            "around obstructions can be 2-3x higher.",
            "Damage curves are regional averages; building quality varies.",
            econ_limit,
            "Agriculture parcels are point-samples, not polygons."]}


def _impact_schedule(nodes, pts, assets, params, tmax, incident_id=None, region_key=None):
    impact = []
    totals = {"people": {"LOW": 0, "MODERATE": 0, "HIGH": 0, "EXTREME": 0},
              "people_total": 0, "buildings_affected": 0,
              "buildings_fully_damaged_eq": 0.0, "critical_infra": [],
              "agri_ha_affected": 0.0, "agri_ha_lost": 0.0, "livestock": 0,
              "economic_inr": {"buildings": 0, "agriculture": 0, "livestock": 0}}
    uc_info = get_costs(incident_id=incident_id, region_key=region_key)
    uc = uc_info["costs"]
    totals["unit_costs_source"] = uc_info["source"]
    totals["unit_costs_flagged"] = uc_info["flagged_placeholder"]
    event_hr = tmax / 60.0
    B = params.get("valley_width_m", 90.0)
    for a in assets:
        d, ch, vi = geo.point_polyline_distance(a["lat"], a["lon"], pts)
        channel_hw = nodes[vi]["flood_width_m"] / 2.0
        hw = max(channel_hw, 3500.0)
        if d > hw:
            continue
        nd = nodes[vi]
        depth = nd["max_depth_m"] if d <= channel_hw else max(0.3, round(nd["max_depth_m"] * max(0.1, 1.0 - 0.75 * (d - channel_hw) / max(hw - channel_hw, 1.0)), 2))
        st = node_state(nd["peak_Q_m3s"], B, params.get("manning_n", 0.045),
                        params.get("bed_slope", 0.02),
                        params.get("spreading_factor", 2.5),
                        params.get("base_flow_m3s", 50.0))
        cls = people_hazard_class(st["dv"], depth)
        entry = {"name": a["name"], "kind": a["kind"],
                 "lat": a["lat"], "lon": a["lon"],
                 "nearest_km": round(ch / 1000.0, 2),
                 "arrival_min": nd["arrival_min"],
                 "peak_depth_m": depth, "peak_v_ms": st["v"],
                 "dv": st["dv"], "force_kN_m": st["force_kN_m"],
                 "people_hazard": cls}
        if a["kind"] in ("settlement", "building"):
            entry["population"] = a.get("population", 0)
            entry["buildings"] = a.get("buildings", 1)
            entry["attributes"] = a.get("attributes", {})
            entry["critical"] = a.get("critical", False)
            bdf = building_damage_fraction(depth)
            entry["building_damage_frac"] = round(bdf, 2)
            totals["people"][cls] += a.get("population", 0) or 0
            totals["people_total"] += a.get("population", 0) or 0
            totals["buildings_affected"] += a.get("buildings", 1) or 0
            totals["buildings_fully_damaged_eq"] += (a.get("buildings", 1) or 0) * bdf
            totals["economic_inr"]["buildings"] += int(
                (a.get("buildings", 1) or 0) * bdf * uc["building"])
        elif a["kind"] == "infrastructure":
            entry["attributes"] = a.get("attributes", {})
            entry["critical"] = True
            totals["critical_infra"].append({
                "name": a["name"], "depth_m": depth,
                "force_kN_m": st["force_kN_m"],
                "arrival_min": nd["arrival_min"]})
        elif a["kind"] == "agriculture":
            attrs = a.get("attributes") or {}
            defaulted = "area_ha" not in attrs
            ha = float(attrs.get("area_ha", 1.0))
            crop = attrs.get("crop", "default")
            loss = agri_loss_fraction(depth, event_hr, crop)
            entry["area_ha"] = ha
            entry["crop"] = crop
            entry["loss_frac"] = loss
            entry["defaulted_area"] = defaulted
            totals["agri_ha_affected"] += ha
            totals["agri_ha_lost"] += ha * loss
            totals["economic_inr"]["agriculture"] += int(ha * loss * uc["crop_per_ha"])
        if a.get("livestock"):
            entry["livestock"] = a["livestock"]
            totals["livestock"] += a["livestock"]
            totals["economic_inr"]["livestock"] += int(
                a["livestock"] * uc["livestock_per_head"])
        impact.append(entry)
    totals["buildings_fully_damaged_eq"] = round(totals["buildings_fully_damaged_eq"], 1)
    totals["agri_ha_affected"] = round(totals["agri_ha_affected"], 1)
    totals["agri_ha_lost"] = round(totals["agri_ha_lost"], 1)
    totals["economic_total_inr"] = sum(totals["economic_inr"].values())
    impact.sort(key=lambda e: (e.get("arrival_min") is None,
                               e.get("arrival_min") or 1e9))
    return impact, totals
