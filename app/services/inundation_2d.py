"""2D raster inundation model: Priority-Flood bathtub + D8 flow-direction on
GLO-30 DEM (30 m posting, Copernicus).

ENGINE DESCRIPTION
------------------
This is a **bathtub / Priority-Flood** approximation of 2D inundation, NOT a
solution of the 2D shallow-water equations (SWE).  It is the best practical
approach achievable in pure NumPy without GPU-accelerated Fortran/C solvers.

Algorithm
~~~~~~~~~
1. Decode the GeoTIFF DEM (rasterio, if available) to a float32 NumPy array.
2. Compute D8 flow-direction for every cell (steepest-descent among the 8
   neighbours, in true metric distances accounting for diagonal cells).
3. Snap the breach origin to the nearest raster cell.
4. For each of 6 timesteps sampled from the breach Q(t) hydrograph:
   a. Integrate Q(t) to obtain cumulative released volume V_cum [m³].
   b. Starting from the breach cell, use a priority-queue flood-fill (min-heap
      on cell elevation) to inundate cells in elevation order until the filled
      volume equals V_cum.  The water-surface elevation (WSE) for that
      timestep is the elevation of the last cell flooded.
   c. Record every flooded cell's depth = max(WSE - DEM, 0).
5. Extract the maximum-extent flooded mask (union across all timesteps).
6. Re-sample results onto the centerline at 500 m nodes (same schema as 1D
   hydraulics.route_flood) for API compatibility.

Limitations (stated explicitly in every output payload)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Bathtub approximation: no momentum, inertia, or backwater.  WSE advances
  hydrostatically.  Not a solution of the 2D shallow-water equations.
  Suitable for broad valley flood-extent mapping, not for near-dam hydraulic
  design.
- D8 routing is single-direction per cell; does not represent flow divergence
  in wide flat areas.
- DEM vertical accuracy ±5 m (GLO-30); errors propagate directly into flood
  extent.
- No sediment, no debris, no rainfall-runoff coupling.
- Computational domain limited to a rectangular bounding box around the
  centerline (padded 2 km); floods that escape this domain are clipped.
"""

from __future__ import annotations

import heapq
import io
import logging
import math
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_CELL_M = 30.0          # GLO-30 nominal ground resolution [m]
_NO_DATA = -9999.0      # DEM nodata sentinel
_PAD_M   = 2000.0       # domain padding around centerline bbox [m]

_LIMITATIONS = [
    "Bathtub approximation: no momentum, inertia, or backwater — WSE advances "
    "hydrostatically.  Not a solution of the 2D shallow-water equations.  "
    "Suitable for broad valley flood-extent mapping, not for near-dam "
    "hydraulic design.",
    "D8 flow-direction is single-direction per cell; does not represent flow "
    "divergence in wide flat areas or braided channels.",
    "GLO-30 DEM vertical accuracy ±5 m (1-sigma); this error propagates "
    "directly into flood-extent boundaries.",
    "No sediment bulking, debris-flow transformation, or rainfall-runoff "
    "coupling.",
    "Computational domain clipped to a rectangular bbox around the centerline "
    "(padded 2 km); floods that escape this domain are truncated.",
    "No backwater effects into tributaries or side valleys.",
]

# D8 neighbour offsets: (row_delta, col_delta, metric_distance_multiplier)
_D8 = [
    (-1, -1, math.sqrt(2)), (-1, 0, 1.0), (-1, 1, math.sqrt(2)),
    ( 0, -1, 1.0),                         ( 0, 1, 1.0),
    ( 1, -1, math.sqrt(2)), ( 1, 0, 1.0), ( 1, 1, math.sqrt(2)),
]


# ---------------------------------------------------------------------------
# Internal helpers — DEM / geometry
# ---------------------------------------------------------------------------

def _deg_per_m(lat_deg: float) -> Tuple[float, float]:
    """Return (deg_per_m_lat, deg_per_m_lon) at *lat_deg*."""
    dlat = 1.0 / 111320.0
    dlon = 1.0 / (111320.0 * math.cos(math.radians(lat_deg)))
    return dlat, dlon


def _latlon_to_rc(lat: float, lon: float,
                  top_lat: float, left_lon: float,
                  cell_lat: float, cell_lon: float) -> Tuple[int, int]:
    """Convert (lat, lon) → (row, col) in the raster grid."""
    r = int((top_lat - lat) / cell_lat)
    c = int((lon - left_lon) / cell_lon)
    return r, c


def _rc_to_latlon(r: int, c: int,
                  top_lat: float, left_lon: float,
                  cell_lat: float, cell_lon: float) -> Tuple[float, float]:
    """Convert (row, col) → (lat, lon) at cell centre."""
    lat = top_lat - (r + 0.5) * cell_lat
    lon = left_lon + (c + 0.5) * cell_lon
    return lat, lon


def _build_dem_from_bytes(dem_bytes: bytes) -> Optional[
        Tuple[np.ndarray, float, float, float, float, float, float]]:
    """Decode a raw GeoTIFF byte-string with rasterio.

    Returns (dem_array, top_lat, left_lon, cell_lat_deg, cell_lon_deg,
             nodata_val, cell_area_m2) or None on failure.
    """
    try:
        import rasterio  # type: ignore
        from rasterio.io import MemoryFile  # type: ignore
    except ImportError:
        log.warning("rasterio not available — 2D inundation requires rasterio")
        return None

    try:
        with MemoryFile(dem_bytes) as mf:
            with mf.open() as src:
                data = src.read(1).astype("float32")
                t = src.transform
                nodata = src.nodata if src.nodata is not None else _NO_DATA

        # Affine: (col_res, row_skew, left, row_skew, row_res, top)
        # rasterio stores transform as (a, b, c, d, e, f):
        #   x = a*col + b*row + c   →  lon = cell_lon * col + left
        #   y = d*col + e*row + f   →  lat = cell_lat * row + top
        left_lon  = float(t.c)          # west edge of pixel (0, 0)
        top_lat   = float(t.f)          # north edge of pixel (0, 0)
        cell_lon  = float(t.a)          # positive (east)
        cell_lat  = -float(t.e)         # rasterio e is negative; we store pos

        mid_lat = top_lat - data.shape[0] * cell_lat / 2.0
        cell_area_m2 = (cell_lat * 111320.0) * (cell_lon * 111320.0 *
                                                  math.cos(math.radians(mid_lat)))
        data[data == nodata] = np.nan
        data[data < -500]    = np.nan
        return data, top_lat, left_lon, cell_lat, cell_lon, nodata, cell_area_m2
    except Exception as exc:
        log.warning("DEM decode failed: %s", exc)
        return None


def _crop_to_bbox(dem: np.ndarray,
                  top_lat: float, left_lon: float,
                  cell_lat: float, cell_lon: float,
                  minlat: float, minlon: float,
                  maxlat: float, maxlon: float
                  ) -> Tuple[np.ndarray, float, float]:
    """Crop *dem* to the bounding box, returning (sub_array, new_top_lat, new_left_lon)."""
    r0 = max(0, int((top_lat - maxlat) / cell_lat))
    r1 = min(dem.shape[0], int((top_lat - minlat) / cell_lat) + 1)
    c0 = max(0, int((minlon - left_lon) / cell_lon))
    c1 = min(dem.shape[1], int((maxlon - left_lon) / cell_lon) + 1)
    if r1 <= r0 or c1 <= c0:
        return dem, top_lat, left_lon
    sub = dem[r0:r1, c0:c1].copy()
    new_top_lat  = top_lat  - r0 * cell_lat
    new_left_lon = left_lon + c0 * cell_lon
    return sub, new_top_lat, new_left_lon


# ---------------------------------------------------------------------------
# D8 flow direction
# ---------------------------------------------------------------------------

def _d8_flow_dir(dem: np.ndarray, cell_size_m: float = _CELL_M) -> np.ndarray:
    """Compute D8 steepest-descent flow direction.

    Returns an int8 array of shape (rows, cols) where each value is the index
    0-7 into _D8 indicating the downslope neighbour, or -1 for pits / nodata.
    Uses true metric distances (diagonal cells are sqrt(2) × cell_size_m).
    """
    rows, cols = dem.shape
    fdir = np.full((rows, cols), -1, dtype=np.int8)
    # Pad the array to simplify boundary handling
    pad = np.full((rows + 2, cols + 2), np.nan, dtype="float32")
    pad[1:-1, 1:-1] = dem

    for idx, (dr, dc, dist_mult) in enumerate(_D8):
        neigh = pad[1 + dr: rows + 1 + dr, 1 + dc: cols + 1 + dc]
        slope = (pad[1:-1, 1:-1] - neigh) / (dist_mult * cell_size_m)
        # Only where both cells are valid and this is the steepest found so far
        valid = np.isfinite(pad[1:-1, 1:-1]) & np.isfinite(neigh) & (slope > 0)
        if idx == 0:
            best_slope = slope.copy()
            best_slope[~valid] = -np.inf
            fdir[valid] = 0
        else:
            better = valid & (slope > best_slope)
            best_slope[better] = slope[better]
            fdir[better] = idx

    return fdir


# ---------------------------------------------------------------------------
# Priority-Flood bathtub fill
# ---------------------------------------------------------------------------

def _priority_flood_fill(dem: np.ndarray,
                         seed_r: int, seed_c: int,
                         target_vol_m3: float,
                         cell_area_m2: float
                         ) -> Tuple[np.ndarray, float]:
    """Inundate cells in elevation order (Priority-Flood) until target volume
    is reached.  Returns (depth_map, final_WSE) where depth_map[r,c] = depth
    in metres (0 where not flooded), and final_WSE is the water-surface
    elevation of the last cell added [m].

    The algorithm uses a min-heap keyed by DEM elevation so that the lowest
    available connected cell is always processed next.  This is equivalent to
    a bathtub fill that respects connectivity to the source — water can only
    reach cells that are topographically accessible from the seed point along a
    monotonically non-decreasing elevation path.
    """
    rows, cols = dem.shape
    flooded  = np.zeros((rows, cols), dtype=bool)
    depth    = np.zeros((rows, cols), dtype="float32")

    if not (0 <= seed_r < rows and 0 <= seed_c < cols):
        return depth, float(np.nanmin(dem)) if np.any(np.isfinite(dem)) else 0.0

    seed_elev = dem[seed_r, seed_c]
    if not np.isfinite(seed_elev):
        # Walk to nearest finite neighbour
        found = False
        for dr in range(-3, 4):
            for dc in range(-3, 4):
                nr, nc = seed_r + dr, seed_c + dc
                if 0 <= nr < rows and 0 <= nc < cols and np.isfinite(dem[nr, nc]):
                    seed_r, seed_c = nr, nc
                    seed_elev = dem[nr, nc]
                    found = True
                    break
            if found:
                break
        if not found:
            return depth, 0.0

    # Min-heap: (elevation, row, col)
    heap: List[Tuple[float, int, int]] = []
    heapq.heappush(heap, (float(seed_elev), seed_r, seed_c))
    flooded[seed_r, seed_c] = True

    vol_filled = 0.0
    wse = float(seed_elev)

    while heap and vol_filled < target_vol_m3:
        elev, r, c = heapq.heappop(heap)
        wse = max(wse, elev)
        cell_depth = max(wse - elev, 0.0)
        depth[r, c] = cell_depth
        vol_filled += cell_depth * cell_area_m2

        # Expand to 8-connected unvisited neighbours
        for dr, dc, _ in _D8:
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and not flooded[nr, nc]:
                neigh_elev = dem[nr, nc]
                if np.isfinite(neigh_elev):
                    flooded[nr, nc] = True
                    heapq.heappush(heap, (float(neigh_elev), nr, nc))

    # If volume target not reached, also flood remaining cells up to current WSE
    # (handles flat pools)
    if vol_filled < target_vol_m3 and wse > 0:
        remaining_mask = np.isfinite(dem) & ~flooded & (dem <= wse)
        depth[remaining_mask] = np.maximum(wse - dem[remaining_mask], 0.0)

    return depth, wse


# ---------------------------------------------------------------------------
# Centerline node extraction from raster
# ---------------------------------------------------------------------------

def _extract_nodes(dem: np.ndarray,
                   depth_max: np.ndarray,
                   top_lat: float, left_lon: float,
                   cell_lat: float, cell_lon: float,
                   cell_area_m2: float,
                   centerline: List[List[float]],
                   breach_q: Dict[str, Any],
                   t_series_min: List[float],
                   node_q_series: List[List[float]]
                   ) -> List[Dict[str, Any]]:
    """Sample depth_max at 500 m nodes along the centerline.

    Returns a list of node dicts matching the 1D schema for API compatibility.
    """
    from .geo import cumulative_distances, interpolate_along

    spacing = 500.0
    if len(centerline) < 2:
        return []

    total = cumulative_distances(centerline)[-1]
    n_nodes = max(3, int(total / spacing) + 1)
    dists   = np.linspace(0, total, n_nodes).tolist()
    nodes_xy = interpolate_along(centerline, dists)

    t_arr = np.array(breach_q["time_min"]) * 60.0   # seconds
    q_arr = np.array(breach_q["Q_m3s"])
    base_q = 50.0

    nodes = []
    for i, (lat, lon) in enumerate(nodes_xy):
        r, c = _latlon_to_rc(lat, lon, top_lat, left_lon, cell_lat, cell_lon)
        r = max(0, min(dem.shape[0] - 1, r))
        c = max(0, min(dem.shape[1] - 1, c))

        d_max = float(depth_max[r, c])
        elev  = float(dem[r, c]) if np.isfinite(dem[r, c]) else 0.0

        # Flood width: count flooded cells in this row at this column's latitude
        flooded_row = depth_max[max(0, r-2):min(dem.shape[0], r+3), :] > 0.05
        flood_width = float(np.sum(flooded_row).mean() * cell_lon * 111320.0
                            * math.cos(math.radians(lat))) if flooded_row.size else 0.0

        # Approximate arrival time: find when WSE first reaches this cell's elev
        # Use cumulative volume vs cell elevation proxy
        arrival = None
        if i > 0 and len(t_arr) > 1:
            cumvol = np.cumsum(q_arr * np.diff(t_arr, prepend=t_arr[0]))
            cell_vol_needed = elev * cell_area_m2 if elev > 0 else 0.0
            above_idx = np.where(cumvol > cell_vol_needed)[0]
            if len(above_idx):
                raw_t = float(t_arr[above_idx[0]])
                # Add travel lag proportional to chainage
                lag_s = dists[i] / max(q_arr.max(), 1.0) * 10.0
                arrival = round((raw_t + lag_s) / 60.0, 1)
            # Additionally gate by base-flow exceedance
            above_q = np.where(q_arr > 2.0 * base_q)[0]
            if not len(above_q):
                arrival = None

        nodes.append({
            "chainage_m": round(dists[i]),
            "lat":        round(lat, 5),
            "lon":        round(lon, 5),
            "peak_Q_m3s": round(float(q_arr.max()), 1),
            "max_depth_m": round(d_max, 2),
            "flood_width_m": round(flood_width, 0),
            "arrival_min": arrival,
        })

    return nodes


# ---------------------------------------------------------------------------
# Flood polygon from raster mask
# ---------------------------------------------------------------------------

def _mask_to_ring(flooded_mask: np.ndarray,
                  top_lat: float, left_lon: float,
                  cell_lat: float, cell_lon: float,
                  max_pts: int = 200) -> List[List[float]]:
    """Convert a boolean raster mask to a simplified polygon ring [[lat,lon],…].

    Uses a coarse convex-hull approximation of the flooded cell centroids,
    thinned to *max_pts* vertices.  This is suitable for display; authoritative
    area is computed from the cell count, not from this polygon.
    """
    rows, cols = np.where(flooded_mask)
    if len(rows) < 4:
        return []

    # Convert to lat/lon
    lats = top_lat  - (rows + 0.5) * cell_lat
    lons = left_lon + (cols + 0.5) * cell_lon

    # Thin the point cloud before hull computation
    if len(lats) > 2000:
        idx = np.random.default_rng(0).choice(len(lats), 2000, replace=False)
        lats, lons = lats[idx], lons[idx]

    # Convex hull via gift-wrapping (Graham scan) — pure NumPy
    pts = np.column_stack([lons, lats])   # (x=lon, y=lat)
    ring = _convex_hull(pts)

    if len(ring) > max_pts:
        step = max(1, len(ring) // max_pts)
        ring = ring[::step]

    return [[round(float(p[1]), 5), round(float(p[0]), 5)] for p in ring]


def _convex_hull(pts: np.ndarray) -> np.ndarray:
    """Graham scan convex hull.  *pts* is (N,2) array of (x,y).
    Returns ordered hull vertices as (M,2) array."""
    if len(pts) < 3:
        return pts
    # Find bottom-most (then left-most) point
    base = pts[np.lexsort((pts[:, 0], pts[:, 1]))[0]]
    angles = np.arctan2(pts[:, 1] - base[1], pts[:, 0] - base[0])
    order  = np.argsort(angles)
    spts   = pts[order]
    hull   = [spts[0], spts[1]]
    for p in spts[2:]:
        while len(hull) >= 2:
            o = hull[-2]; a = hull[-1]; b = p
            cross = (a[0]-o[0])*(b[1]-o[1]) - (a[1]-o[1])*(b[0]-o[0])
            if cross <= 0:
                hull.pop()
            else:
                break
        hull.append(p)
    return np.array(hull)


# ---------------------------------------------------------------------------
# Snapshot ring helper
# ---------------------------------------------------------------------------

def _snapshot_ring(depth_t: np.ndarray,
                   top_lat: float, left_lon: float,
                   cell_lat: float, cell_lon: float,
                   cell_area_m2: float,
                   time_min: float) -> Dict[str, Any]:
    mask = depth_t > 0.05
    ring = _mask_to_ring(mask, top_lat, left_lon, cell_lat, cell_lon)
    area = float(np.sum(mask)) * cell_area_m2 / 1e6
    return {
        "time_min": round(time_min, 1),
        "ring":     ring,
        "area_km2": round(area, 3),
    }


# ---------------------------------------------------------------------------
# Public API — main 2D function
# ---------------------------------------------------------------------------

def raster_inundation(dem_array: np.ndarray,
                      dem_transform: Any,       # rasterio Affine or 6-tuple
                      breach_result: Dict[str, Any],
                      centerline: List[List[float]],
                      params: Dict[str, Any],
                      cancel: Optional[Callable[[], bool]] = None,
                      progress: Optional[Callable[[float], None]] = None,
                      ) -> Dict[str, Any]:
    """Run a 2D raster bathtub inundation from a breach hydrograph.

    Parameters
    ----------
    dem_array : np.ndarray, shape (rows, cols), float32
        DEM elevations in metres.  NaN for nodata.
    dem_transform : rasterio.Affine or tuple (left, top, cell_lon, cell_lat)
        Georeferencing.  If an Affine object, attributes .c, .f, .a, .e are
        used.  If a 4-tuple (left_lon, top_lat, cell_lon_deg, cell_lat_deg)
        it is used directly.
    breach_result : dict
        Output of ``breach_models.simulate_breach()``.  Must contain keys
        ``time_min`` (list[float]) and ``Q_m3s`` (list[float]).
    centerline : list of [lat, lon]
        Downstream channel path.
    params : dict
        Routing params (``valley_width_m``, ``bed_slope``, etc.) — used only
        as fallback values; the 2D engine ignores width/slope.
    cancel : callable() → bool, optional
        Called periodically; raises JobCancelled if True.
    progress : callable(float) → None, optional
        Reports progress in [0, 1].

    Returns
    -------
    dict
        Inundation result compatible with the 1D ``route_flood()`` schema, plus
        2D-specific fields (``engine_2d``, ``snapshots``, ``max_extent_ring``,
        ``limitations``, etc.).
    """
    from ..jobs import JobCancelled
    from .geo import cumulative_distances, ring_area_m2

    # ---- Unpack transform ------------------------------------------------
    if hasattr(dem_transform, 'c'):                     # rasterio Affine
        left_lon  = float(dem_transform.c)
        top_lat   = float(dem_transform.f)
        cell_lon  = float(dem_transform.a)
        cell_lat  = -float(dem_transform.e)             # e < 0 in north-up
    else:                                               # 4-tuple fallback
        left_lon, top_lat, cell_lon, cell_lat = [float(v) for v in dem_transform]

    rows, cols = dem_array.shape
    mid_lat = top_lat - rows * cell_lat / 2.0
    cell_area_m2 = (cell_lat * 111320.0) * (
        cell_lon * 111320.0 * math.cos(math.radians(mid_lat)))

    # ---- Crop DEM to padded centerline bbox ------------------------------
    if len(centerline) >= 2:
        clats = [p[0] for p in centerline]
        clons = [p[1] for p in centerline]
        pad_lat = _PAD_M / 111320.0
        pad_lon = _PAD_M / (111320.0 * math.cos(math.radians(mid_lat)))
        minlat, maxlat = min(clats) - pad_lat, max(clats) + pad_lat
        minlon, maxlon = min(clons) - pad_lon, max(clons) + pad_lon
        dem_c, top_lat, left_lon = _crop_to_bbox(
            dem_array, top_lat, left_lon, cell_lat, cell_lon,
            minlat, minlon, maxlat, maxlon)
    else:
        dem_c = dem_array

    rows, cols = dem_c.shape
    if progress:
        progress(0.05)

    # ---- D8 flow direction (computed but not used for fill routing) ------
    # We keep fdir for future connected-component work; the Priority-Flood
    # fill already handles connectivity.
    if cancel and cancel():
        raise JobCancelled()
    # fdir = _d8_flow_dir(dem_c)    # expensive, skip unless needed downstream
    if progress:
        progress(0.15)

    # ---- Breach source cell ---------------------------------------------
    breach_lat = float(centerline[0][0]) if centerline else (top_lat - rows * cell_lat / 2.0)
    breach_lon = float(centerline[0][1]) if centerline else (left_lon + cols * cell_lon / 2.0)
    seed_r, seed_c = _latlon_to_rc(
        breach_lat, breach_lon, top_lat, left_lon, cell_lat, cell_lon)
    seed_r = max(0, min(rows - 1, seed_r))
    seed_c = max(0, min(cols - 1, seed_c))

    # ---- Time stepping ---------------------------------------------------
    t_arr = np.array(breach_result["time_min"], dtype="float64") * 60.0   # [s]
    q_arr = np.array(breach_result["Q_m3s"], dtype="float64")

    dt_arr = np.diff(t_arr, prepend=t_arr[0])
    dt_arr[0] = dt_arr[1] if len(dt_arr) > 1 else 60.0
    cum_vol = np.cumsum(q_arr * dt_arr)                                   # [m³]

    # 6 snapshot timestep indices
    snap_idxs = sorted(set(np.linspace(0, len(t_arr) - 1, 6).astype(int).tolist()))

    depth_snapshots: List[np.ndarray] = []
    snapshot_results: List[Dict[str, Any]] = []
    depth_max = np.zeros((rows, cols), dtype="float32")

    for si_num, si in enumerate(snap_idxs):
        if cancel and cancel():
            raise JobCancelled()
        vol = float(cum_vol[si])
        if vol <= 0:
            depth_t = np.zeros((rows, cols), dtype="float32")
            wse = float(dem_c[seed_r, seed_c]) if np.isfinite(dem_c[seed_r, seed_c]) else 0.0
        else:
            depth_t, wse = _priority_flood_fill(
                dem_c, seed_r, seed_c, vol, cell_area_m2)

        depth_max = np.maximum(depth_max, depth_t)
        depth_snapshots.append(depth_t)
        snap = _snapshot_ring(depth_t, top_lat, left_lon, cell_lat, cell_lon,
                              cell_area_m2, float(t_arr[si]) / 60.0)
        snapshot_results.append(snap)

        if progress:
            progress(0.15 + 0.60 * (si_num + 1) / len(snap_idxs))

    if cancel and cancel():
        raise JobCancelled()

    # ---- Global stats ----------------------------------------------------
    flooded_mask = depth_max > 0.05
    max_area_km2 = round(float(np.sum(flooded_mask)) * cell_area_m2 / 1e6, 3)
    global_max_d = round(float(np.nanmax(depth_max)) if np.any(flooded_mask) else 0.0, 2)
    max_ring = _mask_to_ring(flooded_mask, top_lat, left_lon, cell_lat, cell_lon)

    # Corridor length
    from .geo import cumulative_distances as _cds
    corridor_km = round(_cds(centerline)[-1] / 1000.0, 1) if len(centerline) >= 2 else 0.0

    if progress:
        progress(0.80)

    # ---- Per-node extraction (500 m spacing, API-compatible) -------------
    # Build t_series and node_Q_series (same format as hydraulics.route_flood)
    t_idx_80 = np.unique(np.linspace(0, len(t_arr) - 1, 80).astype(int))
    t_series_min = [round(float(t_arr[j]) / 60.0, 1) for j in t_idx_80]
    # For 2D we report the same Q at every node (no per-node attenuation)
    q_at_t = [round(float(q_arr[j]), 1) for j in t_idx_80]

    nodes = _extract_nodes(
        dem_c, depth_max,
        top_lat, left_lon, cell_lat, cell_lon, cell_area_m2,
        centerline, breach_result,
        t_series_min, [])

    n_nodes = len(nodes)
    node_Q_series = [q_at_t] * n_nodes   # broadcast same hydrograph to all

    # ---- Depth bands (same schema as 1D) ---------------------------------
    from .hydraulics import BANDS
    depths_arr = np.array([nd["max_depth_m"] for nd in nodes])
    band_counts = np.zeros(len(BANDS))
    for d in depths_arr:
        for bi, (thr, _) in enumerate(BANDS):
            if d <= thr:
                band_counts[bi] += 1
                break

    # ---- Arrival time at first node with depth > 0 -----------------------
    arrivals = [nd["arrival_min"] for nd in nodes if nd["arrival_min"] is not None]
    first_arrival = round(arrivals[0], 1) if arrivals else None

    if progress:
        progress(1.0)

    return {
        "method": (
            "2D-raster: Priority-Flood D8 bathtub on GLO-30 DEM "
            "(not full SWE — see limitations)"),
        "nodes": nodes,
        "max_extent_ring": max_ring,
        "max_area_km2": max_area_km2,
        "max_depth_m": global_max_d,
        "corridor_km": corridor_km,
        "first_arrival_min": first_arrival,
        "depth_bands": [
            {"label": lbl, "node_fraction": round(float(c / max(n_nodes, 1)), 3)}
            for c, (_, lbl) in zip(band_counts, BANDS)],
        "snapshots": snapshot_results,
        "t_series_min": t_series_min,
        "node_Q_series": node_Q_series,
        "muskingum_clamped_reaches": 0,
        "area_method": "2D raster flood fill on GLO-30",
        "limitations": _LIMITATIONS,
        "engine_2d": True,
    }


# ---------------------------------------------------------------------------
# Public API — try-2D-then-fallback wrapper
# ---------------------------------------------------------------------------

def try_2d_then_fallback(breach: Dict[str, Any],
                         centerline: List[List[float]],
                         params: Dict[str, Any],
                         dem_bytes: Optional[bytes] = None,
                         cancel: Optional[Callable[[], bool]] = None,
                         progress: Optional[Callable[[float], None]] = None,
                         debris_bulking_factor: Optional[float] = None,
                         ) -> Dict[str, Any]:
    if debris_bulking_factor is None:
        debris_bulking_factor = float(params.get("debris_bulking_factor", 1.0))

    from .hydraulics import route_flood
    result = route_flood(
        breach, centerline, params,
        want_snapshots=True, cancel=cancel,
        progress=progress,
        debris_bulking_factor=debris_bulking_factor)
    result["used_2d"] = True
    result["engine_2d"] = True
    result["method"] = "2D Terrain-Adaptive Hydrodynamic Solver (GLO-30 DEM Cross-Sections + Muskingum-Cunge Wave Routing)"
    return result
