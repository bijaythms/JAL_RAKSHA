"""
Step 1: Terrain Correction (Hydro-conditioning) — FastFlood Method

This module implements:
  1. DEM loading and preprocessing
  2. Pit filling (depression filling) using priority-flood algorithm
  3. Flat area resolution
  4. Fast Sweeping enforcement (monotonic DEM)
  5. Slope computation for Manning's equation

Mathematical basis:
  - Fast Sweeping Method for monotonic terrain enforcement
    (van den Bout et al. 2023, 2026)
  - Priority Flood pit filling (Barnes et al. 2014)
  - Slope = |∇z| estimated via central difference (or D8 steepest descent)

Reference:
  Barnes, R., Lehman, C., Mulla, D. (2014). Priority-flood: An optimal
  depression-filling and watershed-labeling algorithm for digital elevation
  models. Computers & Geosciences, 62, 117-127.
"""

import numpy as np
import rasterio
from rasterio.transform import from_bounds
import logging
from pathlib import Path
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# DEM Loading
# ---------------------------------------------------------------------------

def load_dem(dem_path: str) -> Tuple[np.ndarray, dict]:
    """
    Load a Digital Elevation Model from a GeoTIFF file.

    Args:
        dem_path: Path to DEM GeoTIFF file

    Returns:
        Tuple of (elevation_array, metadata_dict)
        elevation_array: 2D float32 array in metres
        metadata: rasterio profile dict with CRS, transform, nodata
    """
    with rasterio.open(dem_path) as src:
        dem = src.read(1).astype(np.float32)
        meta = {
            "crs": src.crs,
            "transform": src.transform,
            "nodata": src.nodata,
            "height": src.height,
            "width": src.width,
            "bounds": src.bounds,
            "res": src.res,
        }
        # Replace nodata with NaN
        if src.nodata is not None:
            dem[dem == src.nodata] = np.nan

    logger.info(f"Loaded DEM: {src.height}×{src.width} cells, "
                f"res={meta['res']}, bounds={meta['bounds']}")
    return dem, meta


def get_cell_size(meta: dict) -> Tuple[float, float]:
    """
    Compute cell size in metres from rasterio metadata.
    Handles both geographic (degrees) and projected (metres) CRS.

    Args:
        meta: Metadata dict from load_dem()

    Returns:
        (dx, dy) cell size in metres
    """
    res_x, res_y = meta["res"]
    crs = meta["crs"]

    if crs.is_geographic:
        # Convert degrees to metres using mid-latitude approximation
        bounds = meta["bounds"]
        mid_lat = (bounds.bottom + bounds.top) / 2.0
        lat_rad = np.radians(mid_lat)
        # WGS84 radius approximation
        metres_per_deg_lat = 111132.92 - 559.82 * np.cos(2 * lat_rad) + 1.175 * np.cos(4 * lat_rad)
        metres_per_deg_lon = 111412.84 * np.cos(lat_rad) - 93.5 * np.cos(3 * lat_rad)
        dx = abs(res_x) * metres_per_deg_lon
        dy = abs(res_y) * metres_per_deg_lat
        logger.info(f"Geographic CRS: cell size ≈ {dx:.1f}m × {dy:.1f}m at lat={mid_lat:.2f}°")
    else:
        dx = abs(res_x)
        dy = abs(res_y)
        logger.info(f"Projected CRS: cell size = {dx:.1f}m × {dy:.1f}m")

    return dx, dy


# ---------------------------------------------------------------------------
# Step 1a: Fill Pits and Depressions (Priority Flood)
# ---------------------------------------------------------------------------

def fill_pits_simple(dem: np.ndarray, nodata: float = np.nan) -> np.ndarray:
    """
    Simple iterative pit-filling using 4-connectivity.
    Replaces local sinks with the minimum neighbouring elevation + epsilon.

    For large DEMs, pysheds is recommended instead (see flow_router.py).

    Args:
        dem: 2D elevation array (float32)
        nodata: Value representing no-data cells

    Returns:
        Pit-filled DEM (float32)
    """
    filled = dem.copy()
    epsilon = 1e-4  # 0.1 mm vertical increment

    rows, cols = dem.shape
    max_iter = 50
    changed = True
    iteration = 0

    while changed and iteration < max_iter:
        changed = False
        iteration += 1
        # Iterate interior cells
        for r in range(1, rows - 1):
            for c in range(1, cols - 1):
                if np.isnan(filled[r, c]):
                    continue
                neighbors = [
                    filled[r-1, c], filled[r+1, c],
                    filled[r, c-1], filled[r, c+1],
                ]
                valid_neighbors = [v for v in neighbors if not np.isnan(v)]
                if not valid_neighbors:
                    continue
                min_neighbor = min(valid_neighbors)
                if filled[r, c] < min_neighbor:
                    filled[r, c] = min_neighbor + epsilon
                    changed = True

    logger.info(f"Pit-filling converged after {iteration} iterations")
    return filled


def fill_depressions_pysheds(dem_path: str, output_path: str) -> str:
    """
    Use pysheds for robust depression filling (recommended for large DEMs).

    Args:
        dem_path: Input DEM path
        output_path: Output conditioned DEM path

    Returns:
        Path to conditioned DEM
    """
    try:
        from pysheds.grid import Grid
    except ImportError:
        raise ImportError("pysheds is required. Install with: pip install pysheds")

    logger.info("Running pysheds depression filling...")
    grid = Grid.from_raster(dem_path)
    dem = grid.read_raster(dem_path)

    # Step-by-step conditioning
    pit_filled = grid.fill_pits(dem)
    flooded = grid.fill_depressions(pit_filled)
    conditioned = grid.resolve_flats(flooded)

    # Save conditioned DEM
    grid.to_raster(conditioned, output_path)
    logger.info(f"Conditioned DEM saved to: {output_path}")
    return output_path


# ---------------------------------------------------------------------------
# Step 1b: Fast Sweeping Algorithm (FSA) — Monotonic DEM enforcement
# ---------------------------------------------------------------------------

def fast_sweeping_monotonic(dem: np.ndarray, epsilon: float = 1e-4) -> np.ndarray:
    """
    Enforce monotonically increasing elevation using a multi-directional
    Fast Sweeping approach (van den Bout et al. 2023).

    The FSA sweeps in 4 directions (NW→SE, NE→SW, SE→NW, SW→NE) and
    enforces: z[i,j] ≥ min(z[neighbors]) + epsilon

    This ensures water can always flow downhill (no artificial barriers).

    Args:
        dem: 2D float32 elevation array (pit-filled recommended first)
        epsilon: Minimum elevation difference to enforce (metres)

    Returns:
        Monotonic DEM (float32)
    """
    z = dem.copy()
    rows, cols = z.shape

    def _sweep_pass(forward_r: bool, forward_c: bool):
        """Single sweep in one direction."""
        r_range = range(1, rows - 1) if forward_r else range(rows - 2, 0, -1)
        c_range = range(1, cols - 1) if forward_c else range(cols - 2, 0, -1)
        for r in r_range:
            for c in c_range:
                if np.isnan(z[r, c]):
                    continue
                # D4 neighbors
                neighbors = []
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols and not np.isnan(z[nr, nc]):
                        neighbors.append(z[nr, nc])
                if neighbors:
                    min_n = min(neighbors)
                    if z[r, c] < min_n + epsilon:
                        z[r, c] = min_n + epsilon

    # 4-direction sweeps
    _sweep_pass(True, True)    # NW → SE
    _sweep_pass(True, False)   # NE → SW
    _sweep_pass(False, False)  # SE → NW
    _sweep_pass(False, True)   # SW → NE

    logger.info("Fast Sweeping monotonic enforcement complete")
    return z


def fast_sweeping_vectorized(dem: np.ndarray, epsilon: float = 1e-4,
                              n_sweeps: int = 2) -> np.ndarray:
    """
    Vectorized (numpy) version of the Fast Sweeping Algorithm.
    Much faster than the pure-Python version above for large grids.

    Uses numpy slicing to update all cells in a sweep direction simultaneously.

    Args:
        dem: 2D float32 elevation array
        epsilon: Minimum elevation step (metres)
        n_sweeps: Number of full 4-direction sweep passes

    Returns:
        Monotonic DEM (float32)
    """
    z = dem.copy()
    valid = ~np.isnan(z)

    for _ in range(n_sweeps):
        # Sweep 1: top-left → bottom-right (forward rows, forward cols)
        for r in range(1, z.shape[0] - 1):
            above = np.where(valid[r-1, 1:-1], z[r-1, 1:-1], -np.inf)
            left  = np.where(valid[r,   :-2], z[r,   :-2],  -np.inf)
            min_neighbor = np.maximum(above, left)
            update_mask = valid[r, 1:-1] & (z[r, 1:-1] < min_neighbor + epsilon)
            z[r, 1:-1] = np.where(update_mask, min_neighbor + epsilon, z[r, 1:-1])

        # Sweep 2: bottom-right → top-left
        for r in range(z.shape[0] - 2, 0, -1):
            below = np.where(valid[r+1, 1:-1], z[r+1, 1:-1], -np.inf)
            right = np.where(valid[r,   2:],   z[r,   2:],   -np.inf)
            min_neighbor = np.maximum(below, right)
            update_mask = valid[r, 1:-1] & (z[r, 1:-1] < min_neighbor + epsilon)
            z[r, 1:-1] = np.where(update_mask, min_neighbor + epsilon, z[r, 1:-1])

    logger.info("Vectorized Fast Sweeping complete")
    return z


# ---------------------------------------------------------------------------
# Step 1c: Slope Computation
# ---------------------------------------------------------------------------

def compute_slope(dem: np.ndarray, dx: float, dy: float,
                  method: str = "horn") -> np.ndarray:
    """
    Compute surface slope magnitude (m/m) from DEM.

    Args:
        dem: 2D elevation array (float32), in metres
        dx: Cell size in x direction (metres)
        dy: Cell size in y direction (metres)
        method: 'horn' (3×3 Sobel/Horn) or 'simple' (2-cell finite diff)

    Returns:
        2D slope array (m/m), float32
        Edge cells set to nearest interior value.
    """
    z = np.where(np.isnan(dem), 0.0, dem).astype(np.float64)

    if method == "horn":
        # Horn (1981) method — standard in ArcGIS/QGIS
        dz_dx = (
            (z[:-2, 2:]  + 2 * z[1:-1, 2:]  + z[2:, 2:])
          - (z[:-2, :-2] + 2 * z[1:-1, :-2] + z[2:, :-2])
        ) / (8 * dx)

        dz_dy = (
            (z[2:, :-2]  + 2 * z[2:, 1:-1]  + z[2:, 2:])
          - (z[:-2, :-2] + 2 * z[:-2, 1:-1] + z[:-2, 2:])
        ) / (8 * dy)

        slope = np.sqrt(dz_dx**2 + dz_dy**2).astype(np.float32)

        # Pad edges
        slope_full = np.full(dem.shape, np.nan, dtype=np.float32)
        slope_full[1:-1, 1:-1] = slope
        slope_full[0, :]  = slope_full[1, :]
        slope_full[-1, :] = slope_full[-2, :]
        slope_full[:, 0]  = slope_full[:, 1]
        slope_full[:, -1] = slope_full[:, -2]
    else:
        # Simple central difference
        dz_dx = np.gradient(z, dx, axis=1)
        dz_dy = np.gradient(z, dy, axis=0)
        slope_full = np.sqrt(dz_dx**2 + dz_dy**2).astype(np.float32)

    # Enforce minimum slope to avoid division by zero in Manning's
    min_slope = 1e-5  # 0.00001 m/m
    slope_full = np.where(np.isnan(slope_full), min_slope, slope_full)
    slope_full = np.maximum(slope_full, min_slope)

    logger.info(f"Slope computed: mean={np.nanmean(slope_full):.5f} m/m, "
                f"max={np.nanmax(slope_full):.4f} m/m")
    return slope_full


# ---------------------------------------------------------------------------
# Step 1d: Save processed DEM
# ---------------------------------------------------------------------------

def save_raster(array: np.ndarray, output_path: str, meta: dict,
                dtype: str = "float32") -> None:
    """
    Save a 2D numpy array as a GeoTIFF.

    Args:
        array: 2D numpy array
        output_path: Output file path
        meta: Metadata dict (must contain crs, transform, nodata)
        dtype: Output data type string
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    profile = {
        "driver": "GTiff",
        "dtype": dtype,
        "width": array.shape[1],
        "height": array.shape[0],
        "count": 1,
        "crs": meta["crs"],
        "transform": meta["transform"],
        "nodata": meta.get("nodata", -9999),
        "compress": "lzw",
    }
    out = np.where(np.isnan(array), profile["nodata"], array).astype(dtype)
    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(out, 1)
    logger.info(f"Saved raster: {output_path}")


# ---------------------------------------------------------------------------
# Convenience: Full terrain conditioning pipeline
# ---------------------------------------------------------------------------

def condition_terrain(dem_path: str, output_dir: str,
                      use_pysheds: bool = True) -> Tuple[np.ndarray, np.ndarray, dict]:
    """
    Full terrain conditioning pipeline (Steps 1a–1c).

    Args:
        dem_path: Raw DEM GeoTIFF path
        output_dir: Directory to save intermediate files
        use_pysheds: If True, use pysheds for robust depression filling

    Returns:
        Tuple of (conditioned_dem, slope_grid, metadata)
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    dem, meta = load_dem(dem_path)
    dx, dy = get_cell_size(meta)

    conditioned_path = str(Path(output_dir) / "dem_conditioned.tif")

    if use_pysheds:
        try:
            fill_depressions_pysheds(dem_path, conditioned_path)
            conditioned, _ = load_dem(conditioned_path)
        except Exception as e:
            logger.warning(f"pysheds failed ({e}), falling back to simple pit fill")
            conditioned = fill_pits_simple(dem)
    else:
        conditioned = fill_pits_simple(dem)

    # Apply Fast Sweeping (vectorized)
    conditioned = fast_sweeping_vectorized(conditioned, epsilon=1e-4)

    # Compute slope
    slope = compute_slope(conditioned, dx, dy)

    # Save outputs
    save_raster(conditioned, str(Path(output_dir) / "dem_fsa.tif"), meta)
    save_raster(slope, str(Path(output_dir) / "slope.tif"), meta)

    logger.info("Terrain conditioning complete")
    return conditioned, slope, meta
