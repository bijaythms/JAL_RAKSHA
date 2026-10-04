"""
Manning's roughness coefficient (n) lookup for India.

Sources:
  - Chow (1959) Open Channel Hydraulics
  - IS 10430:1982 (Indian Standard for roughness coefficients)
  - NIH Roorkee technical reports on Indian river systems
  - CWPRS (Central Water and Power Research Station) channel surveys

ESA WorldCover class → Manning's n range → representative value
"""

import numpy as np

# ---------------------------------------------------------------------------
# Manning's n by ESA WorldCover class
# ---------------------------------------------------------------------------
# Format: ESA class → (n_min, n_max, n_representative)
ESA_MANNING_TABLE = {
    10:  (0.060, 0.150, 0.100),   # Dense forest / tree cover
    20:  (0.040, 0.080, 0.060),   # Shrubland
    30:  (0.025, 0.050, 0.035),   # Grassland / pasture
    40:  (0.025, 0.045, 0.033),   # Cropland (general)
    50:  (0.012, 0.025, 0.015),   # Urban / built-up (concrete/asphalt)
    60:  (0.020, 0.035, 0.025),   # Bare soil / sparse vegetation
    70:  (0.010, 0.012, 0.010),   # Snow & ice (smooth)
    80:  (0.025, 0.040, 0.030),   # Water body / rivers
    90:  (0.040, 0.090, 0.060),   # Herbaceous wetland
    95:  (0.060, 0.100, 0.080),   # Mangroves
    100: (0.030, 0.050, 0.040),   # Moss / lichen
}

# ---------------------------------------------------------------------------
# Indian river-specific Manning's n (overrides water body class)
# Reference: CWC Flood Estimation Reports by hydro-meteorological subzone
# ---------------------------------------------------------------------------
INDIA_RIVER_MANNING = {
    # Clean straight channels
    "perennial_large":   0.025,   # Major rivers (Ganga, Brahmaputra, Krishna)
    "perennial_medium":  0.030,   # Medium rivers (Godavari tributaries)
    "perennial_small":   0.035,   # Small perennial streams (hill zones)

    # Seasonal / monsoon channels
    "seasonal_flood":    0.040,   # Seasonal rivers with heavy weed growth
    "monsoon_nala":      0.050,   # Monsoon nalas (flash flood channels)

    # Specialised channels
    "irrigation_canal":  0.022,   # Concrete-lined irrigation canals
    "earthen_canal":     0.030,   # Earthen irrigation channels
    "storm_drain":       0.018,   # Urban stormwater drains (concrete)
    "tidal_estuary":     0.025,   # Tidal estuaries (Godavari delta, etc.)
}

# ---------------------------------------------------------------------------
# Floodplain Manning's n for India
# ---------------------------------------------------------------------------
INDIA_FLOODPLAIN_MANNING = {
    "paddy_flooded":     0.030,   # Flooded rice fields (kharif season)
    "paddy_dry":         0.040,   # Dry rice straw after harvest
    "sugarcane":         0.035,
    "cotton":            0.040,
    "wheat":             0.030,
    "orchard":           0.050,
    "dense_forest":      0.100,
    "light_forest":      0.070,
    "grassland":         0.035,
    "scrub":             0.050,
    "urban_dense":       0.015,
    "urban_sparse":      0.020,
    "bare_soil":         0.025,
    "sandy_bed":         0.022,
}

# ---------------------------------------------------------------------------
# Default overland flow Manning's n by terrain type
# (used in the kinematic wave approximation for hillslope runoff)
# ---------------------------------------------------------------------------
OVERLAND_MANNING = {
    "concrete_pavement": 0.012,
    "asphalt":           0.013,
    "bare_smooth_soil":  0.011,
    "gravelled_surface": 0.020,
    "compacted_fill":    0.024,
    "natural_range":     0.013,
    "dense_grass_short": 0.030,
    "dense_grass_tall":  0.060,
    "bermuda_grass":     0.041,
    "wooded_forest":     0.400,
    "light_brush":       0.070,
    "dense_brush":       0.160,
}


def get_manning_n(esa_class: int) -> float:
    """
    Get representative Manning's n for an ESA WorldCover class.

    Args:
        esa_class: ESA WorldCover 2021 pixel value

    Returns:
        Manning's n (float)
    """
    entry = ESA_MANNING_TABLE.get(esa_class, (0.030, 0.060, 0.035))
    return entry[2]  # return representative value


def get_manning_grid(lulc_grid: np.ndarray) -> np.ndarray:
    """
    Compute a spatially distributed Manning's n grid from LULC raster.

    Args:
        lulc_grid: 2D array of ESA WorldCover class values

    Returns:
        2D numpy array of Manning's n (float32)
    """
    n_grid = np.full(lulc_grid.shape, 0.035, dtype=np.float32)  # default: grassland

    for esa_class, (n_min, n_max, n_rep) in ESA_MANNING_TABLE.items():
        mask = lulc_grid == esa_class
        n_grid[mask] = n_rep

    return n_grid


def channel_manning_n(upstream_area_km2: float) -> float:
    """
    Estimate channel Manning's n based on upstream contributing area.
    Larger rivers tend to have more regular channels (lower n).

    Args:
        upstream_area_km2: Upstream catchment area in km²

    Returns:
        Manning's n estimate for the channel
    """
    if upstream_area_km2 > 50000:     # Major river (>50,000 km²)
        return 0.025
    elif upstream_area_km2 > 5000:    # Large river
        return 0.028
    elif upstream_area_km2 > 500:     # Medium river
        return 0.032
    elif upstream_area_km2 > 50:      # Small river / stream
        return 0.040
    else:                             # Nala / ephemeral channel
        return 0.050
