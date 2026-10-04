"""Per-scene water extraction.
OPTICAL: MNDWI (Xu 2006) > 0 AND NDWI (McFeeters 1996) > 0.
SAR: sigma0 [dB] < threshold (configurable per zone, default -17 dB)."""
import json
from pathlib import Path
from typing import Optional
import numpy as np

S1_WATER_DB = -17.0
S1_WATER_DB_DEFAULT = S1_WATER_DB
S2_SCALE = 10000.0
L9_SCALE, L9_OFF = 0.0000275, -0.2

_DATA_FILE = Path("data/sar_thresholds.json")
_ZONE_THRESHOLDS = {}

def _load_thresholds():
    global _ZONE_THRESHOLDS
    if _DATA_FILE.exists():
        try:
            _ZONE_THRESHOLDS = json.loads(_DATA_FILE.read_text(encoding="utf-8"))
        except Exception:
            _ZONE_THRESHOLDS = {}
_load_thresholds()

def get_sar_threshold(zone_id: Optional[str] = None) -> float:
    """Return configured SAR threshold for zone, or platform default."""
    if zone_id and str(zone_id) in _ZONE_THRESHOLDS:
        return float(_ZONE_THRESHOLDS[str(zone_id)])
    return S1_WATER_DB

def set_sar_threshold(zone_id: str, threshold_db: float) -> float:
    """Set and persist SAR threshold for zone."""
    if not (-25.0 <= threshold_db <= -10.0):
        raise ValueError("threshold_db must be between -25.0 and -10.0 dB")
    _ZONE_THRESHOLDS[str(zone_id)] = float(threshold_db)
    _DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    _DATA_FILE.write_text(json.dumps(_ZONE_THRESHOLDS, indent=2), encoding="utf-8")
    return float(threshold_db)

def optical_water(green, nir, swir, source):
    g = green.astype("float32"); n = nir.astype("float32"); s = swir.astype("float32")
    if "landsat" in source.lower():
        g = g * L9_SCALE + L9_OFF; n = n * L9_SCALE + L9_OFF
        s = s * L9_SCALE + L9_OFF
    else:
        g, n, s = g / S2_SCALE, n / S2_SCALE, s / S2_SCALE
    valid = (g > 0) & (g < 0.7) & (n > -0.1) & (s > -0.2)
    with np.errstate(divide="ignore", invalid="ignore"):
        mndwi = (g - s) / (g + s)
        ndwi = (g - n) / (g + n)
    water = valid & (mndwi > 0.0) & (ndwi > 0.0)
    return water, valid


def sar_water(vv_db, threshold_db=None):
    if vv_db is None:
        return None
    thr = float(threshold_db) if threshold_db is not None else S1_WATER_DB
    med = _median_filter(vv_db, 5)
    return med < thr


def _median_filter(a, k):
    if k == 1:
        return a
    pad = k // 2
    p = np.pad(a, pad, mode="edge")
    h, w = a.shape
    stack = np.stack([p[i:i+h, j:j+w] for i in range(k) for j in range(k)])
    return np.median(stack, axis=0)
