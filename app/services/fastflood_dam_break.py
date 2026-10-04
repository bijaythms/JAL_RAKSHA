"""
FastFlood Dam-Break Visualization & 2D Inundation Engine.
Integrates the hackathon FastFlood steady-state HAND + Manning's inversion model
with high-resolution Leaflet / Folium interactive maps, Google Hybrid / ESRI basemaps,
NDMA risk classification, and raster image overlays.
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List
import numpy as np

# Ensure hackathon engine is on path
_HACKATHON_DIR = Path(__file__).resolve().parent / "hackathon_engine"
if str(_HACKATHON_DIR) not in sys.path:
    sys.path.insert(0, str(_HACKATHON_DIR))

from visualization.flood_map_plot import (
    depth_to_rgba,
    risk_to_rgba,
    velocity_to_rgba,
    _array_to_base64_png,
    create_interactive_map,
    plot_flood_depth,
    RISK_CLASS_COLORS,
    RISK_LABELS,
)




def simulate_dam_break_fastflood(
    dam_lat: float,
    dam_lon: float,
    centerline: List[List[float]],
    peak_Q_m3s: float,
    stored_volume_m3: float,
    dam_height_m: float,
    valley_width_m: float = 90.0,
    bed_slope: float = 0.02,
    manning_n: float = 0.045,
    debris_bulking: float = 1.0,
    grid_size: int = 160,
    reach_buffer_deg: float = 0.06,
    dam_name: str = "Dam Break Scenario",
    output_html_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate high-resolution 2D FastFlood inundation raster, velocity field,
    NDMA risk classification, and interactive Google/ESRI map for a dam breach event.
    """
    # 1. Determine bounding box around dam and downstream reach
    lats = [dam_lat] + [pt[0] for pt in centerline]
    lons = [dam_lon] + [pt[1] for pt in centerline]

    min_lat = min(lats) - reach_buffer_deg
    max_lat = max(lats) + reach_buffer_deg
    min_lon = min(lons) - reach_buffer_deg
    max_lon = max(lons) + reach_buffer_deg

    bbox = (min_lon, min_lat, max_lon, max_lat)

    # 2. Build 2D geographic grid
    lat_arr = np.linspace(max_lat, min_lat, grid_size)
    lon_arr = np.linspace(min_lon, max_lon, grid_size)
    lon_grid, lat_grid = np.meshgrid(lon_arr, lat_arr)

    # 3. Calculate distance from every grid cell to the downstream flow centerline
    cl_pts = np.array([[dam_lat, dam_lon]] + centerline)
    dist_grid = np.full((grid_size, grid_size), 1e9, dtype=np.float32)
    chainage_grid = np.zeros((grid_size, grid_size), dtype=np.float32)

    # Compute distances in approximate metres (1 deg lat ~ 111 km, 1 deg lon ~ 111*cos(lat) km)
    cos_lat = np.cos(np.radians(dam_lat))
    scale_y = 111139.0
    scale_x = 111139.0 * cos_lat

    # Cumulative chainage along centerline
    cum_ch = [0.0]
    for i in range(1, len(cl_pts)):
        dy = (cl_pts[i, 0] - cl_pts[i - 1, 0]) * scale_y
        dx = (cl_pts[i, 1] - cl_pts[i - 1, 1]) * scale_x
        cum_ch.append(cum_ch[-1] + np.hypot(dx, dy))

    # Project cells onto centerline segments
    for i in range(len(cl_pts) - 1):
        p1 = cl_pts[i]
        p2 = cl_pts[i + 1]
        seg_dy = (p2[0] - p1[0]) * scale_y
        seg_dx = (p2[1] - p1[1]) * scale_x
        seg_len_sq = seg_dx**2 + seg_dy**2

        if seg_len_sq < 1.0:
            continue

        cy = (lat_grid - p1[0]) * scale_y
        cx = (lon_grid - p1[1]) * scale_x

        t = np.clip((cx * seg_dx + cy * seg_dy) / seg_len_sq, 0.0, 1.0)
        proj_x = cx - t * seg_dx
        proj_y = cy - t * seg_dy
        d = np.hypot(proj_x, proj_y)

        closer = d < dist_grid
        dist_grid[closer] = d[closer]
        chainage_grid[closer] = cum_ch[i] + t[closer] * np.sqrt(seg_len_sq)

    # 4. Discharge attenuation along reach (Muskingum decay)
    total_reach = cum_ch[-1] if cum_ch[-1] > 100 else 10000.0
    decay = np.exp(-0.000035 * chainage_grid)  # gradual peak decay downstream
    Q_local = peak_Q_m3s * debris_bulking * decay

    # 5. Manning's normal depth along main channel:
    # h = [ Q * n / (W * S^0.5) ]^(3/5)
    S0 = max(bed_slope, 0.0005)
    W = max(valley_width_m, 20.0)
    n = max(manning_n, 0.02)
    h_channel = (Q_local * n / (W * np.sqrt(S0))) ** 0.6
    h_channel = np.clip(h_channel, 0.1, dam_height_m * 1.2)

    # 6. HAND (Height Above Nearest Drainage) floodplain spread
    # Synthetic terrain: parabolic valley slope away from centerline
    # z_hand(d) = (d / (W * 1.5))^1.8
    valley_spread = W * 2.2
    hand_grid = (dist_grid / valley_spread) ** 1.65

    # Inundation depth: d_flood = max(0, h_channel - HAND)
    flood_depth = np.maximum(0.0, h_channel - hand_grid)
    flood_depth[dist_grid > (valley_spread * 2.5)] = 0.0

    # 7. Velocity field: v = Q / (W * h) in channel, lower on fringes
    velocity = np.zeros_like(flood_depth)
    wet = flood_depth > 0.02
    velocity[wet] = (1.0 / n) * (flood_depth[wet] ** (2.0 / 3.0)) * np.sqrt(S0)
    velocity[wet] = np.clip(velocity[wet], 0.2, 12.0)

    # 8. NDMA Risk Classification (0 to 4)
    # Class 0: < 0.10 m (dry)
    # Class 1: 0.10 - 0.30 m (Low)
    # Class 2: 0.30 - 1.00 m (Medium)
    # Class 3: 1.00 - 2.00 m (High)
    # Class 4: > 2.00 m (Extreme)
    risk_class = np.zeros_like(flood_depth, dtype=np.uint8)
    risk_class[flood_depth >= 0.10] = 1
    risk_class[flood_depth >= 0.30] = 2
    risk_class[flood_depth >= 1.00] = 3
    risk_class[flood_depth >= 2.00] = 4

    # 9. Statistics
    cell_area_km2 = (reach_buffer_deg * 2 * 111.139 / grid_size) ** 2
    wet_cells = np.sum(wet)
    inundated_area_km2 = round(float(wet_cells * cell_area_km2), 2)
    max_d = round(float(np.max(flood_depth)), 2)
    mean_d = round(float(np.mean(flood_depth[wet])) if np.any(wet) else 0.0, 2)
    max_v = round(float(np.max(velocity)), 2)

    risk_counts = {
        "class_0_dry": int(np.sum(risk_class == 0)),
        "class_1_low": int(np.sum(risk_class == 1)),
        "class_2_medium": int(np.sum(risk_class == 2)),
        "class_3_high": int(np.sum(risk_class == 3)),
        "class_4_extreme": int(np.sum(risk_class == 4)),
    }
    high_risk_area_km2 = round(float((risk_counts["class_3_high"] + risk_counts["class_4_extreme"]) * cell_area_km2), 2)

    stats = {
        "dam_name": dam_name,
        "peak_discharge_m3s": round(peak_Q_m3s * debris_bulking, 1),
        "total_inundated_area_km2": inundated_area_km2,
        "max_depth_m": max_d,
        "mean_depth_m": mean_d,
        "max_velocity_ms": max_v,
        "high_risk_area_km2": high_risk_area_km2,
        "risk_breakdown": risk_counts,
        "engine": "FastFlood 5-Step Steady-State HAND + Manning Inversion (van den Bout et al. 2026)"
    }

    # 10. Generate RGBA base64 PNG overlays
    rgba_depth = depth_to_rgba(flood_depth, vmax=max(max_d, 2.0))
    b64_depth = _array_to_base64_png(rgba_depth)

    rgba_risk = risk_to_rgba(flood_depth)
    b64_risk = _array_to_base64_png(rgba_risk)

    rgba_vel = velocity_to_rgba(velocity, vmax=max(max_v, 3.0))
    b64_vel = _array_to_base64_png(rgba_vel)

    # 11. Generate Interactive HTML map with Google Hybrid / ESRI
    if output_html_path:
        os.makedirs(os.path.dirname(output_html_path), exist_ok=True)
        create_interactive_map(
            flood_depth=flood_depth,
            bbox=bbox,
            output_path=output_html_path,
            velocity=velocity,
            stats=stats,
            title=f"FastFlood 2D Dam-Break: {dam_name}",
            default_basemap="google_hybrid"
        )

    return {
        "bbox": [min_lat, min_lon, max_lat, max_lon],
        "bounds_leaflet": [[min_lat, min_lon], [max_lat, max_lon]],
        "stats": stats,
        "overlays": {
            "depth_b64": b64_depth,
            "risk_b64": b64_risk,
            "velocity_b64": b64_vel,
        },
        "html_map_path": output_html_path,
        "risk_labels": RISK_LABELS
    }
