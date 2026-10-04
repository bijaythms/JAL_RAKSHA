"""
Standalone Flood Engine Test — No Internet Required
===================================================

Tests the complete engine pipeline using:
  - Synthetic DEM (river valley, 50x50 km)
  - Synthetic land cover (cropland + forest + urban + river)
  - Default soil HSG (B = loam, most common in India)
  - Manual rainfall input (Very Heavy Rain threshold)

Run with:
  python test_engine.py

Outputs saved to: test_outputs/
"""
import sys
import os

# Fix PROJ_DATA conflict BEFORE importing rasterio/main
def _fix_proj():
    from pathlib import Path
    import importlib.util
    spec = importlib.util.find_spec("rasterio")
    if spec and spec.origin:
        proj_db = Path(spec.origin).parent / "proj_data" / "proj.db"
        if proj_db.exists():
            os.environ["PROJ_DATA"] = str(proj_db.parent)
            os.environ["PROJ_LIB"]  = str(proj_db.parent)
_fix_proj()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

from main import IndiaFloodEngine

# ---------------------------------------------------------------------------
# Test parameters — Kerala (Periyar basin, flood-prone)
# ---------------------------------------------------------------------------
BBOX = (76.5, 9.9, 76.9, 10.3)   # ~44 km² near Ernakulam, Kerala

RAINFALL_MM = 150.0   # Very Heavy Rain (IMD category)
DURATION_HR = 12.0    # 12-hour event

CONFIG = {
    "amc":              "III",    # AMC-III = wet soil (Kerala monsoon)
    "dem_type":         "nasadem",
    "stream_threshold_km2": 0.5,
    "use_synthetic_dem":  True,   # No internet needed
    "use_synthetic_lulc": True,   # No internet needed
    "use_default_soil":   True,   # Use HSG-C (default for laterite Kerala)
    "save_geotiff":     True,
    "save_html_map":    True,     # Google Hybrid + ESRI
    "save_png_map":     True,
    "fast_hand":        True,
}


def main():
    print("=" * 60)
    print("  INDIA FLOOD ENGINE — DEMO TEST")
    print(f"  Area: Kerala (Ernakulam district)")
    print(f"  Rainfall: {RAINFALL_MM} mm / {DURATION_HR} hr")
    print(f"  IMD Category: Very Heavy Rain")
    print("=" * 60)

    engine = IndiaFloodEngine(
        bbox=BBOX,
        output_dir="test_outputs",
        config=CONFIG,
    )

    result = engine.run(
        rainfall_mm=RAINFALL_MM,
        duration_hr=DURATION_HR,
    )

    print("\n[PASS] TEST COMPLETE")
    print("\nOutput files:")
    for name, path in result["output_paths"].items():
        print(f"  {name:20s}: {path}")

    print("\n[>] Open the interactive map in your browser:")
    html = result["output_paths"].get("html_map", "")
    if html:
        print(f"  {html}")

    return result


if __name__ == "__main__":
    main()
