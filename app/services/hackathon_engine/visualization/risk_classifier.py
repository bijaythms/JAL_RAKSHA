"""
Risk Classification and Hazard Assessment

Provides:
  - NDMA India-compatible risk classification
  - People at risk estimation
  - Infrastructure vulnerability
  - Flash flood potential scoring
  - Return period estimation
"""

import numpy as np
from typing import Dict, Tuple


# ---------------------------------------------------------------------------
# NDMA India Flood Hazard Thresholds
# ---------------------------------------------------------------------------

# Based on National Disaster Management Authority (NDMA) India guidelines
# and EU Floods Directive 2007/60/EC thresholds

NDMA_DEPTH_THRESHOLDS = {
    "no_hazard": 0.0,
    "low":       0.1,    # Ankle-deep; movement affected
    "medium":    0.3,    # Knee-deep; vehicles stalled
    "high":      1.0,    # Waist-deep; people cannot stand
    "extreme":   2.0,    # Above head; life-threatening
}

# Combined depth-velocity hazard thresholds (d × v product)
# Source: FLFArs, RESCDAM project; adapted for India
DV_THRESHOLDS = {
    "low":     0.3,    # d×v < 0.3 m²/s  → low structural hazard
    "medium":  0.6,    # d×v < 0.6 m²/s
    "high":    1.0,    # d×v < 1.0 m²/s  → dangerous for vehicles
    "extreme": 2.0,    # d×v > 2.0 m²/s  → catastrophic
}


def classify_flood_hazard(
    flood_depth: np.ndarray,
    velocity: np.ndarray = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Classify flood hazard using depth and optionally depth×velocity.

    Returns two classifications:
    1. Depth-only classification (NDMA India standard)
    2. Combined depth-velocity (where velocity data available)

    Args:
        flood_depth: 2D depth array (metres)
        velocity: Optional 2D velocity array (m/s)

    Returns:
        Tuple of (depth_risk_class, dv_risk_class) — both uint8 (0–4)
    """
    # Depth-only classification
    depth_class = np.zeros_like(flood_depth, dtype=np.uint8)
    depth_class[flood_depth >= 0.10] = 1  # Low
    depth_class[flood_depth >= 0.30] = 2  # Medium
    depth_class[flood_depth >= 1.00] = 3  # High
    depth_class[flood_depth >= 2.00] = 4  # Extreme

    # DV classification (if velocity provided)
    if velocity is not None:
        dv = flood_depth * velocity
        dv_class = np.zeros_like(flood_depth, dtype=np.uint8)
        dv_class[dv >= DV_THRESHOLDS["low"]]    = 1
        dv_class[dv >= DV_THRESHOLDS["medium"]] = 2
        dv_class[dv >= DV_THRESHOLDS["high"]]   = 3
        dv_class[dv >= DV_THRESHOLDS["extreme"]] = 4
        # Combined: max of depth and dv class
        combined = np.maximum(depth_class, dv_class)
    else:
        combined = depth_class

    return depth_class, combined


def estimate_flash_flood_potential(
    slope: np.ndarray,
    acc: np.ndarray,
    cn: np.ndarray,
    rainfall_intensity_mm_hr: float,
    cell_area_m2: float = 900.0,
) -> np.ndarray:
    """
    Compute Flash Flood Potential Index (FFPI) for each cell.

    FFPI combines:
    - Terrain slope (steeper = faster response)
    - Upstream area (larger = more flow concentration)
    - Soil runoff potential (higher CN = more runoff)
    - Rainfall intensity

    Adapted from Smith et al. (2003) FFPI methodology for India.

    Args:
        slope: 2D slope array (m/m)
        acc: 2D flow accumulation (m²)
        cn: 2D Curve Number
        rainfall_intensity_mm_hr: Rainfall intensity
        cell_area_m2: Cell area

    Returns:
        2D FFPI array (0–10 scale, higher = more flash flood risk)
    """
    # Normalise components to 0–1
    slope_norm = np.clip(slope / 0.15, 0, 1)          # 0.15 m/m = high slope
    area_km2 = acc / 1e6
    area_norm = np.clip(area_km2 / 500.0, 0, 1)        # 500 km² = large catchment
    cn_norm = (cn - 40.0) / 60.0                        # CN 40–100 → 0–1
    cn_norm = np.clip(cn_norm, 0, 1)
    intensity_norm = np.clip(rainfall_intensity_mm_hr / 100.0, 0, 1)

    # Weighted FFPI
    ffpi = (
        0.35 * slope_norm +
        0.25 * area_norm +
        0.25 * cn_norm +
        0.15 * intensity_norm
    ) * 10.0

    return np.clip(ffpi, 0, 10).astype(np.float32)


def estimate_return_period(
    peak_discharge_m3s: float,
    upstream_area_km2: float,
    region: str = "default",
) -> Dict:
    """
    Estimate approximate return period of an event using CWC envelope curves.

    Based on CWC Flood Estimation Reports — Regional flood frequency analysis.
    Provides rough return period estimation for ungauged basins in India.

    Formula (Creager's envelope):
        Q_T = C × A^n × f(T)
    where f(T) is return period factor.

    Args:
        peak_discharge_m3s: Estimated peak discharge (m³/s)
        upstream_area_km2: Upstream catchment area (km²)
        region: Indian hydro-met region

    Returns:
        Dict with estimated return period and confidence
    """
    # CWC regional coefficients (C, n) from flood estimation reports
    CWC_COEFF = {
        "default":          (0.028, 0.78),
        "himalayan":        (0.040, 0.75),
        "indo_gangetic":    (0.025, 0.82),
        "peninsular":       (0.020, 0.80),
        "western_ghats":    (0.045, 0.72),
        "northeast":        (0.050, 0.73),
    }

    C, n = CWC_COEFF.get(region, CWC_COEFF["default"])
    A = max(upstream_area_km2, 1.0)

    # Mean annual flood estimate (1 in 2.33 year)
    Q_mean = C * (A ** n)

    # Ratio of event to mean annual flood
    if Q_mean <= 0:
        return {"return_period": "Unknown", "confidence": "Low"}

    ratio = peak_discharge_m3s / Q_mean

    # Approximate return period from ratio using LP3 relationship
    if ratio < 0.5:
        rp, prob = "<2 years", "Very frequent"
    elif ratio < 1.0:
        rp, prob = "~2 years", "Frequent"
    elif ratio < 2.0:
        rp, prob = "5–10 years", "Moderate"
    elif ratio < 3.5:
        rp, prob = "25–50 years", "Infrequent"
    elif ratio < 5.0:
        rp, prob = "100 years", "Rare"
    else:
        rp, prob = "> 100 years", "Very rare / Extreme"

    return {
        "return_period": rp,
        "probability": prob,
        "mean_annual_flood_m3s": round(Q_mean, 1),
        "ratio_to_mean": round(ratio, 2),
        "confidence": "Low (ungauged basin estimate)",
    }
