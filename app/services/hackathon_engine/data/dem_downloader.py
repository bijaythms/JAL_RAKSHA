"""
DEM Downloader — Automatic SRTM & Copernicus GLO-30 download

Supports:
  1. SRTM 30m via OpenTopography API (free, no account needed for small areas)
  2. Copernicus DEM GLO-30 via AWS S3 (public bucket)
  3. NASADEM via OpenTopography API
  4. Synthetic DEM generation (for testing without downloads)

All DEMs are clipped to the requested bounding box and saved as GeoTIFF.

The OpenTopography API has a free tier (no API key for small requests < 500 km²).
For larger areas, a free API key is available at: https://opentopography.org/
"""

import numpy as np
import requests
import logging
import os
from pathlib import Path
from typing import Tuple, Optional
import rasterio
from rasterio.transform import from_bounds

logger = logging.getLogger(__name__)

# OpenTopography API endpoint
OPENTOPOGRAPHY_API_URL = "https://portal.opentopography.org/API/globaldem"

# DEM type codes for OpenTopography
DEM_TYPES = {
    "srtmgl1":   "SRTMGL1",      # SRTM 30m (1 arc-sec)
    "srtmgl3":   "SRTMGL3",      # SRTM 90m (3 arc-sec)
    "nasadem":   "NASADEM",      # NASADEM (improved SRTM)
    "cop30":     "COP30",        # Copernicus DEM GLO-30
    "alos":      "AW3D30",       # ALOS World 3D 30m
}


def download_dem_opentopography(
    bbox: Tuple[float, float, float, float],
    output_path: str,
    dem_type: str = "nasadem",
    api_key: Optional[str] = None,
) -> str:
    """
    Download DEM from OpenTopography API.

    Args:
        bbox: (min_lon, min_lat, max_lon, max_lat) in WGS84
        output_path: Path to save the downloaded GeoTIFF
        dem_type: One of 'srtmgl1', 'nasadem', 'cop30', 'alos'
        api_key: Optional OpenTopography API key (for large areas)

    Returns:
        Path to downloaded DEM file
    """
    min_lon, min_lat, max_lon, max_lat = bbox
    dt_code = DEM_TYPES.get(dem_type, DEM_TYPES["nasadem"])

    params = {
        "demtype": dt_code,
        "south": min_lat,
        "north": max_lat,
        "west": min_lon,
        "east": max_lon,
        "outputFormat": "GTiff",
    }
    if api_key:
        params["API_Key"] = api_key

    logger.info(f"Downloading {dem_type.upper()} DEM for bbox={bbox}")
    logger.info(f"Request: {OPENTOPOGRAPHY_API_URL}?{params}")

    try:
        response = requests.get(OPENTOPOGRAPHY_API_URL, params=params,
                                timeout=300, stream=True)
        if response.status_code == 200:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            size_mb = Path(output_path).stat().st_size / (1024 * 1024)
            logger.info(f"DEM downloaded: {output_path} ({size_mb:.1f} MB)")
            return output_path
        else:
            raise RuntimeError(
                f"OpenTopography API error: {response.status_code} — {response.text[:200]}"
            )
    except requests.Timeout:
        raise RuntimeError("OpenTopography API timed out (300s). Try a smaller area.")


def download_copernicus_aws(
    bbox: Tuple[float, float, float, float],
    output_path: str,
    resolution: str = "30",
) -> str:
    """
    Download Copernicus DEM GLO-30 from AWS public S3 bucket.

    The Copernicus DEM tiles are publicly available at:
    s3://copernicus-dem-30m/{tile_name}/DEM/{tile_name}_DEM.tif

    Tile naming convention: Copernicus_DSM_COG_10_{LAT}_{LON}_00_DEM

    Args:
        bbox: (min_lon, min_lat, max_lon, max_lat)
        output_path: Output GeoTIFF path
        resolution: '30' (30m) or '90' (90m)

    Returns:
        Path to merged DEM file
    """
    try:
        import boto3
        from botocore import UNSIGNED
        from botocore.config import Config
    except ImportError:
        raise ImportError("boto3 required. pip install boto3")

    min_lon, min_lat, max_lon, max_lat = bbox

    # Determine tile IDs needed
    tiles_needed = []
    for lat in range(int(min_lat), int(max_lat) + 1):
        for lon in range(int(min_lon), int(max_lon) + 1):
            lat_str = f"{'N' if lat >= 0 else 'S'}{abs(lat):02d}"
            lon_str = f"{'E' if lon >= 0 else 'W'}{abs(lon):03d}"
            tiles_needed.append((lat_str, lon_str))

    bucket_name = f"copernicus-dem-{resolution}m"
    s3 = boto3.client("s3", config=Config(signature_version=UNSIGNED))

    downloaded_tiles = []
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    tmp_dir = Path(output_path).parent / "copernicus_tiles"
    tmp_dir.mkdir(exist_ok=True)

    for lat_str, lon_str in tiles_needed:
        tile_name = f"Copernicus_DSM_COG_10_{lat_str}_00_{lon_str}_00_DEM"
        s3_key = f"{tile_name}/DEM/{tile_name}.tif"
        tile_path = tmp_dir / f"{tile_name}.tif"

        try:
            s3.download_file(bucket_name, s3_key, str(tile_path))
            downloaded_tiles.append(str(tile_path))
            logger.info(f"Downloaded tile: {tile_name}")
        except Exception as e:
            logger.warning(f"Could not download tile {tile_name}: {e}")

    if not downloaded_tiles:
        raise RuntimeError("No Copernicus DEM tiles downloaded")

    if len(downloaded_tiles) == 1:
        import shutil
        shutil.copy(downloaded_tiles[0], output_path)
    else:
        # Merge tiles using rasterio
        _merge_rasters(downloaded_tiles, output_path, bbox)

    return output_path


def _merge_rasters(input_paths: list, output_path: str,
                   bbox: Tuple[float, float, float, float]) -> None:
    """Merge multiple GeoTIFF tiles into one clipped to bbox."""
    from rasterio.merge import merge
    from rasterio.mask import mask
    from shapely.geometry import box

    datasets = [rasterio.open(p) for p in input_paths]
    mosaic, out_transform = merge(datasets)
    for ds in datasets:
        ds.close()

    meta = datasets[0].meta.copy()
    meta.update({
        "driver": "GTiff",
        "height": mosaic.shape[1],
        "width": mosaic.shape[2],
        "transform": out_transform,
        "compress": "lzw",
    })

    with rasterio.open(output_path, "w", **meta) as dest:
        dest.write(mosaic)


def generate_synthetic_dem(
    bbox: Tuple[float, float, float, float],
    output_path: str,
    resolution_m: float = 30.0,
    base_elevation: float = 10.0,
    slope_gradient: float = 0.002,
    add_river: bool = True,
    add_noise: bool = True,
) -> str:
    """
    Generate a synthetic DEM for testing the flood engine.

    Creates a simple sloped terrain with:
    - A valley/river channel running N-S through the center
    - Random terrain noise
    - Realistic elevation range

    Args:
        bbox: (min_lon, min_lat, max_lon, max_lat)
        output_path: Output GeoTIFF path
        resolution_m: Cell size in metres (approximate for geographic CRS)
        base_elevation: Base terrain elevation (m)
        slope_gradient: E-W slope gradient (m/m)
        add_river: Add a river channel through the centre
        add_noise: Add random terrain noise

    Returns:
        Path to synthetic DEM file
    """
    min_lon, min_lat, max_lon, max_lat = bbox

    # Compute grid dimensions
    mid_lat = (min_lat + max_lat) / 2.0
    metres_per_deg_lat = 111132.92
    metres_per_deg_lon = 111412.84 * np.cos(np.radians(mid_lat))

    total_width_m = (max_lon - min_lon) * metres_per_deg_lon
    total_height_m = (max_lat - min_lat) * metres_per_deg_lat

    ncols = max(int(total_width_m / resolution_m), 10)
    nrows = max(int(total_height_m / resolution_m), 10)

    logger.info(f"Generating synthetic DEM: {nrows}×{ncols} at ~{resolution_m}m")

    # Base slope (higher in west, lower in east — common in many Indian catchments)
    x = np.linspace(0, 1, ncols)
    y = np.linspace(0, 1, nrows)
    X, Y = np.meshgrid(x, y)

    # Slope from N to S and W to E
    dem = base_elevation + slope_gradient * total_height_m * (1 - Y) + \
          slope_gradient * total_width_m * 0.3 * (1 - X)

    # Add a river channel (depression) through the center
    if add_river:
        center_col = ncols // 2
        river_width_cells = max(3, ncols // 20)
        river_depth = 5.0
        for c in range(center_col - river_width_cells, center_col + river_width_cells):
            if 0 <= c < ncols:
                dist = abs(c - center_col)
                profile_depth = river_depth * (1 - dist / river_width_cells) ** 2
                dem[:, c] -= profile_depth

    # Add terrain noise
    if add_noise:
        np.random.seed(42)
        noise = np.random.normal(0, 0.5, (nrows, ncols))
        # Smooth noise with a Gaussian filter
        from scipy.ndimage import gaussian_filter
        noise_smooth = gaussian_filter(noise, sigma=3)
        dem += noise_smooth

    # Ensure minimum elevation = 0
    dem = np.maximum(dem, 0.1)

    # Save as GeoTIFF
    transform = from_bounds(min_lon, min_lat, max_lon, max_lat, ncols, nrows)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    with rasterio.open(
        output_path, "w",
        driver="GTiff", dtype="float32",
        count=1, width=ncols, height=nrows,
        crs="EPSG:4326",
        transform=transform,
        nodata=-9999,
        compress="lzw",
    ) as dst:
        dst.write(dem.astype(np.float32), 1)

    logger.info(f"Synthetic DEM saved: {output_path} "
                f"(elevation range: {dem.min():.1f}–{dem.max():.1f}m)")
    return output_path


def get_dem(
    bbox: Tuple[float, float, float, float],
    output_dir: str,
    dem_type: str = "nasadem",
    api_key: Optional[str] = None,
    use_synthetic_fallback: bool = True,
) -> str:
    """
    Get DEM for a bounding box — tries online download first,
    falls back to synthetic DEM if download fails.

    Args:
        bbox: (min_lon, min_lat, max_lon, max_lat)
        output_dir: Directory to save DEM
        dem_type: 'srtmgl1', 'nasadem', 'cop30'
        api_key: Optional OpenTopography API key
        use_synthetic_fallback: If True, generate synthetic DEM on failure

    Returns:
        Path to DEM GeoTIFF
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    dem_path = str(Path(output_dir) / f"dem_{dem_type}.tif")

    # Check if already downloaded
    if Path(dem_path).exists():
        logger.info(f"Using cached DEM: {dem_path}")
        return dem_path

    try:
        return download_dem_opentopography(bbox, dem_path, dem_type, api_key)
    except Exception as e:
        logger.warning(f"DEM download failed: {e}")
        if use_synthetic_fallback:
            logger.info("Generating synthetic DEM for testing...")
            synth_path = str(Path(output_dir) / "dem_synthetic.tif")
            return generate_synthetic_dem(bbox, synth_path)
        raise
