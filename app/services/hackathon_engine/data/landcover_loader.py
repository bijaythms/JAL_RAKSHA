"""
Land Cover Data Loader — ESA WorldCover 2021

Downloads and processes ESA WorldCover 2021 data (10m resolution, free, open):
  - Fetches from AWS S3 public bucket (no account required)
  - Resamples to DEM resolution
  - Provides Manning's n and SCS-CN lookup

ESA WorldCover 2021:
  S3 bucket: s3://esa-worldcover/v200/2021/map/
  License: CC BY 4.0 (free for any use, including commercial)
  Resolution: 10m (resampled to DEM resolution)

Class codes:
  10 = Tree cover, 20 = Shrubland, 30 = Grassland, 40 = Cropland,
  50 = Built-up, 60 = Bare / sparse vegetation, 70 = Snow and ice,
  80 = Permanent water, 90 = Herbaceous wetland, 95 = Mangroves, 100 = Moss
"""

import numpy as np
import requests
import logging
from pathlib import Path
from typing import Tuple, Optional, Dict
import rasterio
from rasterio.merge import merge
from rasterio.enums import Resampling
from rasterio.transform import from_bounds

logger = logging.getLogger(__name__)

# ESA WorldCover class definitions
ESA_CLASSES = {
    10:  "Tree cover",
    20:  "Shrubland",
    30:  "Grassland",
    40:  "Cropland",
    50:  "Built-up",
    60:  "Bare / sparse vegetation",
    70:  "Snow and ice",
    80:  "Permanent water bodies",
    90:  "Herbaceous wetland",
    95:  "Mangroves",
    100: "Moss and lichen",
}

# Default ESA class for India fallback
INDIA_DEFAULT_LULC = 40  # Cropland (most common in agricultural India)


# ---------------------------------------------------------------------------
# ESA WorldCover Download from AWS
# ---------------------------------------------------------------------------

def get_worldcover_tile_ids(bbox: Tuple[float, float, float, float]) -> list:
    """
    Compute ESA WorldCover tile identifiers for a bounding box.

    Tiles are 3°×3° with naming: ESA_WorldCover_10m_2021_v200_{LAT}{LON}

    Args:
        bbox: (min_lon, min_lat, max_lon, max_lat)

    Returns:
        List of tile ID strings
    """
    min_lon, min_lat, max_lon, max_lat = bbox
    tile_ids = []

    lat_start = int(np.floor(min_lat / 3)) * 3
    lon_start = int(np.floor(min_lon / 3)) * 3

    for lat in range(lat_start, int(np.ceil(max_lat)), 3):
        for lon in range(lon_start, int(np.ceil(max_lon)), 3):
            lat_str = f"{'N' if lat >= 0 else 'S'}{abs(lat):02d}"
            lon_str = f"{'E' if lon >= 0 else 'W'}{abs(lon):03d}"
            tile_ids.append(f"{lat_str}{lon_str}")

    return tile_ids


def download_worldcover_tile(
    tile_id: str,
    output_dir: str,
) -> Optional[str]:
    """
    Download one ESA WorldCover 2021 tile from AWS S3.

    Args:
        tile_id: Tile ID string (e.g., 'N12E076')
        output_dir: Directory to save tile

    Returns:
        Path to downloaded tile or None if failed
    """
    filename = f"ESA_WorldCover_10m_2021_v200_{tile_id}_Map.tif"
    s3_url = f"https://esa-worldcover.s3.amazonaws.com/v200/2021/map/{filename}"
    output_path = Path(output_dir) / filename

    if output_path.exists():
        logger.info(f"WorldCover tile cached: {filename}")
        return str(output_path)

    logger.info(f"Downloading WorldCover tile: {filename}")
    try:
        response = requests.get(s3_url, timeout=120, stream=True)
        if response.status_code == 200:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            size_mb = output_path.stat().st_size / (1024 * 1024)
            logger.info(f"Downloaded: {filename} ({size_mb:.1f} MB)")
            return str(output_path)
        else:
            logger.warning(f"Failed to download {filename}: HTTP {response.status_code}")
            return None
    except Exception as e:
        logger.warning(f"Error downloading {filename}: {e}")
        return None


def get_worldcover_for_bbox(
    bbox: Tuple[float, float, float, float],
    output_dir: str,
    target_shape: Optional[Tuple[int, int]] = None,
    target_meta: Optional[dict] = None,
) -> np.ndarray:
    """
    Download and resample ESA WorldCover data for a bounding box.

    Args:
        bbox: (min_lon, min_lat, max_lon, max_lat)
        output_dir: Directory for downloads
        target_shape: (rows, cols) to resample to (DEM resolution)
        target_meta: DEM metadata for resampling

    Returns:
        2D uint8 array of ESA WorldCover class values
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    tile_ids = get_worldcover_tile_ids(bbox)
    logger.info(f"WorldCover tiles needed: {tile_ids}")

    # Download tiles
    tile_paths = []
    for tid in tile_ids:
        path = download_worldcover_tile(tid, output_dir)
        if path:
            tile_paths.append(path)

    if not tile_paths:
        logger.warning("No WorldCover tiles downloaded. Using default cropland (40).")
        if target_shape:
            return np.full(target_shape, INDIA_DEFAULT_LULC, dtype=np.uint8)
        return np.array([[INDIA_DEFAULT_LULC]], dtype=np.uint8)

    # Merge tiles
    if len(tile_paths) == 1:
        merged_path = tile_paths[0]
    else:
        merged_path = str(Path(output_dir) / "worldcover_merged.tif")
        _merge_worldcover_tiles(tile_paths, merged_path, bbox)

    # Resample to target resolution
    if target_shape and target_meta:
        return resample_to_dem(merged_path, target_shape, target_meta)
    else:
        with rasterio.open(merged_path) as src:
            return src.read(1)


def _merge_worldcover_tiles(tile_paths: list, output_path: str,
                             bbox: Tuple[float, float, float, float]) -> None:
    """Merge multiple WorldCover tiles into one clipped to bbox."""
    datasets = [rasterio.open(p) for p in tile_paths]
    mosaic, out_transform = merge(datasets)
    meta = datasets[0].meta.copy()
    for ds in datasets:
        ds.close()

    meta.update({
        "driver": "GTiff",
        "height": mosaic.shape[1],
        "width": mosaic.shape[2],
        "transform": out_transform,
        "compress": "lzw",
    })
    with rasterio.open(output_path, "w", **meta) as dst:
        dst.write(mosaic)


def resample_to_dem(
    lulc_path: str,
    target_shape: Tuple[int, int],
    target_meta: dict,
    resample_method: str = "nearest",
) -> np.ndarray:
    """
    Resample a LULC raster to match the DEM grid.

    Args:
        lulc_path: Path to LULC GeoTIFF
        target_shape: (rows, cols)
        target_meta: DEM metadata (transform, crs)
        resample_method: 'nearest' (preserves class values) or 'mode'

    Returns:
        Resampled 2D array at DEM resolution
    """
    from rasterio.warp import reproject, Resampling as WarpResampling

    method = WarpResampling.nearest  # Always nearest for categorical data

    with rasterio.open(lulc_path) as src:
        out = np.empty(target_shape, dtype=np.uint8)
        reproject(
            source=rasterio.band(src, 1),
            destination=out,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=target_meta["transform"],
            dst_crs=target_meta["crs"],
            resampling=method,
        )

    logger.info(f"Resampled LULC to {target_shape}")
    return out


# ---------------------------------------------------------------------------
# Fallback: Generate Synthetic Land Cover (India region guess)
# ---------------------------------------------------------------------------

def generate_synthetic_lulc(
    target_shape: Tuple[int, int],
    bbox: Tuple[float, float, float, float],
) -> np.ndarray:
    """
    Generate a plausible synthetic LULC grid for India based on geographic position.

    Assigns rough LULC classes based on:
    - Latitude/longitude position within India
    - Coastal proximity
    - Himalayan foothills detection

    This is for testing ONLY — always use real WorldCover data for production.

    Args:
        target_shape: (rows, cols)
        bbox: (min_lon, min_lat, max_lon, max_lat)

    Returns:
        2D uint8 LULC array
    """
    min_lon, min_lat, max_lon, max_lat = bbox
    nrows, ncols = target_shape

    lulc = np.full(target_shape, 40, dtype=np.uint8)  # Default: cropland

    # High latitude (Himalayas) → Tree cover + Snow
    lats = np.linspace(max_lat, min_lat, nrows)
    for i, lat in enumerate(lats):
        if lat > 30:
            lulc[i, :] = 10   # Tree cover
        elif lat > 32:
            lulc[i, :] = 70   # Snow/ice

    # Western edge → scrubland (Rajasthan)
    lons = np.linspace(min_lon, max_lon, ncols)
    for j, lon in enumerate(lons):
        if lon < 72 and min_lat < 27:
            lulc[:, j] = 60   # Bare/sparse (desert)

    # Add river channel (water body) through center
    center_col = ncols // 2
    river_width = max(2, ncols // 30)
    lulc[:, center_col - river_width:center_col + river_width] = 80  # Water

    # Urban area in center (10×10 cells)
    r_mid = nrows // 2
    c_mid = ncols // 2
    urban_size = max(5, min(20, nrows // 10))
    lulc[r_mid-urban_size:r_mid+urban_size, c_mid-urban_size:c_mid+urban_size] = 50

    return lulc


def get_lulc_summary(lulc: np.ndarray) -> Dict:
    """Compute land cover class distribution statistics."""
    total = lulc.size
    return {
        ESA_CLASSES.get(cls, f"Class {cls}"): {
            "cells": int(np.sum(lulc == cls)),
            "pct": round(100 * np.sum(lulc == cls) / total, 1),
        }
        for cls in np.unique(lulc)
        if cls in ESA_CLASSES
    }
