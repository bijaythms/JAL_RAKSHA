"""
India monsoon region definitions and rainfall intensity adjustments.

India is divided into 36 IMD meteorological subdivisions and CWC
hydro-meteorological (HM) subzones. This module provides:
  - Region boundary boxes (approximate)
  - Seasonal correction factors for rainfall-runoff response
  - IMD heavy rainfall thresholds
  - Return period rainfall estimates (adapted from CWC flood estimation reports)

Reference:
  - IMD Technical Report on Climatological Tables (2010)
  - CWC Flood Estimation Reports (Subzone 1a through 7)
  - National Institute of Hydrology, Roorkee (Annual Reports)
"""

from dataclasses import dataclass
from typing import Tuple

# ---------------------------------------------------------------------------
# IMD rainfall intensity classification (mm/day)
# Reference: IMD Circular No. NWP/15 (2015)
# ---------------------------------------------------------------------------
IMD_RAINFALL_CATEGORIES = {
    "no_rain":          (0, 2.4),
    "very_light":       (2.5, 7.4),
    "light":            (7.5, 15.4),
    "moderate":         (15.5, 35.4),
    "rather_heavy":     (35.5, 64.4),
    "heavy":            (64.5, 115.5),
    "very_heavy":       (115.6, 204.4),
    "extremely_heavy":  (204.5, float("inf")),
}

# IMD flood alert thresholds (24-hr rainfall in mm) — district level
IMD_FLOOD_ALERT_THRESHOLDS = {
    "watch":   64.5,    # Heavy rain watch issued
    "warning": 115.6,   # Heavy rain warning
    "alert":   204.5,   # Extremely heavy rain alert
}


@dataclass
class MonsoonRegion:
    """Defines a monsoon climatological region for India."""
    name: str
    subdivisions: list
    bbox: Tuple[float, float, float, float]  # (min_lon, min_lat, max_lon, max_lat)
    peak_months: Tuple[int, ...]             # Months with peak rainfall
    avg_annual_rainfall_mm: float
    # Seasonal intensity multiplier: scales runoff response
    # >1 = more intense runoff (compact events), <1 = gentler
    runoff_intensity_factor: float
    # Typical event duration (hours) for IMD design storms
    typical_storm_duration_hr: float
    # Soil moisture correction (AMC tends to be III during peak monsoon)
    default_amc_peak: str


# ---------------------------------------------------------------------------
# India Monsoon Regions
# ---------------------------------------------------------------------------
MONSOON_REGIONS = {

    "western_ghats": MonsoonRegion(
        name="Western Ghats & Konkan Coast",
        subdivisions=["Konkan & Goa", "Madhya Maharashtra", "Kerala"],
        bbox=(73.0, 8.0, 77.5, 20.0),
        peak_months=(6, 7, 8),
        avg_annual_rainfall_mm=3000,
        runoff_intensity_factor=1.35,   # Very intense orographic rainfall
        typical_storm_duration_hr=6.0,
        default_amc_peak="III",
    ),

    "northeast_india": MonsoonRegion(
        name="Northeast India (Brahmaputra Valley)",
        subdivisions=["Assam & Meghalaya", "Arunachal Pradesh",
                      "Nagaland/Manipur/Mizoram/Tripura"],
        bbox=(88.0, 22.0, 97.5, 29.5),
        peak_months=(6, 7, 8, 9),
        avg_annual_rainfall_mm=2500,
        runoff_intensity_factor=1.40,   # Highest flash flood risk in India
        typical_storm_duration_hr=12.0,
        default_amc_peak="III",
    ),

    "indo_gangetic_plain": MonsoonRegion(
        name="Indo-Gangetic Plain",
        subdivisions=["Uttar Pradesh", "Bihar", "Jharkhand", "West Bengal"],
        bbox=(75.5, 22.5, 88.5, 30.5),
        peak_months=(7, 8, 9),
        avg_annual_rainfall_mm=950,
        runoff_intensity_factor=1.10,   # Flat terrain, slow drainage
        typical_storm_duration_hr=24.0,
        default_amc_peak="III",
    ),

    "central_india": MonsoonRegion(
        name="Central India (Narmada-Tapi)",
        subdivisions=["Madhya Pradesh", "Chhattisgarh", "Vidarbha"],
        bbox=(73.5, 18.5, 84.5, 26.5),
        peak_months=(7, 8),
        avg_annual_rainfall_mm=1100,
        runoff_intensity_factor=1.15,
        typical_storm_duration_hr=12.0,
        default_amc_peak="II",
    ),

    "eastern_india": MonsoonRegion(
        name="Eastern India (Mahanadi-Godavari)",
        subdivisions=["Odisha", "Andhra Pradesh", "Coastal AP"],
        bbox=(80.0, 14.0, 87.5, 22.0),
        peak_months=(7, 8, 9, 10),   # Bay of Bengal cyclone influence
        avg_annual_rainfall_mm=1400,
        runoff_intensity_factor=1.20,  # Cyclone-driven extreme events
        typical_storm_duration_hr=12.0,
        default_amc_peak="III",
    ),

    "northwest_india": MonsoonRegion(
        name="Northwest India (Aravalli-Rajasthan)",
        subdivisions=["Rajasthan", "Haryana", "Punjab", "Delhi"],
        bbox=(69.5, 23.5, 77.5, 32.0),
        peak_months=(7, 8),
        avg_annual_rainfall_mm=400,
        runoff_intensity_factor=1.25,   # Flash flood risk despite low annual rain
        typical_storm_duration_hr=6.0,  # Short intense events
        default_amc_peak="I",            # Drier antecedent conditions
    ),

    "peninsular_south": MonsoonRegion(
        name="Peninsular South (Deccan Plateau)",
        subdivisions=["Karnataka", "Tamil Nadu", "Telangana"],
        bbox=(74.5, 8.5, 80.5, 18.5),
        peak_months=(10, 11),           # NE monsoon dominates
        avg_annual_rainfall_mm=750,
        runoff_intensity_factor=1.05,
        typical_storm_duration_hr=24.0,
        default_amc_peak="II",
    ),

    "himalayan_foothills": MonsoonRegion(
        name="Himalayan Foothills (Terai-Dooars)",
        subdivisions=["Uttarakhand", "Himachal Pradesh", "Jammu"],
        bbox=(74.5, 28.0, 82.0, 33.5),
        peak_months=(7, 8),
        avg_annual_rainfall_mm=1600,
        runoff_intensity_factor=1.45,   # Steep slopes → extreme flash floods
        typical_storm_duration_hr=3.0,  # Very short intense cloudbursts
        default_amc_peak="III",
    ),

    "gujarat_saurashtra": MonsoonRegion(
        name="Gujarat & Saurashtra",
        subdivisions=["Gujarat", "Saurashtra & Kutch"],
        bbox=(68.0, 20.0, 74.5, 24.5),
        peak_months=(7, 8),
        avg_annual_rainfall_mm=650,
        runoff_intensity_factor=1.20,
        typical_storm_duration_hr=6.0,
        default_amc_peak="I",
    ),
}


def get_region_for_point(lat: float, lon: float) -> MonsoonRegion:
    """
    Identify the monsoon region for a given lat/lon point.

    Args:
        lat: Latitude (decimal degrees, WGS84)
        lon: Longitude (decimal degrees, WGS84)

    Returns:
        MonsoonRegion object for the location
    """
    for region in MONSOON_REGIONS.values():
        min_lon, min_lat, max_lon, max_lat = region.bbox
        if min_lon <= lon <= max_lon and min_lat <= lat <= max_lat:
            return region

    # Default fallback: Central India (average Indian conditions)
    return MONSOON_REGIONS["central_india"]


def get_intensity_factor(lat: float, lon: float) -> float:
    """Get runoff intensity correction factor for a location."""
    return get_region_for_point(lat, lon).runoff_intensity_factor


def get_storm_duration(lat: float, lon: float) -> float:
    """Get typical design storm duration (hours) for a location."""
    return get_region_for_point(lat, lon).typical_storm_duration_hr


def classify_rainfall_intensity(rainfall_mm: float, duration_hr: float = 24.0) -> str:
    """
    Classify rainfall intensity per IMD standards.

    Args:
        rainfall_mm: Total rainfall (mm)
        duration_hr: Duration over which rainfall is measured (default 24h)

    Returns:
        IMD intensity category string
    """
    # Normalise to 24-hour equivalent if different duration
    rain_24hr = rainfall_mm * (24.0 / duration_hr) if duration_hr != 24.0 else rainfall_mm

    for category, (low, high) in IMD_RAINFALL_CATEGORIES.items():
        if low <= rain_24hr <= high:
            return category
    return "extremely_heavy"


# ---------------------------------------------------------------------------
# CWC subzone-based peak runoff coefficients
# Source: CWC Flood Estimation Reports (Design Flood)
# ---------------------------------------------------------------------------
# Regional runoff coefficient (C) for Rational Method / unit hydrograph
# Used as a secondary check on SCS-CN results
CWC_RUNOFF_COEFFICIENTS = {
    "subzone_1a_lower_ganga":        0.60,
    "subzone_1b_upper_ganga":        0.55,
    "subzone_1c_yamuna_chambal":     0.50,
    "subzone_2_brahmaputra":         0.70,
    "subzone_3a_mahanadi":           0.55,
    "subzone_3b_godavari_upper":     0.55,
    "subzone_3c_krishna_tungabhadra": 0.50,
    "subzone_3d_godavari_lower":     0.60,
    "subzone_3e_east_coast":         0.65,
    "subzone_3f_cauvery":            0.60,
    "subzone_3g_west_coast":         0.70,
    "subzone_3h_kerala":             0.75,
    "subzone_4a_narmada_upper":      0.55,
    "subzone_4b_tapi":               0.55,
    "subzone_4c_mahi_sabarmati":     0.45,
    "subzone_5_satluj_beas":         0.65,
    "subzone_6_indus_jhelum":        0.60,
    "subzone_7_northeast_hilly":     0.75,
}
