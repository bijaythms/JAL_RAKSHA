"""
Soil Data Loader — Hydrologic Soil Group (HSG) from SoilGrids

Fetches and processes soil texture / HSG data from:
  1. SoilGrids (ISRIC) — Global 250m resolution soil data (free, open access)
  2. FAO HWSD (Harmonized World Soil Database) — 1km resolution
  3. Local HSG raster (if provided by user)

SoilGrids API: https://rest.soilgrids.org/soilgrids/v2.0/

Soil properties fetched:
  - clay: Clay fraction (%) — key indicator for HSG D
  - sand: Sand fraction (%) — key indicator for HSG A
  - silt: Silt fraction (%)
  - bdod: Bulk density (cg/cm³)
  - ocs: Organic carbon stock

HSG Classification:
  A: Sand, loamy sand, sandy loam (Ksat > 7.6 µm/s)
  B: Silt loam, loam (Ksat 3.8–7.6 µm/s)
  C: Sandy clay loam (Ksat 1.3–3.8 µm/s)
  D: Clay loam, silty clay loam, sandy clay, silty clay, clay (Ksat < 1.3 µm/s)
"""

import numpy as np
import requests
import logging
from pathlib import Path
from typing import Tuple, Optional, Dict
import rasterio
from rasterio.transform import from_bounds

logger = logging.getLogger(__name__)

# SoilGrids REST API endpoint
SOILGRIDS_API = "https://rest.soilgrids.org/soilgrids/v2.0/properties/query"

# HSG index: A=0, B=1, C=2, D=3
HSG_INDEX = {"A": 0, "B": 1, "C": 2, "D": 3}


# ---------------------------------------------------------------------------
# HSG Classification from Texture
# ---------------------------------------------------------------------------

def classify_hsg_from_texture(
    clay_pct: float,
    sand_pct: float,
    silt_pct: float = None,
) -> str:
    """
    Classify Hydrologic Soil Group from soil texture.

    Classification based on USDA-NRCS methodology adapted for India.
    Reference: NRCS Engineering Field Handbook Part 630 Chapter 7

    Args:
        clay_pct: Clay content (%)
        sand_pct: Sand content (%)
        silt_pct: Silt content (%)

    Returns:
        HSG: 'A', 'B', 'C', or 'D'
    """
    if silt_pct is None:
        silt_pct = max(0, 100 - clay_pct - sand_pct)

    # HSG D: High clay content (> 40%) → very low infiltration
    if clay_pct >= 40:
        return "D"

    # HSG C: Sandy clay loam region
    if clay_pct >= 20 and sand_pct <= 45:
        return "C"

    # HSG B: Silt loam / loam
    if silt_pct >= 50 or (clay_pct >= 10 and clay_pct < 20 and silt_pct >= 28):
        return "B"

    # HSG A: Sandy soils
    if sand_pct >= 70:
        return "A"

    # Default: B (moderate)
    return "B"


def classify_hsg_grid(
    clay_grid: np.ndarray,
    sand_grid: np.ndarray,
    silt_grid: Optional[np.ndarray] = None,
) -> np.ndarray:
    """
    Classify HSG for each grid cell.

    Args:
        clay_grid: 2D clay percentage array
        sand_grid: 2D sand percentage array
        silt_grid: 2D silt percentage array (computed if None)

    Returns:
        2D uint8 HSG index array (0=A, 1=B, 2=C, 3=D)
    """
    if silt_grid is None:
        silt_grid = np.maximum(100.0 - clay_grid - sand_grid, 0.0)

    rows, cols = clay_grid.shape
    hsg_idx = np.ones((rows, cols), dtype=np.uint8)  # Default: B

    # Vectorized classification
    hsg_idx = np.where(clay_grid >= 40, 3, hsg_idx)  # D
    hsg_idx = np.where(
        (clay_grid >= 20) & (clay_grid < 40) & (sand_grid <= 45),
        2, hsg_idx
    )  # C
    hsg_idx = np.where(
        (silt_grid >= 50) | ((clay_grid >= 10) & (clay_grid < 20) & (silt_grid >= 28)),
        1, hsg_idx
    )  # B
    hsg_idx = np.where(sand_grid >= 70, 0, hsg_idx)  # A

    logger.info(
        f"HSG classification: A={np.sum(hsg_idx==0)}, B={np.sum(hsg_idx==1)}, "
        f"C={np.sum(hsg_idx==2)}, D={np.sum(hsg_idx==3)} cells"
    )
    return hsg_idx


# ---------------------------------------------------------------------------
# India-Specific Soil Defaults by State/Region
# ---------------------------------------------------------------------------

# Default HSG for major Indian soil orders (fallback when no data available)
INDIA_SOIL_DEFAULTS_HSG = {
    # Black cotton / Vertisols (Regur) — shrink-swell clay
    "black_cotton":  {"clay": 55, "sand": 10, "silt": 35, "hsg": "D"},
    # Alluvial (Indo-Gangetic plain)
    "alluvial_light": {"clay": 15, "sand": 50, "silt": 35, "hsg": "B"},
    "alluvial_heavy": {"clay": 30, "sand": 25, "silt": 45, "hsg": "C"},
    # Red loam (Deccan Plateau)
    "red_loam":      {"clay": 25, "sand": 35, "silt": 40, "hsg": "C"},
    # Laterite (Kerala, Karnataka, Goa)
    "laterite":      {"clay": 40, "sand": 30, "silt": 30, "hsg": "D"},
    # Sandy desert (Rajasthan)
    "desert_sand":   {"clay": 5,  "sand": 90, "silt": 5,  "hsg": "A"},
    # Hill forest soils
    "hill_forest":   {"clay": 20, "sand": 40, "silt": 40, "hsg": "B"},
    # Coastal saline
    "coastal_saline": {"clay": 45, "sand": 10, "silt": 45, "hsg": "D"},
}


# ---------------------------------------------------------------------------
# SoilGrids API Fetch (Point Query)
# ---------------------------------------------------------------------------

def fetch_soil_point(lat: float, lon: float) -> Dict:
    """
    Fetch soil texture data for a point from SoilGrids REST API.

    Args:
        lat: Latitude
        lon: Longitude

    Returns:
        Dict with clay, sand, silt percentages and derived HSG
    """
    params = {
        "lon": lon,
        "lat": lat,
        "property": ["clay", "sand", "silt"],
        "depth": ["0-5cm"],
        "value": ["mean"],
    }

    try:
        response = requests.get(SOILGRIDS_API, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        logger.warning(f"SoilGrids API error at ({lat},{lon}): {e}. Using defaults.")
        return {"clay": 25, "sand": 35, "silt": 40, "hsg": "B", "source": "default"}

    props = data.get("properties", {})

    def _extract(key):
        try:
            return props[key]["layers"][0]["depths"][0]["values"]["mean"]
        except (KeyError, IndexError):
            return None

    clay = _extract("clay")
    sand = _extract("sand")
    silt = _extract("silt")

    # SoilGrids returns values × 10 (g/kg → divide by 10 for %)
    clay = clay / 10.0 if clay is not None else 25.0
    sand = sand / 10.0 if sand is not None else 35.0
    silt = silt / 10.0 if silt is not None else 40.0

    hsg = classify_hsg_from_texture(clay, sand, silt)
    return {"clay": clay, "sand": sand, "silt": silt, "hsg": hsg, "source": "soilgrids"}


# ---------------------------------------------------------------------------
# Gridded HSG Generation for Model Domain
# ---------------------------------------------------------------------------

def generate_hsg_grid(
    bbox: Tuple[float, float, float, float],
    target_shape: Tuple[int, int],
    output_path: Optional[str] = None,
    meta: Optional[dict] = None,
    api_sample_points: int = 4,
    india_default_hsg: int = 1,  # B = 1 (most common in India)
) -> np.ndarray:
    """
    Generate a gridded HSG array for the model domain.

    Samples SoilGrids at a coarse grid, then interpolates to DEM resolution.

    Args:
        bbox: (min_lon, min_lat, max_lon, max_lat)
        target_shape: (rows, cols) of DEM grid
        output_path: Optional path to save HSG GeoTIFF
        meta: DEM metadata for saving
        api_sample_points: N×N grid of API sample points
        india_default_hsg: Default HSG index if API fails (1=B)

    Returns:
        2D uint8 HSG index array (0=A, 1=B, 2=C, 3=D)
    """
    min_lon, min_lat, max_lon, max_lat = bbox
    nrows, ncols = target_shape

    lats = np.linspace(min_lat, max_lat, api_sample_points)
    lons = np.linspace(min_lon, max_lon, api_sample_points)

    # Fetch soil data at sample points
    clay_samples = np.zeros((api_sample_points, api_sample_points))
    sand_samples = np.zeros((api_sample_points, api_sample_points))
    silt_samples = np.zeros((api_sample_points, api_sample_points))

    for i, lat in enumerate(lats):
        for j, lon in enumerate(lons):
            soil = fetch_soil_point(lat, lon)
            clay_samples[i, j] = soil["clay"]
            sand_samples[i, j] = soil["sand"]
            silt_samples[i, j] = soil["silt"]

    # Interpolate to DEM resolution
    from scipy.interpolate import RegularGridInterpolator

    def _interpolate(data):
        interp = RegularGridInterpolator(
            (lats, lons), data,
            method="linear", bounds_error=False,
            fill_value=float(np.mean(data)),
        )
        target_lats = np.linspace(max_lat, min_lat, nrows)  # N→S
        target_lons = np.linspace(min_lon, max_lon, ncols)
        grid_lons, grid_lats = np.meshgrid(target_lons, target_lats)
        return interp(np.column_stack([grid_lats.ravel(), grid_lons.ravel()])).reshape(target_shape)

    clay_grid = _interpolate(clay_samples)
    sand_grid = _interpolate(sand_samples)
    silt_grid = _interpolate(silt_samples)

    # Classify HSG
    hsg_idx = classify_hsg_grid(clay_grid, sand_grid, silt_grid)

    # Save if requested
    if output_path and meta:
        profile = {
            "driver": "GTiff", "dtype": "uint8",
            "count": 1, "width": ncols, "height": nrows,
            "crs": meta["crs"], "transform": meta["transform"],
            "nodata": 255, "compress": "lzw",
        }
        with rasterio.open(output_path, "w", **profile) as dst:
            dst.write(hsg_idx, 1)
        logger.info(f"HSG grid saved: {output_path}")

    return hsg_idx


def get_default_hsg_grid(
    target_shape: Tuple[int, int],
    default_hsg: int = 1,
) -> np.ndarray:
    """
    Generate uniform default HSG grid (for offline/testing use).

    Args:
        target_shape: (rows, cols)
        default_hsg: HSG index (0=A, 1=B, 2=C, 3=D)

    Returns:
        Uniform HSG index array
    """
    return np.full(target_shape, default_hsg, dtype=np.uint8)
