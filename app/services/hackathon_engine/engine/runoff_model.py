"""
SCS-CN Rainfall-Runoff Model (India-calibrated)

Implements:
  - SCS Curve Number method for direct runoff estimation
  - India-specific AMC adjustments for monsoon conditions
  - Green-Ampt infiltration (optional, more physically-based)
  - Antecedent soil moisture correction
  - Time-distributed rainfall (for event hydrograph shaping)

Mathematical Basis:
  SCS-CN (USDA, 1972) — India adaptation per IS 5477 and NIH guidelines:

  Retention parameter:
    S = (25400 / CN) - 254   [mm]

  Initial abstraction (India: λ=0.1 per IS 5477, vs 0.2 in standard):
    Ia = λ × S = 0.1 × S   [mm]

  Direct runoff depth (when P > Ia):
    Q = (P - Ia)² / (P - Ia + S)   [mm]

  where P = total storm rainfall (mm)

Note: λ=0.1 (instead of USDA default λ=0.2) has been validated
for Indian conditions where initial abstraction is typically lower
during the monsoon due to pre-wetted soils.
(Reference: Mishra & Singh, 2003, Hydrol. Process.)
"""

import numpy as np
import logging
from typing import Union, Tuple

logger = logging.getLogger(__name__)

# India-specific initial abstraction ratio (λ)
# Default USDA: 0.2; India monsoon conditions: 0.1
INDIA_LAMBDA = 0.1


# ---------------------------------------------------------------------------
# Core SCS-CN Functions
# ---------------------------------------------------------------------------

def compute_S(cn: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
    """
    Compute SCS potential maximum retention S (mm).

    S = (25400 / CN) - 254   [mm]

    Args:
        cn: Curve Number (scalar or array, 1–100)

    Returns:
        S in mm (same shape as input)
    """
    cn_safe = np.clip(cn, 1.0, 99.9)  # Avoid CN=100 (inf) issues
    return (25400.0 / cn_safe) - 254.0


def compute_initial_abstraction(cn: Union[float, np.ndarray],
                                 lam: float = INDIA_LAMBDA) -> Union[float, np.ndarray]:
    """
    Compute initial abstraction Ia = λ × S (mm).

    Args:
        cn: Curve Number
        lam: Initial abstraction ratio (default=0.1 for India)

    Returns:
        Initial abstraction Ia in mm
    """
    return lam * compute_S(cn)


def scs_cn_runoff(
    rainfall_mm: Union[float, np.ndarray],
    cn: Union[float, np.ndarray],
    lam: float = INDIA_LAMBDA,
) -> np.ndarray:
    """
    Compute direct runoff depth (mm) using SCS-CN method.

    Q = (P - Ia)² / (P - Ia + S)   when P > Ia
    Q = 0                            when P ≤ Ia

    Args:
        rainfall_mm: Total storm rainfall depth (mm), scalar or 2D array
        cn: Curve Number, scalar or 2D array matching rainfall_mm shape
        lam: Initial abstraction ratio (default 0.1 for India)

    Returns:
        Direct runoff depth Q (mm), same shape as input
    """
    P = np.asarray(rainfall_mm, dtype=np.float64)
    CN = np.asarray(cn, dtype=np.float64)

    S = compute_S(CN)
    Ia = lam * S

    numerator = np.maximum(P - Ia, 0.0) ** 2
    denominator = P - Ia + S

    # Avoid division by zero where P ≤ Ia (no runoff)
    runoff = np.where(P > Ia, numerator / np.maximum(denominator, 1e-10), 0.0)
    runoff = np.maximum(runoff, 0.0)

    if np.isscalar(rainfall_mm) and np.isscalar(cn):
        return float(runoff)

    return runoff.astype(np.float32)


def scs_cn_runoff_ratio(cn: Union[float, np.ndarray],
                         rainfall_mm: Union[float, np.ndarray] = 100.0,
                         lam: float = INDIA_LAMBDA) -> Union[float, np.ndarray]:
    """
    Compute runoff ratio Q/P (dimensionless) for a given rainfall event.

    Args:
        cn: Curve Number
        rainfall_mm: Reference rainfall depth (mm)
        lam: Lambda

    Returns:
        Runoff coefficient (0–1)
    """
    Q = scs_cn_runoff(rainfall_mm, cn, lam)
    P = np.asarray(rainfall_mm, dtype=np.float64)
    return np.where(P > 0, Q / P, 0.0)


# ---------------------------------------------------------------------------
# AMC (Antecedent Moisture Condition) Adjustments
# ---------------------------------------------------------------------------

def adjust_cn_for_amc(cn_ii: Union[float, np.ndarray],
                       amc: str) -> Union[float, np.ndarray]:
    """
    Adjust CN from AMC-II baseline to AMC-I or AMC-III.

    AMC-I  (dry conditions):
        CN_I  = CN_II / (2.281 - 0.01281 × CN_II)

    AMC-III (wet/saturated conditions, common during India monsoon):
        CN_III = CN_II / (0.427 + 0.00573 × CN_II)

    Reference: Chow et al. (1988) Applied Hydrology

    Args:
        cn_ii: Baseline CN (AMC-II)
        amc: 'I', 'II', or 'III'

    Returns:
        Adjusted CN
    """
    CN = np.asarray(cn_ii, dtype=np.float64)

    if amc == "I":
        return CN / (2.281 - 0.01281 * CN)
    elif amc == "III":
        return CN / (0.427 + 0.00573 * CN)
    elif amc == "II":
        return CN
    else:
        raise ValueError(f"AMC must be 'I', 'II', or 'III'. Got: {amc}")


# ---------------------------------------------------------------------------
# Time-Distributed Runoff (for rainfall time series)
# ---------------------------------------------------------------------------

def scs_cn_runoff_incremental(
    rainfall_series_mm: np.ndarray,
    cn: Union[float, np.ndarray],
    lam: float = INDIA_LAMBDA,
) -> np.ndarray:
    """
    Compute incremental runoff from a time series of rainfall depths.

    This properly accounts for cumulative abstraction — the SCS-CN method
    should be applied to cumulative rainfall, then differenced to get
    incremental runoff at each time step.

    Args:
        rainfall_series_mm: 1D array of rainfall increments per time step (mm)
        cn: CN value (scalar or 2D spatial array)
        lam: Initial abstraction ratio

    Returns:
        1D array of incremental runoff per time step (mm)
        (or 3D array if cn is 2D spatial)
    """
    n_steps = len(rainfall_series_mm)
    cumulative_rain = np.cumsum(rainfall_series_mm)

    # Compute cumulative runoff at each time step
    cumulative_runoff = np.array([
        scs_cn_runoff(cumulative_rain[t], cn, lam)
        for t in range(n_steps)
    ])

    # Incremental runoff = difference of cumulative
    if cumulative_runoff.ndim == 1:
        incremental = np.diff(cumulative_runoff, prepend=0.0)
    else:
        incremental = np.diff(cumulative_runoff, axis=0, prepend=0.0)

    return np.maximum(incremental, 0.0)


# ---------------------------------------------------------------------------
# Effective Rainfall Rate Computation
# ---------------------------------------------------------------------------

def rainfall_to_effective_rate(
    rainfall_mm: float,
    duration_hr: float,
    cn_grid: np.ndarray,
    amc: str = "II",
    lam: float = INDIA_LAMBDA,
    intensity_factor: float = 1.0,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Convert storm rainfall to spatially distributed effective runoff rate.

    Used in Step 3 (steady-state discharge routing):
        q_eff[i] = Q_runoff[i] / (duration_s)   [m/s]

    Args:
        rainfall_mm: Total storm rainfall (mm)
        duration_hr: Storm duration (hours)
        cn_grid: 2D Curve Number array
        amc: Antecedent Moisture Condition ('I', 'II', 'III')
        lam: Initial abstraction ratio
        intensity_factor: Regional correction from monsoon_regions.py

    Returns:
        Tuple of:
          - runoff_mm: 2D array of net runoff depth (mm)
          - q_eff: 2D array of effective rain rate (m/s) for discharge routing
    """
    # Apply AMC adjustment
    cn_adjusted = adjust_cn_for_amc(cn_grid, amc)

    # Compute runoff depth (mm)
    runoff_mm = scs_cn_runoff(rainfall_mm, cn_adjusted, lam)

    # Apply regional intensity factor — capped at rainfall (physical constraint)
    # Note: intensity_factor > 1 accounts for greater peak flow frequency in
    # orographic regions; it does NOT mean runoff > rainfall
    runoff_mm = np.minimum(runoff_mm * intensity_factor, np.full_like(runoff_mm, rainfall_mm))

    # Convert to m/s rate
    duration_s = max(duration_hr * 3600.0, 1.0)
    q_eff = (runoff_mm / 1000.0) / duration_s  # m/s

    pct = 100 * float(np.nanmean(runoff_mm)) / max(rainfall_mm, 1)
    logger.info(
        f"Runoff: rain={rainfall_mm:.1f}mm, duration={duration_hr:.1f}h, "
        f"AMC={amc}, mean_CN={np.nanmean(cn_grid):.1f}, "
        f"mean_runoff={np.nanmean(runoff_mm):.1f}mm ({pct:.0f}%), "
        f"mean_q_eff={np.nanmean(q_eff)*1000:.4f} mm/s"
    )
    return runoff_mm.astype(np.float32), q_eff.astype(np.float32)


# ---------------------------------------------------------------------------
# Green-Ampt Infiltration (optional, more physically-based)
# ---------------------------------------------------------------------------

def green_ampt_infiltration(
    rainfall_rate_mm_hr: float,
    soil_type: str = "loam",
    initial_moisture_deficit: float = 0.3,
    duration_hr: float = 6.0,
    dt_hr: float = 0.1,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Green-Ampt infiltration model for computing runoff generation.

    F(t) = Ks × t + ψ × θd × ln(1 + F(t) / (ψ × θd))

    where:
        Ks  = saturated hydraulic conductivity (mm/hr)
        ψ   = capillary suction head (mm)
        θd  = initial moisture deficit (dimensionless)
        F(t) = cumulative infiltration at time t

    Args:
        rainfall_rate_mm_hr: Uniform rainfall rate (mm/hr)
        soil_type: Soil texture class (for Ks and ψ lookup)
        initial_moisture_deficit: θd (0=saturated, 1=very dry)
        duration_hr: Total storm duration (hours)
        dt_hr: Time step (hours)

    Returns:
        Tuple of (time_array_hr, runoff_mm_per_step)
    """
    # Green-Ampt parameters for common soil textures
    # (Ks in mm/hr, psi in mm) — from Rawls et al. (1983)
    GA_PARAMS = {
        "sand":             (117.8, 49.5),
        "loamy_sand":       (29.9, 61.3),
        "sandy_loam":       (10.9, 110.1),
        "loam":             (3.4, 88.9),
        "silt_loam":        (6.5, 166.8),
        "sandy_clay_loam":  (1.5, 218.5),
        "clay_loam":        (1.0, 208.8),
        "silty_clay_loam":  (1.0, 273.0),
        "sandy_clay":       (0.6, 239.0),
        "silty_clay":       (0.5, 292.2),
        "clay":             (0.3, 316.3),
        # Indian soil types (approximate)
        "black_cotton":     (0.3, 350.0),   # Vertisol
        "alluvial":         (5.0, 100.0),   # Indo-Gangetic
        "laterite":         (2.0, 150.0),
        "red_loam":         (4.0, 120.0),
    }

    Ks, psi = GA_PARAMS.get(soil_type, GA_PARAMS["loam"])
    theta_d = initial_moisture_deficit

    times = np.arange(0, duration_hr + dt_hr, dt_hr)
    n_steps = len(times)
    runoff = np.zeros(n_steps)

    F = 0.0  # Cumulative infiltration (mm)
    ponding = False
    t_ponding = 0.0
    F_ponding = 0.0

    for i, t in enumerate(times):
        i_rain = rainfall_rate_mm_hr
        if not ponding:
            # Check if infiltration capacity is exceeded
            f_cap = Ks * (1 + psi * theta_d / max(F, 0.01))
            if i_rain > f_cap:
                ponding = True
                t_ponding = t
                F_ponding = F
            else:
                F += i_rain * dt_hr
                runoff[i] = 0.0
        if ponding:
            # Solve F(t) implicitly (Newton-Raphson)
            for _ in range(20):  # iteration
                dF = Ks * (t - t_ponding + psi * theta_d * np.log(1 + F / max(psi * theta_d, 0.01)))
                F_new = F_ponding + dF
                if abs(F_new - F) < 0.001:
                    break
                F = F_new
            infiltration_this_step = Ks * dt_hr * (1 + psi * theta_d / max(F, 0.01))
            runoff[i] = max(i_rain * dt_hr - infiltration_this_step, 0.0)

    return times, runoff
