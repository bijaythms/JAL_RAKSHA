"""
Locality Population Clustering & Demographic Service for Jal-Raksha.
Aggregates riverside dwellings, schools, wards, and settlements into distinct
locality population clusters with demographic breakdowns, evacuation metrics,
and circular overlay geometries.
"""

import math
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from ..db import Asset, Incident, Simulation

def get_population_clusters(incident_id: str, db: Session) -> List[Dict[str, Any]]:
    """
    Groups incident assets into locality population clusters and computes
    demographic vulnerability, circle display radii, and evacuation estimates.
    """
    assets = db.query(Asset).filter(Asset.incident_id == incident_id).all()
    if not assets:
        return []

    # Get latest simulation results for hazard context if available
    latest_sim = (db.query(Simulation)
                  .filter(Simulation.incident_id == incident_id, Simulation.status == "DONE")
                  .order_by(Simulation.created_at.desc())
                  .first())
    impact_map = {}
    if latest_sim and latest_sim.results:
        try:
            import json
            sim_res = json.loads(latest_sim.results) if isinstance(latest_sim.results, str) else latest_sim.results
            for imp in sim_res.get("visual", {}).get("impact", []):
                if imp.get("name"):
                    impact_map[imp["name"]] = imp
        except Exception:
            pass

    # Group assets into geographic locality clusters (radius ~ 1.8 km)
    clusters: List[Dict[str, Any]] = []

    for a in assets:
        pop = a.population or 0
        bld = a.buildings or 1
        name = a.name or ""
        import json
        attrs = json.loads(a.attributes) if isinstance(a.attributes, str) else (a.attributes or {})
        
        # Determine locality group key by proximity or name stem
        matched_cluster = None
        for c in clusters:
            dist_deg = math.hypot(c["sum_lat_weight"] / max(c["total_pop"], 1) - a.lat,
                                  c["sum_lon_weight"] / max(c["total_pop"], 1) - a.lon)
            if dist_deg < 0.022:  # ~2.2 km locality cluster threshold
                matched_cluster = c
                break

        weight = max(pop, 20)
        if matched_cluster:
            matched_cluster["assets"].append(a)
            matched_cluster["total_pop"] += pop
            matched_cluster["total_bld"] += bld
            matched_cluster["sum_lat_weight"] += a.lat * weight
            matched_cluster["sum_lon_weight"] += a.lon * weight
            matched_cluster["weight_sum"] += weight
        else:
            clusters.append({
                "assets": [a],
                "total_pop": pop,
                "total_bld": bld,
                "sum_lat_weight": a.lat * weight,
                "sum_lon_weight": a.lon * weight,
                "weight_sum": weight
            })

    output = []
    for idx, c in enumerate(clusters):
        c_assets = c["assets"]
        pop = max(c["total_pop"], len(c_assets) * 45)
        bld = max(c["total_bld"], len(c_assets))
        
        # Centroid
        lat = round(c["sum_lat_weight"] / c["weight_sum"], 5)
        lon = round(c["sum_lon_weight"] / c["weight_sum"], 5)

        # Derive representative locality name from key assets
        facility_names = []
        loc_name = ""
        for a in c_assets:
            aname = a.name
            attrs = json.loads(a.attributes) if isinstance(a.attributes, str) else (a.attributes or {})
            btype = (attrs.get("building_type") or a.kind or "").lower()
            if any(k in btype or k in aname.lower() for k in ["hospital", "school", "bridge", "powerhouse", "depot"]):
                facility_names.append(aname)
            if not loc_name:
                # Extract first word or geographical tag
                words = aname.split()
                if words:
                    loc_name = words[0]
                    if len(words) > 1 and words[1] in ["Town", "Riverbank", "Valley", "Gorge", "Highway"]:
                        loc_name += f" {words[1]}"

        if not loc_name:
            loc_name = f"Locality Reach #{idx+1}"
        else:
            if not any(w in loc_name for w in ["Locality", "Settlement", "Town", "Colony"]):
                loc_name += " Locality"

        # Circle display radius: scaled with square root of population
        # (between 320m for small settlements and 1400m for major towns)
        circle_radius_m = max(320, min(1400, int(math.sqrt(pop) * 22)))

        # Demographics breakdown
        children = int(pop * 0.16)
        elderly = int(pop * 0.13)
        adults = pop - children - elderly
        
        # Check simulation impact on assets in this cluster
        max_depth = 0.0
        min_arrival = 999.0
        hazard_level = "LOW"
        for a in c_assets:
            if a.name in impact_map:
                im = impact_map[a.name]
                d = float(im.get("peak_depth_m") or 0.0)
                arr = im.get("arrival_min")
                if d > max_depth:
                    max_depth = d
                if arr is not None and float(arr) < min_arrival:
                    min_arrival = float(arr)
                haz = im.get("people_hazard", "LOW")
                if haz == "EXTREME":
                    hazard_level = "EXTREME"
                elif haz == "HIGH" and hazard_level != "EXTREME":
                    hazard_level = "HIGH"
                elif haz == "MODERATE" and hazard_level not in ["EXTREME", "HIGH"]:
                    hazard_level = "MODERATE"

        # Evacuation metrics
        clearance_hr = round(pop / 750.0, 1)  # ~750 persons per evacuation lane per hour
        evac_priority = "IMMEDIATE" if hazard_level == "EXTREME" else "HIGH" if hazard_level == "HIGH" else "STANDARD"

        output.append({
            "id": f"loc-{idx+1}",
            "name": loc_name,
            "lat": lat,
            "lon": lon,
            "population": pop,
            "buildings": bld,
            "radius_meters": circle_radius_m,
            "hazard_level": hazard_level,
            "peak_depth_m": round(max_depth, 2) if max_depth > 0 else None,
            "first_arrival_min": round(min_arrival, 1) if min_arrival < 900 else None,
            "facilities": facility_names[:4],
            "demographics": {
                "children": children,
                "elderly": elderly,
                "adults": adults
            },
            "evacuation": {
                "estimated_clearance_hr": clearance_hr,
                "priority": evac_priority
            }
        })

    # Sort down-valley (highest latitude to lowest, or by arrival time)
    output.sort(key=lambda x: (x["first_arrival_min"] if x["first_arrival_min"] is not None else 999, -x["lat"]))
    return output
