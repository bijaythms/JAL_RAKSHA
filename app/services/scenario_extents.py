"""
Multi-Scenario Inundation Extent Engine for Jal-Raksha.
Generates comparative hydrodynamic inundation polygon layers for:
1. Minor Breach (Advisory / Partial Spillway Jam)
2. Moderate Breach (Piping Failure at Normal Pool)
3. Major Breach (Design Overtopping Flood)
4. Catastrophic / PMF Full Dam Break (Probable Maximum Flood)
"""

import json
import math
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from . import geo
from ..db import Simulation, Incident

SCENARIO_CONFIGS = [
    {
        "key": "minor",
        "name": "Minor / Partial Breach (Advisory)",
        "mechanism": "Controlled spillway discharge or partial structural breach (0.4x width, 0.5x depth).",
        "hw_factor": 0.55,
        "q_factor": 0.28,
        "depth_factor": 0.52,
        "color": "#eab308",
        "fill_color": "#fef08a",
        "fill_opacity": 0.28,
        "badge_class": "risk-moderate",
        "risk_level": "MODERATE"
    },
    {
        "key": "moderate",
        "name": "Moderate Breach (Piping Failure)",
        "mechanism": "Internal embankment piping failure during normal operational pool (0.7x width, 0.75x depth).",
        "hw_factor": 0.78,
        "q_factor": 0.62,
        "depth_factor": 0.78,
        "color": "#f97316",
        "fill_color": "#fed7aa",
        "fill_opacity": 0.32,
        "badge_class": "risk-high",
        "risk_level": "HIGH"
    },
    {
        "key": "major",
        "name": "Major Breach (Design Overtopping)",
        "mechanism": "Overtopping crest failure during design flood conditions (baseline 1.0x width, 1.0x depth).",
        "hw_factor": 1.00,
        "q_factor": 1.00,
        "depth_factor": 1.00,
        "color": "#ef4444",
        "fill_color": "#fca5a5",
        "fill_opacity": 0.36,
        "badge_class": "risk-extreme",
        "risk_level": "EXTREME"
    },
    {
        "key": "full",
        "name": "Catastrophic / PMF Full Dam Break",
        "mechanism": "Full crest breach collapse with Probable Maximum Flood (PMF) extreme inflow.",
        "hw_factor": 1.48,
        "q_factor": 2.15,
        "depth_factor": 1.45,
        "color": "#a855f7",
        "fill_color": "#e9d5ff",
        "fill_opacity": 0.35,
        "badge_class": "risk-extreme",
        "risk_level": "CATASTROPHIC"
    }
]

def get_simulation_scenario_extents(sim_id: str, db: Session) -> Dict[str, Any]:
    """
    Computes comparative inundation polygon extents and hydraulic metrics
    for all 4 breach scenarios based on the simulation hydraulic reach.
    """
    sim = db.get(Simulation, sim_id)
    if not sim or not sim.results:
        return {"error": "Simulation not found or missing results"}

    res = json.loads(sim.results) if isinstance(sim.results, str) else sim.results
    inun = res.get("inundation", {})
    breach = res.get("breach", {})
    nodes = inun.get("nodes", [])

    if len(nodes) < 2:
        return {"error": "Insufficient centerline nodes to construct scenarios"}

    pts = [[n["lat"], n["lon"]] for n in nodes]
    N = len(nodes)
    hw_l_base = []
    hw_r_base = []
    for i, n in enumerate(nodes):
        wl = n.get("hw_left_m")
        wr = n.get("hw_right_m")
        w_tot = float(n.get("flood_width_m") or 0.0)
        if wl is not None and wr is not None and wl > 10 and wr > 10:
            hw_l_base.append(float(wl))
            hw_r_base.append(float(wr))
        elif w_tot > 25:
            hw_l_base.append(float(w_tot / 2.0))
            hw_r_base.append(float(w_tot / 2.0))
        else:
            frac = i / max(N - 1, 1)
            est_hw = 65.0 + 180.0 * (frac ** 1.1)
            hw_l_base.append(est_hw)
            hw_r_base.append(est_hw)

    base_q = float(breach.get("peak_Q_m3s") or 15000.0)
    base_depth = float(inun.get("max_depth_m") or 16.0)

    scenarios_output = []

    for cfg in SCENARIO_CONFIGS:
        hw_l = [round(w * cfg["hw_factor"], 1) for w in hw_l_base]
        hw_r = [round(w * cfg["hw_factor"], 1) for w in hw_r_base]
        ring = geo.buffer_polygon(pts, hw_l, hw_r)
        area_km2 = round(geo.ring_area_m2(ring) / 1e6, 3) if ring else 0.0

        q_peak = round(base_q * cfg["q_factor"], 1)
        depth_max = round(base_depth * cfg["depth_factor"], 2)

        scenarios_output.append({
            "key": cfg["key"],
            "name": cfg["name"],
            "mechanism": cfg["mechanism"],
            "risk_level": cfg["risk_level"],
            "color": cfg["color"],
            "fill_color": cfg["fill_color"],
            "fill_opacity": cfg["fill_opacity"],
            "badge_class": cfg["badge_class"],
            "peak_Q_m3s": q_peak,
            "max_depth_m": depth_max,
            "area_km2": area_km2,
            "polygon": [[round(p[0], 5), round(p[1], 5)] for p in ring],
            "vertex_count": len(ring)
        })

    return {
        "simulation_id": sim.id,
        "incident_id": sim.incident_id,
        "reaches_count": len(nodes),
        "corridor_km": inun.get("corridor_km"),
        "scenarios": scenarios_output
    }
