"""
Flood Map Assembly — Final Output Generation

Assembles the outputs from all 5 modelling steps into a coherent
flood hazard map with:
  - Flood depth raster (GeoTIFF)
  - Flood velocity raster (GeoTIFF)
  - Risk classification raster (Low/Medium/High/Extreme)
  - Summary statistics
  - JSON metadata for downstream use
"""

import numpy as np
import rasterio
import json
import logging
from pathlib import Path
from typing import Tuple, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Risk Classification Thresholds
# ---------------------------------------------------------------------------

# Based on NDMA India flood hazard guidelines and EU FD 2007/60/EC
RISK_THRESHOLDS = {
    "dry":     (0.0,  0.1),    # No significant flood
    "low":     (0.1,  0.3),    # Low hazard (ankle deep)
    "medium":  (0.3,  1.0),    # Medium hazard (knee to waist deep)
    "high":    (1.0,  2.0),    # High hazard (above waist, dangerous)
    "extreme": (2.0, float("inf")),  # Extreme — life-threatening
}

# RGB colours for risk map rendering
RISK_COLORS = {
    0: (255, 255, 255, 0),    # Dry (transparent)
    1: (255, 255, 0, 180),    # Low (yellow)
    2: (255, 165, 0, 200),    # Medium (orange)
    3: (255, 0, 0, 220),      # High (red)
    4: (128, 0, 128, 240),    # Extreme (purple)
}


def classify_risk(flood_depth: np.ndarray) -> np.ndarray:
    """
    Classify flood depth into risk categories.

    Returns integer array:
      0 = Dry
      1 = Low    (0.1 – 0.3 m)
      2 = Medium (0.3 – 1.0 m)
      3 = High   (1.0 – 2.0 m)
      4 = Extreme (> 2.0 m)

    Args:
        flood_depth: 2D float array of flood depth (metres)

    Returns:
        2D uint8 risk class array
    """
    risk = np.zeros_like(flood_depth, dtype=np.uint8)
    risk = np.where(flood_depth >= 0.1, 1, risk)
    risk = np.where(flood_depth >= 0.3, 2, risk)
    risk = np.where(flood_depth >= 1.0, 3, risk)
    risk = np.where(flood_depth >= 2.0, 4, risk)
    return risk


def compute_summary_statistics(
    flood_depth: np.ndarray,
    velocity: np.ndarray,
    risk: np.ndarray,
    meta: dict,
    rainfall_mm: float,
    duration_hr: float,
) -> Dict:
    """
    Compute comprehensive summary statistics for the flood simulation.

    Args:
        flood_depth: 2D flood depth array (m)
        velocity: 2D flow velocity array (m/s)
        risk: 2D risk class array
        meta: DEM metadata dict
        rainfall_mm: Input rainfall (mm)
        duration_hr: Event duration (hours)

    Returns:
        Dictionary of statistics
    """
    flooded_mask = flood_depth > 0.01
    n_total = flood_depth.size
    n_flooded = int(np.sum(flooded_mask))

    # Cell area in km²
    dx, dy = meta.get("res", (30, 30))
    if meta.get("crs", None) and hasattr(meta["crs"], "is_geographic"):
        if meta["crs"].is_geographic:
            bounds = meta.get("bounds")
            if bounds:
                mid_lat = (bounds.bottom + bounds.top) / 2.0
                lat_rad = np.radians(mid_lat)
                dx_m = abs(dx) * 111412.84 * np.cos(lat_rad)
                dy_m = abs(dy) * 111132.92
                cell_area_km2 = (dx_m * dy_m) / 1e6
            else:
                cell_area_km2 = 0.0009  # ~30m cells
        else:
            cell_area_km2 = (abs(dx) * abs(dy)) / 1e6
    else:
        cell_area_km2 = 0.0009

    total_area_km2 = n_total * cell_area_km2
    flooded_area_km2 = n_flooded * cell_area_km2

    risk_counts = {
        "dry": int(np.sum(risk == 0)),
        "low": int(np.sum(risk == 1)),
        "medium": int(np.sum(risk == 2)),
        "high": int(np.sum(risk == 3)),
        "extreme": int(np.sum(risk == 4)),
    }
    risk_areas_km2 = {k: v * cell_area_km2 for k, v in risk_counts.items()}

    stats = {
        "simulation_time": datetime.now().isoformat(),
        "input": {
            "rainfall_mm": round(rainfall_mm, 2),
            "duration_hr": round(duration_hr, 2),
            "intensity_mm_hr": round(rainfall_mm / max(duration_hr, 0.1), 2),
        },
        "domain": {
            "total_cells": n_total,
            "total_area_km2": round(total_area_km2, 3),
        },
        "flood_extent": {
            "flooded_cells": n_flooded,
            "flooded_area_km2": round(flooded_area_km2, 3),
            "flood_fraction_pct": round(100 * n_flooded / max(n_total, 1), 2),
        },
        "depth_stats_m": {
            "max": round(float(np.nanmax(flood_depth)), 3),
            "mean_flooded": round(float(np.nanmean(flood_depth[flooded_mask])), 3) if n_flooded > 0 else 0.0,
            "p75_flooded": round(float(np.nanpercentile(flood_depth[flooded_mask], 75)), 3) if n_flooded > 0 else 0.0,
            "p95_flooded": round(float(np.nanpercentile(flood_depth[flooded_mask], 95)), 3) if n_flooded > 0 else 0.0,
        },
        "velocity_stats_m_per_s": {
            "max": round(float(np.nanmax(velocity)), 3),
            "mean_flooded": round(float(np.nanmean(velocity[flooded_mask])), 3) if n_flooded > 0 else 0.0,
        },
        "risk_classes": {
            "counts": risk_counts,
            "areas_km2": {k: round(v, 3) for k, v in risk_areas_km2.items()},
        },
    }

    return stats


def save_flood_outputs(
    flood_depth: np.ndarray,
    velocity: np.ndarray,
    hand: np.ndarray,
    risk: np.ndarray,
    meta: dict,
    output_dir: str,
    prefix: str = "flood",
) -> Dict[str, str]:
    """
    Save all flood output rasters to GeoTIFF files.

    Args:
        flood_depth: 2D flood depth (m)
        velocity: 2D velocity (m/s)
        hand: 2D HAND (m)
        risk: 2D risk class (uint8)
        meta: DEM metadata dict
        output_dir: Output directory path
        prefix: Filename prefix

    Returns:
        Dictionary of {layer_name: file_path}
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    paths = {}

    base_profile = {
        "driver": "GTiff",
        "count": 1,
        "width": meta["width"],
        "height": meta["height"],
        "crs": meta["crs"],
        "transform": meta["transform"],
        "compress": "lzw",
    }

    def _write(arr, name, dtype, nodata_val):
        path = str(Path(output_dir) / f"{prefix}_{name}.tif")
        profile = {**base_profile, "dtype": dtype, "nodata": nodata_val}
        out = np.where(np.isnan(arr), nodata_val, arr).astype(dtype)
        with rasterio.open(path, "w", **profile) as dst:
            dst.write(out, 1)
            dst.update_tags(LAYER=name, UNITS="metres" if "depth" in name or name == "hand" else "m/s" if "velocity" in name else "class")
        logger.info(f"Saved {name}: {path}")
        paths[name] = path

    _write(flood_depth, "depth_m",    "float32", -9999.0)
    _write(velocity,   "velocity_ms", "float32", -9999.0)
    _write(hand,       "hand_m",      "float32", -9999.0)
    _write(risk.astype(np.float32), "risk_class", "float32", 255.0)

    return paths


def save_simulation_report(
    stats: Dict,
    output_dir: str,
    prefix: str = "flood",
) -> str:
    """
    Save simulation summary statistics as a JSON report.

    Args:
        stats: Statistics dict from compute_summary_statistics()
        output_dir: Output directory
        prefix: Filename prefix

    Returns:
        Path to saved JSON file
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    report_path = str(Path(output_dir) / f"{prefix}_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    logger.info(f"Simulation report saved: {report_path}")
    return report_path


def print_summary(stats: Dict) -> None:
    """Print a human-readable flood simulation summary (ASCII-safe for Windows)."""
    inp  = stats["input"]
    ext  = stats["flood_extent"]
    dep  = stats["depth_stats_m"]
    risk = stats["risk_classes"]

    sep = "=" * 60
    print("\n" + sep)
    print("  INDIA FLOOD INUNDATION MODEL - SIMULATION SUMMARY")
    print(sep)
    print(f"  Input Rainfall : {inp['rainfall_mm']:.1f} mm over {inp['duration_hr']:.1f} hr"
          f"  ({inp['intensity_mm_hr']:.1f} mm/hr)")
    print(f"  Domain Area    : {stats['domain']['total_area_km2']:.1f} km2")
    print(f"  Flooded Area   : {ext['flooded_area_km2']:.2f} km2"
          f"  ({ext['flood_fraction_pct']:.1f}% of domain)")
    print(f"\n  Flood Depth (flooded cells):")
    print(f"    Max          : {dep['max']:.2f} m")
    print(f"    Mean         : {dep['mean_flooded']:.2f} m")
    print(f"    75th pctile  : {dep['p75_flooded']:.2f} m")
    print(f"    95th pctile  : {dep['p95_flooded']:.2f} m")
    print(f"\n  Risk Class Areas:")
    total_area = max(stats['domain']['total_area_km2'], 1)
    for cls, area in risk["areas_km2"].items():
        bar_len = int(area / total_area * 30)
        bar = "#" * bar_len   # ASCII-safe bar
        print(f"    {cls.upper():8s}: {area:8.2f} km2  {bar}")
    print(sep + "\n")
