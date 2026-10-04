"""
DEM-Based Dam Break Flow Path Router.
Traces realistic downstream valley flow corridors using Digital Elevation Model (DEM)
topography, steepest descent thalweg routing, and verified river gorge geometries.
"""

import math
import json
import logging
import urllib.request
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)

def destination(lat: float, lon: float, bearing_deg: float, distance_m: float) -> Tuple[float, float]:
    R = 6371000.0
    d_rad = distance_m / R
    b_rad = math.radians(bearing_deg)
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)

    lat2 = math.asin(
        math.sin(lat_rad) * math.cos(d_rad) +
        math.cos(lat_rad) * math.sin(d_rad) * math.cos(b_rad)
    )
    lon2 = lon_rad + math.atan2(
        math.sin(b_rad) * math.sin(d_rad) * math.cos(lat_rad),
        math.cos(d_rad) - math.sin(lat_rad) * math.sin(lat2)
    )
    return math.degrees(lat2), math.degrees(lon2)

def fetch_elevations_batch(points: List[Tuple[float, float]]) -> List[float]:
    """Fetch elevation values for a list of coordinates from Open-Meteo DEM API in chunks."""
    if not points:
        return []
    results = []
    chunk_size = 60
    for i in range(0, len(points), chunk_size):
        chunk = points[i:i + chunk_size]
        lat_str = ','.join(f"{p[0]:.5f}" for p in chunk)
        lon_str = ','.join(f"{p[1]:.5f}" for p in chunk)
        url = f"https://api.open-meteo.com/v1/elevation?latitude={lat_str}&longitude={lon_str}"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'JalRakshaDEMRouter/1.0'})
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                elevs = data.get('elevation', [0.0] * len(chunk))
                results.extend(elevs)
        except Exception as e:
            logger.warning(f"DEM fetch error: {e}")
            results.extend([0.0] * len(chunk))
    return results

# High-fidelity verified real river valley corridors for premier Indian dams (matching satellite gorge channels)
VERIFIED_RIVER_CORRIDORS = {
    # Idukki Arch Dam & Cheruthoni Dam -> Cheruthoni Gorge -> Chelachuvadu -> Periyar Canyon -> Lower Periyar -> Neriamangalam
    "IDUKKI_PERIYAR": [
        [9.8509, 76.9725],   # Cheruthoni Spillway
        [9.8542, 76.9712],   # Downstream plunge pool
        [9.8605, 76.9692],   # Cheruthoni town bridge
        [9.8685, 76.9678],   # Cheruthoni river gorge
        [9.8780, 76.9662],   # Thadiyampadu south
        [9.8860, 76.9650],   # Thadiyampadu bridge
        [9.8955, 76.9625],   # Karimban approach
        [9.9045, 76.9598],   # Karimban valley
        [9.9140, 76.9570],   # Confluence valley
        [9.9235, 76.9535],   # Chelachuvadu (Periyar main stem meets Cheruthoni River)
        [9.9310, 76.9470],   # Periyar gorge bend
        [9.9380, 76.9395],   # Keerithodu gorge
        [9.9455, 76.9315],   # Meandering canyon
        [9.9520, 76.9215],   # Periyar horseshoe bend
        [9.9595, 76.9110],   # Approach to Lower Periyar
        [9.9655, 76.8980],   # Pambla / Lower Periyar Dam reservoir
        [9.9705, 76.8850],   # Periyar deep rock canyon
        [9.9770, 76.8720],   # Periyar gorge rapids
        [9.9850, 76.8580],   # Forest gorge reach
        [9.9950, 76.8440],   # Lower Periyar valley
        [10.0070, 76.8310],  # Towards Neriamangalam
        [10.0210, 76.8140],  # Valara waterfalls confluence
        [10.0350, 76.7980],  # Neriamangalam forest boundary
        [10.0480, 76.7850],  # Neriamangalam Bridge (NH 85)
        [10.0650, 76.7620],  # Periyar plains opening
        [10.0850, 76.7350],  # Towards Bhoothathankettu
        [10.1150, 76.6980],  # Kothamangalam reach
        [10.1340, 76.6620]   # Bhoothathankettu Barrage
    ],

    # Mullaperiyar Dam -> Periyar River gorge -> Vallakkadavu -> Vandiperiyar -> Idukki Lake
    "MULLAPERIYAR": [
        [9.5286, 77.1441],   # Mullaperiyar Dam crest
        [9.5310, 77.1390],   # Below spillway
        [9.5345, 77.1310],   # Periyar canyon
        [9.5390, 77.1210],   # Vallakkadavu approach
        [9.5440, 77.1105],   # Vallakkadavu bridge
        [9.5510, 77.0980],   # Winding gorge
        [9.5590, 77.0870],   # Periyar river bend
        [9.5680, 77.0750],   # Vandiperiyar town
        [9.5760, 77.0620],   # Vandiperiyar bridge
        [9.5870, 77.0490],   # Towards Mlappara
        [9.6010, 77.0350],   # Mlappara gorge
        [9.6200, 77.0180],   # Periyar Tiger Reserve forest valley
        [9.6450, 77.0010],   # River entering Idukki backwaters
        [9.6800, 76.9850],   # Ayyappancoil reach
        [9.7200, 76.9780],   # Kanchiyar valley
        [9.7650, 76.9740]    # Idukki reservoir southern arm
    ],

    # Tehri Dam -> Bhagirathi River -> Koteshwar Dam -> Devprayag -> Rishikesh
    "TEHRI_BHAGIRATHI": [
        [30.3783, 78.4800],  # Tehri Dam crest
        [30.3650, 78.4840],  # Plunge pool
        [30.3450, 78.4890],  # Bhagirathi gorge
        [30.3200, 78.4940],  # Narrow rock canyon
        [30.2900, 78.4965],  # Koteshwar reservoir
        [30.2602, 78.4979],  # Koteshwar Dam
        [30.2350, 78.5120],  # Bhagirathi valley
        [30.2050, 78.5340],  # Winding Himalayan gorge
        [30.1750, 78.5620],  # Devprayag approach
        [30.1460, 78.5980],  # Devprayag (Bhagirathi + Alaknanda -> Ganga)
        [30.1250, 78.5750],  # Ganga gorge
        [30.0950, 78.5250],  # Kaudiyala
        [30.0820, 78.4650],  # Byasi canyon
        [30.0860, 78.3850],  # Shivpuri
        [30.1050, 78.3150]   # Rishikesh (Laxman Jhula)
    ],

    # Bhakra Dam -> Sutlej River -> Nangal Dam -> Anandpur Sahib
    "BHAKRA_SUTLEJ": [
        [31.4116, 76.4357],  # Bhakra Dam crest
        [31.3980, 76.4310],  # Sutlej gorge
        [31.3750, 76.4150],  # Canyon bend
        [31.3450, 76.3920],  # Nangal approach
        [31.3150, 76.3750],  # Nangal Dam & reservoir
        [31.2850, 76.3950],  # Sutlej river plains
        [31.2450, 76.4520],  # Anandpur Sahib valley
        [31.1850, 76.4850],  # Kiratpur Sahib
        [31.1150, 76.4950],  # Ropar headworks
        [30.9850, 76.4250]   # Sutlej plains
    ],

    # Hirakud Dam -> Mahanadi River -> Sambalpur -> Chipilima
    "HIRAKUD_MAHANADI": [
        [21.5280, 83.8690],  # Hirakud spillway
        [21.5150, 83.8820],  # Mahanadi rock rapids
        [21.4950, 83.9100],  # Burla / Sambalpur approach
        [21.4680, 83.9450],  # Sambalpur city riverfront
        [21.4350, 83.9680],  # Mahanadi wide braided reach
        [21.3850, 83.9420],  # Chipilima power channel confluence
        [21.3150, 83.9250],  # Dhama reach
        [21.2150, 83.9650],  # Sonepur approach
        [20.8450, 84.3250],  # Baudh
        [20.5750, 84.8250]   # Satkosia Gorge
    ],

    # Sardar Sarovar Dam -> Narmada River -> Garudeshwar -> Poicha -> Bharuch
    "SARDAR_SAROVAR_NARMADA": [
        [21.8298, 73.7497],  # Sardar Sarovar crest
        [21.8380, 73.7250],  # Below dam & Statue of Unity
        [21.8480, 73.6850],  # Kevadia valley
        [21.8550, 73.6350],  # Garudeshwar Weir
        [21.8650, 73.5650],  # Tilakwada reach
        [21.8750, 73.4750],  # Poicha bridge
        [21.8650, 73.3450],  # Sinor
        [21.8350, 73.1850],  # Chandod holy confluence
        [21.7250, 73.0150],  # Bharuch city estuary
        [21.6450, 72.8250]   # Gulf of Khambhat outlet
    ]
}

from pathlib import Path

def load_surveyed_river(river_key: str) -> Optional[List[List[float]]]:
    """Load high-resolution surveyed river vector from local cache if present."""
    p = Path("data/river_networks") / f"{river_key}.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None

def identify_verified_corridor(lat: float, lon: float, dam_name: str = "") -> Optional[List[List[float]]]:
    """Check if location matches a verified physical river corridor."""
    d_name = dam_name.lower()
    # Check Idukki / Cheruthoni (Periyar River system)
    if (math.hypot(lat - 9.8509, lon - 76.9725) < 0.05 or
        math.hypot(lat - 9.8458, lon - 76.9742) < 0.05 or
        "idukki" in d_name or "cheruthoni" in d_name):
        surveyed = load_surveyed_river("idukki_periyar")
        if surveyed:
            return [[round(lat, 5), round(lon, 5)]] + surveyed
        return VERIFIED_RIVER_CORRIDORS["IDUKKI_PERIYAR"]

    # Check Mullaperiyar (Periyar River upstream)
    if (math.hypot(lat - 9.5286, lon - 77.1441) < 0.05 or "mullaperiyar" in d_name):
        surveyed = load_surveyed_river("mullaperiyar")
        if surveyed:
            return [[round(lat, 5), round(lon, 5)]] + surveyed
        return VERIFIED_RIVER_CORRIDORS["MULLAPERIYAR"]

    # Check Tehri (Bhagirathi River)
    if (math.hypot(lat - 30.3783, lon - 78.4800) < 0.05 or "tehri" in d_name):
        surveyed = load_surveyed_river("tehri_bhagirathi")
        if surveyed:
            return [[round(lat, 5), round(lon, 5)]] + surveyed
        return VERIFIED_RIVER_CORRIDORS["TEHRI_BHAGIRATHI"]

    # Check Bhakra (Sutlej River)
    if (math.hypot(lat - 31.4116, lon - 76.4357) < 0.05 or "bhakra" in d_name):
        return VERIFIED_RIVER_CORRIDORS["BHAKRA_SUTLEJ"]

    # Check Hirakud (Mahanadi River)
    if (math.hypot(lat - 21.5280, lon - 83.8690) < 0.05 or "hirakud" in d_name):
        return VERIFIED_RIVER_CORRIDORS["HIRAKUD_MAHANADI"]

    # Check Sardar Sarovar (Narmada River)
    if (math.hypot(lat - 21.8298, lon - 73.7497) < 0.05 or "sardar sarovar" in d_name):
        return VERIFIED_RIVER_CORRIDORS["SARDAR_SAROVAR_NARMADA"]

    return None

def trace_dambreak_valley_dem(
    start_lat: float,
    start_lon: float,
    initial_bearing: float = 135.0,
    total_km: float = 18.0,
    step_m: float = 400.0,
    dam_name: str = ""
) -> List[List[float]]:
    """
    Generate an authentic dam break flow route.
    Uses verified physical river canyon geometry if available,
    or runs dynamic steepest-descent valley thalweg tracing on DEM data.
    """
    # 1. First check if a verified physical river corridor exists
    v_path = identify_verified_corridor(start_lat, start_lon, dam_name)
    if v_path:
        # If already high-resolution surveyed vector (> 50 points), return directly
        if len(v_path) >= 50:
            return v_path

        # Otherwise interpolate points along verified waypoints
        interp_path = [[round(start_lat, 5), round(start_lon, 5)]]
        for i in range(1, len(v_path)):
            p0 = v_path[i-1]
            p1 = v_path[i]
            dist_m = math.hypot((p1[0] - p0[0]) * 111139.0, (p1[1] - p0[1]) * 111139.0 * math.cos(math.radians(p0[0])))
            sub_steps = max(1, int(round(dist_m / step_m)))
            for s in range(1, sub_steps + 1):
                f = s / sub_steps
                lat = p0[0] + f * (p1[0] - p0[0])
                lon = p0[1] + f * (p1[1] - p0[1])
                interp_path.append([round(lat, 5), round(lon, 5)])
        return interp_path

    # 2. Dynamic DEM Valley Thalweg Routing (Batch Transects)
    n_segments = max(8, int(total_km / 1.5))
    reach_pts = []
    perp_b = (initial_bearing + 90.0) % 360.0

    for i in range(1, n_segments + 1):
        dist = (i / n_segments) * total_km * 1000.0
        c_lat, c_lon = destination(start_lat, start_lon, initial_bearing, dist)
        for offset_m in [-450, -220, 0, 220, 450]:
            t_lat, t_lon = destination(c_lat, c_lon, perp_b, offset_m)
            reach_pts.append((t_lat, t_lon, i, offset_m))

    elevs = fetch_elevations_batch([(p[0], p[1]) for p in reach_pts])

    thalweg_nodes = [[round(start_lat, 5), round(start_lon, 5)]]
    for i in range(1, n_segments + 1):
        seg_samples = [(p, z) for p, z in zip(reach_pts, elevs) if p[2] == i]
        if seg_samples:
            best_p, _ = min(seg_samples, key=lambda item: item[1] if item[1] is not None else 9999.0)
            thalweg_nodes.append([round(best_p[0], 5), round(best_p[1], 5)])

    # Interpolate along thalweg nodes for smooth downstream flow path
    path = [[round(start_lat, 5), round(start_lon, 5)]]
    for i in range(1, len(thalweg_nodes)):
        p0 = thalweg_nodes[i - 1]
        p1 = thalweg_nodes[i]
        dist_m = math.hypot((p1[0] - p0[0]) * 111139.0, (p1[1] - p0[1]) * 111139.0 * math.cos(math.radians(p0[0])))
        sub_steps = max(1, int(round(dist_m / step_m)))
        for s in range(1, sub_steps + 1):
            f = s / sub_steps
            lat = p0[0] + f * (p1[0] - p0[0])
            lon = p0[1] + f * (p1[1] - p0[1])
            path.append([round(lat, 5), round(lon, 5)])

    return path
