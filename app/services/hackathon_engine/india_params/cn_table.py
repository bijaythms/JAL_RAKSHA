"""
India-specific SCS Curve Number (CN) lookup table.

Reference: IS:5477, USDA-SCS adaptation for Indian conditions.
Based on:
  - Bureau of Indian Standards IS 5477 (Methods for fixing the capacities of reservoirs)
  - ICAR-IIWM guidelines for watershed hydrology in India
  - Regional studies by NIH Roorkee and IIT Delhi

Land cover codes are matched to ESA WorldCover 2021 classes.
Hydrologic Soil Groups (HSG) A, B, C, D per FAO/USDA classification.
Antecedent Moisture Condition II (average) — adjustments for AMC-I/III provided.

AMC-I  (dry):   CN_I  = CN_II / (2.281 - 0.01281 * CN_II)
AMC-III (wet):  CN_III = CN_II / (0.427 + 0.00573 * CN_II)
"""

import numpy as np

# ---------------------------------------------------------------------------
# Primary CN lookup: ESA WorldCover class → (CN_A, CN_B, CN_C, CN_D)
# ---------------------------------------------------------------------------
# ESA WorldCover 2021 class values:
#  10  = Tree cover (forests)
#  20  = Shrubland
#  30  = Grassland
#  40  = Cropland (general agriculture)
#  50  = Built-up / Urban
#  60  = Bare / sparse vegetation
#  70  = Snow & ice
#  80  = Permanent water bodies
#  90  = Herbaceous wetland
#  95  = Mangroves
#  100 = Moss & lichen

# CN table for AMC-II (standard condition)
# (CN_A, CN_B, CN_C, CN_D)
ESA_WORLDCOVER_CN_TABLE = {
    10:  (36, 60, 73, 79),   # Dense forest / tree cover
    20:  (48, 67, 77, 83),   # Shrubland / open forest
    30:  (49, 69, 79, 84),   # Grassland / savanna
    40:  (67, 78, 85, 89),   # General cropland (kharif/rabi mixed)
    50:  (89, 92, 94, 95),   # Urban / built-up (dense)
    60:  (77, 86, 91, 94),   # Bare soil / sparse vegetation
    70:  (100, 100, 100, 100),  # Snow & ice (treat as impervious)
    80:  (100, 100, 100, 100),  # Water body
    90:  (78, 84, 90, 93),   # Herbaceous wetland
    95:  (65, 76, 82, 88),   # Mangroves (high infiltration)
    100: (49, 69, 79, 84),   # Moss/lichen (similar to grassland)
}

# ---------------------------------------------------------------------------
# India-specific sub-crop refinements (overrides ESA class 40)
# ---------------------------------------------------------------------------
# These use the NRCS/SCS India adaptation for specific Indian agricultural types
INDIA_CROP_CN_TABLE = {
    "paddy_wet":        (72, 81, 88, 91),  # Irrigated rice (flooded)
    "paddy_dry":        (67, 78, 85, 89),  # Dryland rice
    "sugarcane":        (67, 78, 85, 89),
    "cotton":           (65, 76, 84, 88),
    "wheat_good":       (63, 75, 83, 87),
    "wheat_poor":       (74, 82, 88, 90),
    "pulses":           (65, 76, 84, 88),
    "plantation_tea":   (45, 66, 77, 83),
    "plantation_coffee": (40, 62, 74, 81),
    "kitchen_garden":   (77, 85, 90, 92),
    "fallow":           (77, 86, 91, 94),
}

# ---------------------------------------------------------------------------
# Urban sub-type refinements (overrides ESA class 50)
# ---------------------------------------------------------------------------
INDIA_URBAN_CN_TABLE = {
    "dense_urban_concrete": (95, 95, 95, 95),  # Commercial/industrial
    "dense_urban_mixed":    (89, 92, 94, 95),  # Mixed residential + commercial
    "residential_good":     (77, 85, 90, 92),  # Planned suburbs, good drainage
    "residential_poor":     (85, 90, 93, 95),  # Informal settlements, poor drainage
    "roads_paved":          (98, 98, 98, 98),
    "roads_gravel":         (76, 85, 89, 91),
    "parks_urban":          (49, 69, 79, 84),
}

# ---------------------------------------------------------------------------
# HSG (Hydrologic Soil Group) lookup by FAO soil texture class
# ---------------------------------------------------------------------------
# FAO soil texture → HSG mapping for Indian soils
# Reference: USDA-NRCS Technical Note 69 + India-specific adjustments
FAO_TEXTURE_HSG = {
    "sand":             "A",
    "loamy_sand":       "A",
    "sandy_loam":       "B",
    "loam":             "B",
    "silt_loam":        "B",
    "silt":             "B",
    "sandy_clay_loam":  "C",
    "clay_loam":        "C",
    "silty_clay_loam":  "C",
    "sandy_clay":       "D",
    "silty_clay":       "D",
    "clay":             "D",
    # Indian-specific soil orders
    "alluvial":         "B",   # Indo-Gangetic alluvial soils
    "black_cotton":     "D",   # Vertisols (Regur) – swell/shrink clay
    "red_laterite":     "C",   # Alfisols (Deccan)
    "red_loam":         "B",   # Red loam of peninsular India
    "laterite":         "C",   # Laterite soils (Kerala, Goa)
    "peaty_marshy":     "D",   # Waterlogged / marshy soils
    "desert_arid":      "A",   # Arid Rajasthan / sandy desert
    "forest_hill":      "B",   # Hill forest soils (steep terrain)
}

# Numeric HSG to index mapping
HSG_INDEX = {"A": 0, "B": 1, "C": 2, "D": 3}
HSG_FROM_INDEX = {0: "A", 1: "B", 2: "C", 3: "D"}


def get_cn(esa_class: int, hsg: str, amc: str = "II") -> float:
    """
    Get SCS Curve Number for a given ESA WorldCover class and Hydrologic Soil Group.

    Args:
        esa_class: ESA WorldCover 2021 pixel value (10, 20, 30, ...)
        hsg: Hydrologic Soil Group ('A', 'B', 'C', 'D')
        amc: Antecedent Moisture Condition ('I', 'II', 'III')

    Returns:
        CN value (float, 0–100)
    """
    hsg_upper = hsg.upper()
    if hsg_upper not in HSG_INDEX:
        raise ValueError(f"Invalid HSG: {hsg}. Must be A, B, C, or D.")

    idx = HSG_INDEX[hsg_upper]
    cn_tuple = ESA_WORLDCOVER_CN_TABLE.get(esa_class, (77, 86, 91, 94))
    cn_ii = float(cn_tuple[idx])

    if amc == "II":
        return cn_ii
    elif amc == "I":
        return cn_ii / (2.281 - 0.01281 * cn_ii)
    elif amc == "III":
        return cn_ii / (0.427 + 0.00573 * cn_ii)
    else:
        raise ValueError(f"Invalid AMC: {amc}. Must be I, II, or III.")


def get_cn_grid(lulc_grid: np.ndarray, hsg_grid: np.ndarray, amc: str = "II") -> np.ndarray:
    """
    Compute a spatially distributed CN grid from LULC and HSG grids.

    Args:
        lulc_grid: 2D array of ESA WorldCover class values
        hsg_grid: 2D array of HSG index values (0=A, 1=B, 2=C, 3=D)
        amc: Antecedent Moisture Condition

    Returns:
        2D numpy array of CN values (float32)
    """
    cn_grid = np.zeros(lulc_grid.shape, dtype=np.float32)

    # Vectorised lookup using unique class combinations
    unique_classes = np.unique(lulc_grid)
    for esa_class in unique_classes:
        mask_lulc = (lulc_grid == esa_class)
        cn_tuple = ESA_WORLDCOVER_CN_TABLE.get(int(esa_class), (77, 86, 91, 94))
        # Apply per-HSG within this LULC class
        for hsg_idx, cn_val in enumerate(cn_tuple):
            mask = mask_lulc & (hsg_grid == hsg_idx)
            cn_ii = float(cn_val)
            if amc == "II":
                cn_grid[mask] = cn_ii
            elif amc == "I":
                cn_grid[mask] = cn_ii / (2.281 - 0.01281 * cn_ii)
            elif amc == "III":
                cn_grid[mask] = cn_ii / (0.427 + 0.00573 * cn_ii)

    # Clamp to valid range
    cn_grid = np.clip(cn_grid, 1.0, 100.0)
    return cn_grid


def amc_from_5day_rainfall(p5: float) -> str:
    """
    Determine AMC class from 5-day antecedent rainfall total (mm).
    Indian conditions (growing season = kharif/monsoon, roughly Jun–Oct).

    Args:
        p5: 5-day antecedent rainfall in mm

    Returns:
        'I', 'II', or 'III'
    """
    # Growing season thresholds (SCS, adapted for India monsoon season)
    if p5 < 35.6:
        return "I"
    elif p5 < 53.3:
        return "II"
    else:
        return "III"
