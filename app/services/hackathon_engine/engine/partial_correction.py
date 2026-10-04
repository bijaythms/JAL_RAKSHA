"""
Step 4: Partial Steady-State Correction

Natural flood events are NEVER in true steady-state.
The steady-state discharge Q_ss computed in Step 3 represents the
*maximum possible* discharge if rainfall continued indefinitely.

In reality, peak discharge Q_peak < Q_ss because:
  1. The catchment has a finite concentration time (T_c)
  2. The storm has a finite duration (t_event)
  3. Travel time attenuates peak flows

This module applies corrections based on:
  - SCS Lag Time equation (standard for India per IS 5477)
  - Dimensionless runoff ratio curve (based on van den Bout et al. 2023)
  - CWC unit hydrograph approach for larger catchments

Mathematical Basis:
  SCS Lag Time (Mockus, 1957):
    T_lag = L^0.8 × (S + 1)^0.7 / (1900 × Y^0.5)   [hours]

  where:
    L    = longest flow path length (m)
    S    = retention parameter = (25400/CN) - 254 (mm)
    Y    = average slope (%)

  Time of Concentration:
    T_c ≈ T_lag / 0.6   (SCS approximation)

  Peak discharge correction factor:
    f = min(1.0, t_event / T_c)^α

  where α is a shape exponent (typically 0.5–0.8) representing
  the rising limb of the unit hydrograph.

Reference:
  van den Bout et al. (2023, 2026) — FastFlood steady-state correction
  SCS NEH Part 630 Chapter 15 (2010) — Time of concentration
  CWC Flood Estimation Reports (India) — Regional unit hydrographs
"""

import numpy as np
import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

# SCS unit hydrograph peak shape factor (dimensionless)
# India standard: 484 (US), adjusted to ~378 for India (flatter UH)
# Reference: CWC Synthetic Unit Hydrograph Reports
INDIA_UH_PEAK_FACTOR = 378.0   # vs 484 in US
US_UH_PEAK_FACTOR = 484.0


# ---------------------------------------------------------------------------
# Step 4a: Flow Path Length
# ---------------------------------------------------------------------------

def compute_flow_path_length(fdir: np.ndarray, acc: np.ndarray,
                              dx: float, dy: float) -> np.ndarray:
    """
    Compute maximum upstream flow path length (L) for each cell.

    Uses flow accumulation to approximate the length of the longest
    flow path draining to each cell (hydraulic length).

    Args:
        fdir: D8 flow direction array
        acc: Flow accumulation array (m²)
        dx: Cell size in x (metres)
        dy: Cell size in y (metres)

    Returns:
        2D float32 array of flow path length L (metres)
    """
    # Approximate: assume flow path follows the channel (sqrt of acc / drainage density)
    # More accurate: trace actual flow paths upstream (expensive for large grids)
    cell_size = (dx + dy) / 2.0
    # Empirical: L ≈ 1.5 × sqrt(A) for natural catchments (SCS approximation)
    L = 1.5 * np.sqrt(acc)

    # Minimum meaningful path length = 1 cell diagonal
    L = np.maximum(L, np.sqrt(dx**2 + dy**2))

    logger.debug(f"Flow path length: mean={np.mean(L):.0f}m, max={np.max(L)/1000:.1f}km")
    return L.astype(np.float32)


# ---------------------------------------------------------------------------
# Step 4b: SCS Lag Time
# ---------------------------------------------------------------------------

def scs_lag_time(L: np.ndarray, cn: np.ndarray, slope_pct: np.ndarray) -> np.ndarray:
    """
    Compute SCS Lag Time T_lag (hours) for each cell.

    T_lag = L^0.8 × (S + 1)^0.7 / (1900 × Y^0.5)

    where:
      L = flow path length (feet! converted internally from metres)
      S = retention parameter (inches! converted internally from mm)
      Y = average slope (%)

    Args:
        L: Flow path length array (metres)
        cn: Curve Number array
        slope_pct: Slope in percent (%)

    Returns:
        T_lag array in hours (float32)
    """
    # Unit conversion: SCS formula uses feet and inches
    L_ft = L * 3.28084          # metres → feet
    S_mm = (25400.0 / np.maximum(cn, 1.0)) - 254.0
    S_in = S_mm / 25.4          # mm → inches

    # Ensure positive slope
    Y = np.maximum(slope_pct, 0.01)

    # SCS equation
    T_lag = (L_ft**0.8 * (S_in + 1.0)**0.7) / (1900.0 * np.sqrt(Y))

    # Clamp: minimum 0.1 hours (6 min), maximum 500 hours
    T_lag = np.clip(T_lag, 0.1, 500.0)

    logger.debug(f"Lag time: mean={np.mean(T_lag):.2f}hr, max={np.max(T_lag):.1f}hr")
    return T_lag.astype(np.float32)


def time_of_concentration(T_lag: np.ndarray) -> np.ndarray:
    """
    Compute time of concentration T_c from SCS lag time.

    T_c ≈ T_lag / 0.6   (SCS approximation)

    Args:
        T_lag: Lag time array (hours)

    Returns:
        T_c array (hours)
    """
    return T_lag / 0.6


# ---------------------------------------------------------------------------
# Step 4c: Partial Steady-State Correction Factor
# ---------------------------------------------------------------------------

def partial_ss_correction_factor(
    T_c: np.ndarray,
    event_duration_hr: float,
    alpha: float = 0.6,
) -> np.ndarray:
    """
    Compute the partial steady-state correction factor f (0–1).

    This factor accounts for the fact that the storm duration may be
    shorter than the time of concentration, so the catchment never
    reaches full steady-state.

    f = min(1, t_event / T_c)^alpha

    When t_event >> T_c: f → 1.0 (full steady state reached)
    When t_event << T_c: f → small (peak is attenuated)

    The exponent alpha controls the shape of the correction:
    - α ≈ 0.6 corresponds to the SCS triangular unit hydrograph rising limb
    - Higher α = slower rise (more attenuation for short events)

    Args:
        T_c: Time of concentration (hours), 2D array
        event_duration_hr: Storm duration (hours)
        alpha: Shape exponent (default 0.6)

    Returns:
        Correction factor f (float32, 0–1)
    """
    ratio = event_duration_hr / np.maximum(T_c, 0.01)
    f = np.minimum(ratio, 1.0) ** alpha
    f = np.clip(f, 0.01, 1.0).astype(np.float32)

    logger.info(
        f"Partial SS correction: duration={event_duration_hr:.1f}hr, "
        f"mean_Tc={np.mean(T_c):.2f}hr, mean_f={np.mean(f):.3f}"
    )
    return f


# ---------------------------------------------------------------------------
# Step 4d: CWC India peak flow scaling (for larger catchments)
# ---------------------------------------------------------------------------

def cwc_india_peak_correction(
    upstream_area_km2: np.ndarray,
    rainfall_mm: float,
    region_factor: float = 1.0,
) -> np.ndarray:
    """
    Apply CWC (Central Water Commission) India design flood correction.

    For larger Indian catchments (>100 km²), the SCS-CN method tends to
    over-predict peak flows. CWC Flood Estimation Reports provide
    regional correction factors derived from observed flood data.

    Peak discharge reduction factor:
        f_cwc = (A / A_ref)^(-b) for A > A_ref

    where:
        A_ref = 100 km² (reference area)
        b = 0.15 (empirical exponent for Indian plains)

    Args:
        upstream_area_km2: Array of upstream areas (km²)
        rainfall_mm: Event rainfall (mm) — used for intensity scaling
        region_factor: Regional scaling from monsoon_regions.py

    Returns:
        Correction factor array (float32)
    """
    A_ref = 100.0  # km²
    b = 0.15
    A = np.maximum(upstream_area_km2, 0.01)

    # For small catchments (<100 km²): no correction needed
    # For large catchments: apply attenuation
    cwc_factor = np.where(
        A > A_ref,
        (A / A_ref) ** (-b),
        1.0
    )

    # Scale with regional factor
    cwc_factor = cwc_factor * region_factor

    # Clamp to physically reasonable range
    cwc_factor = np.clip(cwc_factor, 0.1, 2.0).astype(np.float32)

    return cwc_factor


# ---------------------------------------------------------------------------
# Step 4: Full Partial Steady-State Correction Pipeline
# ---------------------------------------------------------------------------

def apply_partial_ss_correction(
    Q_ss: np.ndarray,
    fdir: np.ndarray,
    acc: np.ndarray,
    cn: np.ndarray,
    slope: np.ndarray,
    dx: float,
    dy: float,
    event_duration_hr: float,
    region_factor: float = 1.0,
    cell_area_m2: float = 900.0,
) -> np.ndarray:
    """
    Full Step 4 pipeline: compute corrected peak discharge Q_peak.

    Q_peak = Q_ss × f_partial_ss × f_cwc

    Args:
        Q_ss: Steady-state discharge (m³/s), 2D array
        fdir: D8 flow direction array
        acc: Flow accumulation (m²)
        cn: Curve Number array
        slope: Terrain slope (m/m)
        dx, dy: Cell size (metres)
        event_duration_hr: Storm event duration (hours)
        region_factor: Regional monsoon correction factor
        cell_area_m2: Cell area in m²

    Returns:
        Q_peak: Corrected peak discharge (m³/s), 2D float32
    """
    # Flow path length (m)
    L = compute_flow_path_length(fdir, acc, dx, dy)

    # Slope in percent for SCS lag time
    slope_pct = np.maximum(slope * 100.0, 0.01)  # m/m → %

    # SCS lag time and time of concentration
    T_lag = scs_lag_time(L, cn, slope_pct)
    T_c = time_of_concentration(T_lag)

    # Partial steady-state correction factor
    f_pss = partial_ss_correction_factor(T_c, event_duration_hr, alpha=0.6)

    # CWC correction for large catchments
    upstream_area_km2 = acc / 1e6
    f_cwc = cwc_india_peak_correction(upstream_area_km2, 0.0, region_factor)

    # Combined peak discharge
    Q_peak = Q_ss * f_pss * f_cwc

    logger.info(
        f"Peak discharge after correction: "
        f"max_Q_ss={np.max(Q_ss):.2f} m³/s → "
        f"max_Q_peak={np.max(Q_peak):.2f} m³/s, "
        f"mean reduction={np.mean(f_pss):.3f}"
    )
    return Q_peak.astype(np.float32)
