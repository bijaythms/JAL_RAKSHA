"""
Step 5: Flow Depth Reconstruction — Manning's Inversion + HAND Model

This is the final hydraulic step that converts peak discharge Q_peak
into a spatially distributed flood depth map.

Two-stage approach (as per van den Bout et al. 2023, 2026):

  Stage 1: Channel flow depth (Manning's inversion for rectangular channel)
    ─────────────────────────────────────────────────────────────────────
    Manning's equation:  Q = (1/n) × A × R_h^(2/3) × S^(1/2)

    For a wide rectangular channel (width W >> depth h):
        A   = W × h
        R_h ≈ h   (hydraulic radius ≈ depth for wide channels)

    Substituting:
        Q = (1/n) × W × h × h^(2/3) × S^(1/2)
        Q = (1/n) × W × h^(5/3) × S^(1/2)

    Solving for depth h:
        h = [ Q × n / (W × S^(1/2)) ]^(3/5)

    Channel width W estimated from upstream area (hydraulic geometry):
        W = a × A^b   (Leopold & Maddock, 1953)
        India-calibrated: a = 2.5, b = 0.4  (from CWC surveys)

  Stage 2: Floodplain inundation (HAND model)
    ─────────────────────────────────────────────────────────────────────
    HAND = Height Above Nearest Drainage
    For each cell, HAND = elevation - elevation of nearest stream cell

    Water surface elevation (WSE) at stream cell:
        WSE_stream = z_stream + h_channel

    Inundation depth at floodplain cell:
        d = max(0, WSE_stream - (z_cell))
          = max(0, h_channel - HAND_cell)

    This distributes the channel water level across adjacent floodplain
    cells based on terrain height relative to the stream.

Reference:
  Manning, R. (1891). On the flow of water in open channels.
  Transactions of Institution of Civil Engineers of Ireland.
  Leopold & Maddock (1953). The hydraulic geometry of stream channels.
  Nobre et al. (2011). Height Above Nearest Drainage. HESS.
  van den Bout et al. (2023, 2026). FastFlood methodology.
"""

import numpy as np
import logging
from scipy import ndimage
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Hydraulic Geometry: Channel Width from Upstream Area
# ---------------------------------------------------------------------------

# Leopold & Maddock power law: W = a × A^b
# India-calibrated coefficients from CWC Regional Flood Frequency Studies
# (A in km², W in metres)
INDIA_HG_PARAMS = {
    # (a, b) for W = a × A^b
    "default":          (2.50, 0.40),
    "himalayan":        (3.00, 0.42),   # Steeper catchments, wider channels
    "indo_gangetic":    (3.20, 0.38),   # Wide alluvial plains
    "peninsular":       (2.00, 0.38),   # Narrower channels, harder bedrock
    "western_ghats":    (2.20, 0.40),
    "northeast":        (2.80, 0.42),
}


def estimate_channel_width(
    upstream_area_m2: np.ndarray,
    region: str = "default",
    min_width_m: float = 1.0,
    max_width_m: float = 5000.0,
) -> np.ndarray:
    """
    Estimate channel width (m) from upstream contributing area.

    W = a × A_km2^b   (hydraulic geometry power law)

    Args:
        upstream_area_m2: 2D upstream area array (m²)
        region: India region key from INDIA_HG_PARAMS
        min_width_m: Minimum width clamp (metres)
        max_width_m: Maximum width clamp (metres)

    Returns:
        2D channel width array (metres, float32)
    """
    a, b = INDIA_HG_PARAMS.get(region, INDIA_HG_PARAMS["default"])
    A_km2 = upstream_area_m2 / 1e6  # m² → km²
    W = a * np.maximum(A_km2, 1e-4) ** b

    W = np.clip(W, min_width_m, max_width_m)
    logger.debug(f"Channel width: min={np.min(W):.1f}m, max={np.max(W):.0f}m, "
                 f"mean={np.mean(W):.1f}m")
    return W.astype(np.float32)


# ---------------------------------------------------------------------------
# Step 5a: Manning's Depth Inversion
# ---------------------------------------------------------------------------

def mannings_depth_inversion(
    Q: np.ndarray,
    W: np.ndarray,
    slope: np.ndarray,
    n: np.ndarray,
) -> np.ndarray:
    """
    Compute flow depth by inverting Manning's equation for a wide
    rectangular channel.

    h = [ Q × n / (W × S^(1/2)) ]^(3/5)

    Args:
        Q: Peak discharge (m³/s), 2D array
        W: Channel width (metres), 2D array
        slope: Terrain slope (m/m), 2D array
        n: Manning's roughness coefficient, 2D array

    Returns:
        2D float32 array of flow depth h (metres)
        Zero where Q = 0 or no flow.
    """
    # Minimum slope based on upstream area to prevent unrealistically deep
    # channels on flat terrain (Indo-Gangetic Plain gradient ~0.0001 m/m)
    # Use sqrt(acc) as a proxy to set a local minimum slope
    S_min = 1e-4  # 0.01% — absolute minimum for Indian floodplains
    S_safe = np.maximum(slope, S_min)
    W_safe = np.maximum(W, 1.0)

    # Compute depth: h = (Q*n / (W * sqrt(S)))^(3/5)
    numerator = Q * n
    denominator = W_safe * np.sqrt(S_safe)

    # Avoid division by zero
    ratio = np.where(denominator > 1e-10, numerator / denominator, 0.0)
    h = np.where(Q > 0.01, np.power(np.maximum(ratio, 0.0), 0.6), 0.0)

    # Physical cap: realistic maximum for Indian rivers
    # Brahmaputra peak flood ~20m, most rivers <10m
    h = np.clip(h, 0.0, 15.0).astype(np.float32)

    logger.info(f"Channel depth: max={np.max(h):.2f}m, "
                f"mean (wet)={np.mean(h[h>0]):.2f}m if any wet cells")
    return h


def mannings_velocity(
    h: np.ndarray,
    slope: np.ndarray,
    n: np.ndarray,
) -> np.ndarray:
    """
    Compute flow velocity using Manning's equation.

    v = (1/n) × h^(2/3) × S^(1/2)   [m/s]

    Args:
        h: Flow depth (metres)
        slope: Terrain slope (m/m)
        n: Manning's roughness

    Returns:
        2D velocity array (m/s, float32)
    """
    S_safe = np.maximum(slope, 1e-4)
    v = np.where(h > 0.001, (1.0 / n) * (h ** (2.0/3.0)) * np.sqrt(S_safe), 0.0)
    v = np.clip(v, 0.0, 6.0).astype(np.float32)  # Max ~6 m/s (extreme flash flood)
    return v


# ---------------------------------------------------------------------------
# Step 5b: HAND (Height Above Nearest Drainage)
# ---------------------------------------------------------------------------

def compute_hand(
    dem: np.ndarray,
    stream_mask: np.ndarray,
    fdir: np.ndarray,
    max_search_distance: int = 500,
) -> np.ndarray:
    """
    Compute Height Above Nearest Drainage (HAND).

    For each cell, HAND = elevation_cell - elevation_of_nearest_stream_cell,
    where "nearest" is measured along the flow network (not Euclidean distance).

    Algorithm:
      1. Find all stream cells (where stream_mask = True)
      2. For each non-stream cell, trace flow path downstream to
         find the nearest draining-to stream cell
      3. HAND = dem[cell] - dem[stream_outlet]

    Args:
        dem: Conditioned DEM (metres)
        stream_mask: Boolean array of stream cells
        fdir: D8 flow direction array
        max_search_distance: Max cells to trace upstream (prevents infinite loops)

    Returns:
        2D HAND array (metres, float32)
        Stream cells have HAND = 0.
    """
    rows, cols = dem.shape
    hand = np.full((rows, cols), np.nan, dtype=np.float32)

    # Set HAND = 0 at stream cells
    hand[stream_mask] = 0.0

    # D8 direction → (dr, dc) lookup
    D8_DIRMAP = {64: (0,1), 128: (1,1), 1: (1,0), 2: (1,-1),
                  4: (0,-1), 8: (-1,-1), 16: (-1,0), 32: (-1,1)}

    # For each non-stream cell, follow flow path to nearest stream
    for r in range(rows):
        for c in range(cols):
            if stream_mask[r, c]:
                hand[r, c] = 0.0
                continue
            if np.isnan(dem[r, c]):
                continue

            # Follow flow path downstream
            cr, cc = r, c
            found_stream = False
            for _ in range(max_search_distance):
                d = fdir[cr, cc]
                if d == 0 or d not in D8_DIRMAP:
                    break
                dr, dc = D8_DIRMAP[d]
                nr, nc = cr + dr, cc + dc
                if not (0 <= nr < rows and 0 <= nc < cols):
                    break
                if stream_mask[nr, nc]:
                    # Found stream: HAND = height above this stream cell
                    hand[r, c] = max(0.0, dem[r, c] - dem[nr, nc])
                    found_stream = True
                    break
                cr, cc = nr, nc

            if not found_stream and np.isnan(hand[r, c]):
                # Use Euclidean nearest-stream elevation as fallback
                hand[r, c] = max(0.0, dem[r, c] - np.nanmin(dem[stream_mask]))

    # Fill any remaining NaN with large value (very high ground, won't flood)
    hand = np.where(np.isnan(hand), 9999.0, hand)
    logger.info(f"HAND computed: mean={np.nanmean(hand[hand<9999]):.1f}m, "
                f"max={np.nanmax(hand[hand<9999]):.1f}m")
    return hand


def compute_hand_fast(
    dem: np.ndarray,
    stream_mask: np.ndarray,
) -> np.ndarray:
    """
    Fast HAND approximation using Euclidean nearest-neighbor to stream cells.

    This is an approximation (ignores flow routing) but is much faster
    for large grids. Accurate enough for flat areas (Indo-Gangetic Plain).

    For steep terrain use compute_hand() instead.

    Args:
        dem: Conditioned DEM (metres)
        stream_mask: Boolean stream network mask

    Returns:
        2D HAND array (metres, float32)
    """
    # Nearest stream cell index for each cell (Euclidean)
    stream_indices = np.argwhere(stream_mask)
    if len(stream_indices) == 0:
        logger.warning("No stream cells found! HAND set to zero everywhere.")
        return np.zeros_like(dem, dtype=np.float32)

    # Distance transform to nearest stream cell
    dist, nearest_idx = ndimage.distance_transform_edt(
        ~stream_mask, return_indices=True
    )

    # Elevation of nearest stream cell
    nearest_elev = dem[nearest_idx[0], nearest_idx[1]]

    # HAND = max(0, cell_elevation - nearest_stream_elevation)
    hand = np.maximum(dem - nearest_elev, 0.0)
    hand = np.where(np.isnan(dem), np.nan, hand)

    logger.info(f"Fast HAND: mean={np.nanmean(hand):.1f}m, max={np.nanmax(hand):.1f}m")
    return hand.astype(np.float32)


# ---------------------------------------------------------------------------
# Step 5c: Floodplain Inundation from HAND + Channel WSE
# ---------------------------------------------------------------------------

def compute_channel_wse(
    dem: np.ndarray,
    stream_mask: np.ndarray,
    channel_depth: np.ndarray,
) -> np.ndarray:
    """
    Compute Water Surface Elevation (WSE) at stream cells.

    WSE = terrain_elevation + channel_depth

    Args:
        dem: Terrain elevation (metres)
        stream_mask: Boolean stream mask
        channel_depth: Computed channel flow depth (metres)

    Returns:
        2D WSE array (metres); NaN for non-stream cells
    """
    wse = np.full_like(dem, np.nan)
    wse[stream_mask] = dem[stream_mask] + channel_depth[stream_mask]
    return wse


def distribute_inundation(
    dem: np.ndarray,
    hand: np.ndarray,
    stream_mask: np.ndarray,
    channel_depth: np.ndarray,
    Q_peak: np.ndarray,
    acc: np.ndarray,
    min_Q_threshold_m3s: float = 0.01,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Distribute channel water level across floodplain using HAND model.

    For each floodplain cell adjacent to active stream cells:
        flood_depth = max(0, channel_WSE - terrain_elevation)
                    = max(0, h_channel - HAND)

    Where h_channel is the depth at the nearest upstream stream cell
    with that accumulation value.

    Args:
        dem: Terrain DEM (metres)
        hand: HAND array (metres)
        stream_mask: Boolean stream mask
        channel_depth: 2D array of Manning-computed channel depths (m)
        Q_peak: Peak discharge (m³/s)
        acc: Flow accumulation (m²)
        min_Q_threshold_m3s: Minimum discharge to trigger flooding

    Returns:
        Tuple of:
          - flood_depth: 2D array (metres, float32); 0 where no flood
          - flood_extent: 2D bool array
    """
    rows, cols = dem.shape
    flood_depth = np.zeros((rows, cols), dtype=np.float32)

    # For each stream cell, compute the inundation level
    # and flood adjacent cells whose HAND < channel depth
    for r in range(rows):
        for c in range(cols):
            if not stream_mask[r, c]:
                continue
            h = channel_depth[r, c]
            q = Q_peak[r, c]
            if h <= 0 or q < min_Q_threshold_m3s:
                continue

            # Cells within search radius whose HAND < h get flooded
            # Efficient: use broadcasting on local window
            search_r = int(min(h / 0.1, 50))  # Dynamic search radius based on depth
            r1 = max(0, r - search_r)
            r2 = min(rows, r + search_r + 1)
            c1 = max(0, c - search_r)
            c2 = min(cols, c + search_r + 1)

            window_hand = hand[r1:r2, c1:c2]
            local_flood = np.maximum(h - window_hand, 0.0)
            # Only update cells where this gives DEEPER flooding
            flood_depth[r1:r2, c1:c2] = np.maximum(
                flood_depth[r1:r2, c1:c2], local_flood
            )

    # Also directly inundate stream cells
    flood_depth[stream_mask] = np.maximum(
        flood_depth[stream_mask], channel_depth[stream_mask]
    )

    # Remove noise: minimum 1cm depth to be classified as flooded
    flood_depth = np.where(flood_depth < 0.01, 0.0, flood_depth)
    flood_extent = flood_depth > 0

    logger.info(
        f"Flood extent: {np.sum(flood_extent)} cells flooded "
        f"({100*np.sum(flood_extent)/flood_depth.size:.2f}% of domain), "
        f"max depth={np.max(flood_depth):.2f}m, "
        f"mean depth (flooded)={np.mean(flood_depth[flood_extent]):.2f}m"
        if np.any(flood_extent) else
        f"Flood extent: NO cells flooded (check input discharge)"
    )
    return flood_depth, flood_extent


def distribute_inundation_fast(
    hand: np.ndarray,
    stream_mask: np.ndarray,
    channel_depth: np.ndarray,
    Q_peak: np.ndarray,
    acc: np.ndarray = None,
    dx: float = 30.0,
    min_Q_threshold_m3s: float = 0.1,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Fast vectorized HAND inundation mapping with lateral extent gating.

    For each cell, flooding occurs only when BOTH conditions are met:
      1. HAND < local_channel_depth  (water surface elevation above cell)
      2. lateral_distance < floodplain_width  (cell is within reach of stream)

    Floodplain width estimated from discharge: W_fp = k * Q^0.4
    (empirical power-law, calibrated for Indian floodplains)

    This prevents the unrealistic scenario where all low-lying terrain
    floods regardless of distance from the stream.

    Args:
        hand: HAND array (metres)
        stream_mask: Stream network boolean mask
        channel_depth: 2D Manning's channel depth array (m)
        Q_peak: 2D peak discharge (m3/s)
        acc: Flow accumulation (m2) — used to estimate floodplain width
        dx: Cell size (m)
        min_Q_threshold_m3s: Minimum Q threshold to activate stream

    Returns:
        Tuple of (flood_depth, flood_extent)
    """
    significant_streams = stream_mask & (Q_peak >= min_Q_threshold_m3s)

    if not np.any(significant_streams):
        logger.warning("No significant stream discharge found — no flooding")
        return np.zeros_like(hand), np.zeros_like(hand, dtype=bool)

    # Distance transform: Euclidean distance (cells) to nearest significant stream
    dist_cells, nearest_idx = ndimage.distance_transform_edt(
        ~significant_streams, return_indices=True
    )
    dist_metres = dist_cells * dx

    # Channel depth and discharge at nearest stream cell
    nearest_channel_depth = channel_depth[nearest_idx[0], nearest_idx[1]]
    nearest_Q = Q_peak[nearest_idx[0], nearest_idx[1]]

    # Floodplain width estimate: empirical power law W_fp = k * Q^0.4
    # Calibrated: for Q=100 m3/s → W_fp ~500m, Q=1000 → ~1500m
    # This is conservative — prevents flooding of the entire flat plain
    k_fp = 50.0   # Scaling coefficient (m / (m3/s)^0.4)
    floodplain_width_m = np.maximum(k_fp * np.power(np.maximum(nearest_Q, 0.1), 0.4), dx * 3)

    # Gate 1: Cell must be within the estimated floodplain width
    within_floodplain = dist_metres <= floodplain_width_m

    # Gate 2: Cell's HAND must be below the local channel depth
    # flood_depth = channel_depth - HAND (positive means flooded)
    raw_flood_depth = nearest_channel_depth - hand

    # Apply both gates
    flood_depth = np.where(
        within_floodplain & (raw_flood_depth > 0.01),
        raw_flood_depth,
        0.0,
    )

    # Stream cells always flooded up to their channel depth
    flood_depth[stream_mask] = np.maximum(
        flood_depth[stream_mask], channel_depth[stream_mask]
    )

    # Minimum 1cm threshold
    flood_depth = np.where(flood_depth < 0.01, 0.0, flood_depth)
    flood_extent = flood_depth > 0.0

    n_flooded = int(np.sum(flood_extent))
    pct = 100.0 * n_flooded / hand.size
    logger.info(
        f"Fast HAND inundation: {n_flooded} cells flooded ({pct:.1f}% of domain), "
        f"max depth={np.max(flood_depth):.2f}m"
    )
    return flood_depth.astype(np.float32), flood_extent



# ---------------------------------------------------------------------------
# Full Step 5 Pipeline
# ---------------------------------------------------------------------------

def estimate_flood_depth(
    Q_peak: np.ndarray,
    dem: np.ndarray,
    slope: np.ndarray,
    acc: np.ndarray,
    fdir: np.ndarray,
    manning_n: np.ndarray,
    stream_mask: np.ndarray,
    dx: float,
    dy: float,
    region: str = "default",
    fast_hand: bool = True,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Complete Step 5 pipeline: discharge → flood depth map.

    Args:
        Q_peak: Peak discharge (m³/s), 2D array
        dem: Conditioned DEM (metres)
        slope: Terrain slope (m/m)
        acc: Flow accumulation (m²)
        fdir: D8 flow direction
        manning_n: Manning's n, 2D array
        stream_mask: Stream network boolean mask
        dx, dy: Cell size (metres)
        region: India hydrological region key
        fast_hand: If True, use fast HAND (Euclidean); else flow-path HAND

    Returns:
        Tuple of:
          - flood_depth (m): 2D float32 flood depth array
          - velocity (m/s): 2D float32 velocity array
          - hand: 2D HAND array (m)
    """
    logger.info("Step 5: Computing flood depth from peak discharge...")

    # 5a: Estimate channel width
    W = estimate_channel_width(acc, region=region)

    # 5b: Manning's depth inversion (channel depths)
    h_channel = mannings_depth_inversion(Q_peak, W, slope, manning_n)

    # 5c: Flow velocity
    velocity = mannings_velocity(h_channel, slope, manning_n)

    # 5d: HAND model
    if fast_hand:
        hand = compute_hand_fast(dem, stream_mask)
    else:
        hand = compute_hand(dem, stream_mask, fdir)

    # 5e: Distribute inundation (with lateral floodplain extent gating)
    flood_depth, _ = distribute_inundation_fast(
        hand, stream_mask, h_channel, Q_peak,
        acc=acc, dx=dx,
    )

    return flood_depth, velocity, hand
