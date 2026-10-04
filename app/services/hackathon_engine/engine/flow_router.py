"""
Steps 2 & 3: Flow Network Derivation + Steady-State Discharge Routing

Step 2: D8 flow direction from the conditioned (monotonic) DEM
Step 3: Flow accumulation → steady-state discharge routing

Mathematical basis:
  - D8 flow direction: each cell drains to the steepest of 8 neighbors
    (O'Callaghan & Mark, 1984)
  - Flow accumulation: recursive summation of upstream contributing cells
    A_i = Σ(A_j + cell_area) for all j draining into i
  - Steady-state unit discharge: Q_i = q * A_i
    where q = effective runoff rate (m/s) = net rainfall / duration
  - Fast Sweeping used for efficient accumulation (van den Bout et al. 2023)

Reference:
  O'Callaghan, J.F., Mark, D.M. (1984). The extraction of drainage
  networks from digital elevation data. CVGIP, 28(3), 323–344.
"""

import numpy as np
import logging
from pathlib import Path
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

# D8 neighbor offsets: (row_offset, col_offset, distance_weight)
# Order: E, SE, S, SW, W, NW, N, NE
D8_NEIGHBORS = [
    (0, 1, 1.0),      # E
    (1, 1, 1.414),    # SE (diagonal)
    (1, 0, 1.0),      # S
    (1, -1, 1.414),   # SW
    (0, -1, 1.0),     # W
    (-1, -1, 1.414),  # NW
    (-1, 0, 1.0),     # N
    (-1, 1, 1.414),   # NE
]

# D8 direction encoding (matching pysheds convention)
D8_DIRMAP = (64, 128, 1, 2, 4, 8, 16, 32)  # pysheds standard


# ---------------------------------------------------------------------------
# Step 2: Flow Direction (D8)
# ---------------------------------------------------------------------------

def compute_flow_direction_numpy(dem: np.ndarray) -> np.ndarray:
    """
    Compute D8 flow direction from a monotonic (pit-filled) DEM using numpy.

    Each cell is assigned an integer code indicating the direction of the
    steepest descent:
      64  = E
      128 = SE
      1   = S
      2   = SW
      4   = W
      8   = NW
      16  = N
      32  = NE
      0   = Flat / No valid downslope neighbor (outlet)

    Args:
        dem: 2D float32 monotonic DEM (pit-filled)

    Returns:
        2D int16 array of D8 direction codes
    """
    rows, cols = dem.shape
    fdir = np.zeros((rows, cols), dtype=np.int16)

    # Pad DEM with large values so border cells flow outward
    padded = np.pad(dem, 1, mode='edge')
    padded[:, 0] = padded[:, 0] - 1e6   # Force flow off left edge
    padded[:, -1] = padded[:, -1] - 1e6
    padded[0, :] = padded[0, :] - 1e6
    padded[-1, :] = padded[-1, :] - 1e6

    for idx, (dr, dc, dist) in enumerate(D8_NEIGHBORS):
        # Elevation drop to each neighbor (positive = downslope)
        neighbor = padded[1+dr:rows+1+dr, 1+dc:cols+1+dc]
        drop = (dem - neighbor) / dist
        if idx == 0:
            max_drop = drop
            best_dir = np.full((rows, cols), D8_DIRMAP[idx], dtype=np.int16)
        else:
            better = drop > max_drop
            max_drop = np.where(better, drop, max_drop)
            best_dir = np.where(better, D8_DIRMAP[idx], best_dir)

    # Cells with no downslope (flat / outlet) get 0
    fdir = np.where(max_drop >= 0, best_dir, 0)
    fdir = fdir.astype(np.int16)

    logger.info(f"Flow direction computed. Outlet cells: {np.sum(fdir == 0)}")
    return fdir


def compute_flow_direction_pysheds(dem_path: str) -> Tuple[object, np.ndarray]:
    """
    Use pysheds for D8 flow direction (handles flat areas and large DEMs well).

    Args:
        dem_path: Path to conditioned DEM GeoTIFF

    Returns:
        Tuple of (pysheds Grid object, flow direction array)
    """
    try:
        from pysheds.grid import Grid
    except ImportError:
        raise ImportError("pysheds required. pip install pysheds")

    grid = Grid.from_raster(dem_path)
    dem = grid.read_raster(dem_path)
    fdir = grid.flowdir(dem)
    return grid, np.array(fdir)


# ---------------------------------------------------------------------------
# Step 3a: Flow Accumulation (upstream contributing area)
# ---------------------------------------------------------------------------

def compute_flow_accumulation(fdir: np.ndarray,
                              cell_area_m2: float = 900.0) -> np.ndarray:
    """
    Compute flow accumulation from a D8 flow direction grid.

    Uses topological sort (upstream-first traversal) to propagate
    contributing area from headwaters to outlets.

    Args:
        fdir: 2D int16 D8 flow direction array
        cell_area_m2: Area of each cell in m² (default: 30×30 = 900 m²)

    Returns:
        2D float64 array of upstream contributing area (m²)
    """
    rows, cols = fdir.shape
    acc = np.ones((rows, cols), dtype=np.float64) * cell_area_m2

    # Build reverse lookup: D8 code → (dr, dc)
    dir_to_offset = {}
    for idx, (dr, dc, _) in enumerate(D8_NEIGHBORS):
        dir_to_offset[D8_DIRMAP[idx]] = (dr, dc)

    # Compute in-degree (number of cells draining into each cell)
    in_degree = np.zeros((rows, cols), dtype=np.int32)
    for r in range(rows):
        for c in range(cols):
            d = fdir[r, c]
            if d == 0:
                continue
            if d in dir_to_offset:
                dr, dc = dir_to_offset[d]
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    in_degree[nr, nc] += 1

    # Topological sort using a queue of cells with in-degree 0 (headwaters)
    from collections import deque
    queue = deque()
    for r in range(rows):
        for c in range(cols):
            if in_degree[r, c] == 0:
                queue.append((r, c))

    processed = 0
    while queue:
        r, c = queue.popleft()
        processed += 1
        d = fdir[r, c]
        if d == 0:
            continue
        if d in dir_to_offset:
            dr, dc = dir_to_offset[d]
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols:
                acc[nr, nc] += acc[r, c]
                in_degree[nr, nc] -= 1
                if in_degree[nr, nc] == 0:
                    queue.append((nr, nc))

    logger.info(f"Flow accumulation complete. Max contributing area: "
                f"{np.max(acc)/1e6:.2f} km²")
    return acc


def compute_flow_accumulation_pysheds(grid, fdir_array) -> np.ndarray:
    """
    Use pysheds accumulation (faster for large grids).

    Args:
        grid: pysheds Grid object
        fdir_array: pysheds flow direction raster

    Returns:
        2D float64 upstream area array (cells)
    """
    acc = grid.accumulation(fdir_array)
    return np.array(acc, dtype=np.float64)


# ---------------------------------------------------------------------------
# Step 3b: Steady-State Discharge Routing
# ---------------------------------------------------------------------------

def compute_steady_discharge(
    acc: np.ndarray,
    effective_rain_m_per_s: float,
    cell_area_m2: float = 900.0,
) -> np.ndarray:
    """
    Compute steady-state discharge (m³/s) at each cell.

    Under steady-state assumption:
        Q_i = q_eff × A_i

    where:
        q_eff = effective rainfall rate (m/s) after subtracting losses
        A_i   = upstream contributing area (m²)

    The key insight (from FastFlood) is that this avoids full dynamic
    routing — it directly gives the maximum possible discharge if the
    entire catchment were at steady state.

    Args:
        acc: 2D upstream contributing area array (m²)
        effective_rain_m_per_s: Effective (net) rainfall rate (m/s)
        cell_area_m2: Cell area in m²

    Returns:
        2D float32 array of steady-state discharge (m³/s)
    """
    Q_ss = effective_rain_m_per_s * acc
    Q_ss = np.maximum(Q_ss, 0.0).astype(np.float32)
    logger.info(f"Steady-state discharge: max={np.max(Q_ss):.2f} m³/s, "
                f"mean (nonzero)={np.mean(Q_ss[Q_ss > 0]):.4f} m³/s")
    return Q_ss


def compute_effective_rain_rate(
    rainfall_mm: float,
    duration_hr: float,
    cn_grid: np.ndarray,
    spatial: bool = True,
) -> np.ndarray:
    """
    Convert rainfall depth (mm) to effective (runoff-producing) rainfall
    rate (m/s) using the SCS-CN method.

    This function bridges the runoff_model and flow_router modules.

    Args:
        rainfall_mm: Total rainfall depth (mm) over the event
        duration_hr: Storm duration (hours)
        cn_grid: 2D array of SCS Curve Number values
        spatial: If True, return spatially distributed rate array;
                 If False, return scalar mean

    Returns:
        2D float32 array of effective rain rate (m/s)
        or scalar float if spatial=False
    """
    from engine.runoff_model import scs_cn_runoff

    # Compute runoff depth (mm) per cell using SCS-CN
    runoff_depth_mm = scs_cn_runoff(rainfall_mm, cn_grid)

    # Convert to m/s
    duration_s = duration_hr * 3600.0
    effective_rate_m_per_s = (runoff_depth_mm / 1000.0) / duration_s

    if spatial:
        return effective_rate_m_per_s.astype(np.float32)
    else:
        return float(np.nanmean(effective_rate_m_per_s))


# ---------------------------------------------------------------------------
# Stream Network Extraction
# ---------------------------------------------------------------------------

def extract_stream_network(acc: np.ndarray,
                           threshold_km2: float = 1.0,
                           cell_area_m2: float = 900.0) -> np.ndarray:
    """
    Extract stream network by thresholding flow accumulation.

    Args:
        acc: 2D upstream contributing area (m²)
        threshold_km2: Minimum upstream area to classify as stream (km²)
        cell_area_m2: Cell area in m²

    Returns:
        2D boolean array (True = stream cell)
    """
    threshold_m2 = threshold_km2 * 1e6
    stream_mask = acc >= threshold_m2
    n_stream = np.sum(stream_mask)
    logger.info(f"Stream network: {n_stream} cells "
                f"(threshold={threshold_km2} km²)")
    return stream_mask
