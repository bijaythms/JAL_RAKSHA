"""
Engine callable from an external main.py
==========================================

This module exposes the flood engine as a simple callable API
so you can integrate it into ANY existing main.py with 2-3 lines.

Usage in your existing main.py:
--------------------------------

    from flood_engine_api import run_flood_simulation, run_with_forecast

    # Option 1: Manual rainfall
    results = run_flood_simulation(
        bbox=(76.5, 9.9, 76.9, 10.3),
        rainfall_mm=150.0,
        duration_hr=12.0,
        output_dir="my_outputs",
    )

    # Option 2: Live weather forecast
    results = run_with_forecast(
        bbox=(76.5, 9.9, 76.9, 10.3),
        output_dir="my_outputs",
    )

    # Access results
    flood_depth = results["flood_depth"]    # 2D numpy array (metres)
    html_map    = results["output_paths"]["html_map"]  # Path to interactive map
    stats       = results["stats"]           # Dict of flood statistics

"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
from typing import Tuple, Optional, Dict


def run_flood_simulation(
    bbox: Tuple[float, float, float, float],
    rainfall_mm: float,
    duration_hr: float,
    output_dir: str = "outputs",
    amc: str = "II",
    dem_type: str = "nasadem",
    stream_threshold_km2: float = 1.0,
    use_synthetic: bool = False,
    save_html: bool = True,
    save_png: bool = True,
    save_geotiff: bool = True,
) -> Dict:
    """
    Run flood simulation with manual rainfall input.

    Args:
        bbox: (min_lon, min_lat, max_lon, max_lat) — WGS84
        rainfall_mm: Total storm rainfall (mm)
        duration_hr: Storm duration (hours)
        output_dir: Directory for output files
        amc: Antecedent Moisture Condition 'I', 'II', 'III'
        dem_type: DEM source 'nasadem' | 'srtmgl1' | 'cop30'
        stream_threshold_km2: Min upstream area to classify as stream (km²)
        use_synthetic: If True, use synthetic data (no internet needed)
        save_html: Save interactive HTML map (Google Hybrid + ESRI)
        save_png: Save static PNG map
        save_geotiff: Save GeoTIFF rasters

    Returns:
        Dict with keys:
          flood_depth   — 2D numpy array of flood depths (metres)
          velocity      — 2D numpy array of flow velocities (m/s)
          hand          — 2D HAND array (metres)
          stats         — Flood statistics dictionary
          output_paths  — Dict of saved file paths
    """
    from main import IndiaFloodEngine

    config = {
        "amc":                  amc,
        "dem_type":             dem_type,
        "stream_threshold_km2": stream_threshold_km2,
        "use_synthetic_dem":    use_synthetic,
        "use_synthetic_lulc":   use_synthetic,
        "use_default_soil":     use_synthetic,
        "save_geotiff":         save_geotiff,
        "save_html_map":        save_html,
        "save_png_map":         save_png,
        "fast_hand":            True,
    }

    engine = IndiaFloodEngine(bbox=bbox, output_dir=output_dir, config=config)
    return engine.run(rainfall_mm=rainfall_mm, duration_hr=duration_hr)


def run_with_forecast(
    bbox: Tuple[float, float, float, float],
    output_dir: str = "outputs",
    weather_model: str = "ecmwf_ifs025",
    forecast_days: int = 3,
    forecast_hours: int = 24,
    amc: str = "III",     # Use AMC-III for active monsoon forecasts
    **kwargs,
) -> Dict:
    """
    Run flood simulation using live weather forecast from Open-Meteo.

    No API key required. Fetches ECMWF IFS or GFS rainfall forecast
    for the given bounding box centre.

    Args:
        bbox: (min_lon, min_lat, max_lon, max_lat)
        output_dir: Output directory
        weather_model: 'ecmwf_ifs025' | 'gfs_global' | 'cfs'
        forecast_days: Forecast horizon (1–7)
        forecast_hours: Hours to aggregate rainfall over
        amc: AMC condition (recommend 'III' during active monsoon)

    Returns:
        Dict with flood_depth, stats, output_paths, forecast assessment
    """
    from data.weather_forecast import (
        fetch_point_forecast,
        assess_flood_risk_from_forecast,
    )
    from main import IndiaFloodEngine, run_forecast_mode

    class _Args:
        pass
    args = _Args()
    args.weather_model = weather_model
    args.forecast_days = forecast_days
    args.forecast_hours = forecast_hours
    args.output_dir = output_dir

    config = {
        "amc":            amc,
        "weather_model":  weather_model,
        "forecast_days":  forecast_days,
        "save_html_map":  True,
        "save_png_map":   True,
        "save_geotiff":   True,
        "fast_hand":      True,
    }
    config.update(kwargs)

    engine = IndiaFloodEngine(bbox=bbox, output_dir=output_dir, config=config)
    return run_forecast_mode(engine, args)


def run_historical_event(
    bbox: Tuple[float, float, float, float],
    start_date: str,
    end_date: str,
    output_dir: str = "outputs",
    amc: str = "III",
) -> Dict:
    """
    Run flood simulation for a historical event using ERA5 reanalysis.

    Args:
        bbox: (min_lon, min_lat, max_lon, max_lat)
        start_date: 'YYYY-MM-DD'
        end_date: 'YYYY-MM-DD'
        output_dir: Output directory
        amc: AMC condition

    Returns:
        Results dict

    Example (Kerala Floods 2018):
        run_historical_event(
            bbox=(76.2, 9.9, 76.8, 10.4),
            start_date='2018-08-01',
            end_date='2018-08-20',
        )
    """
    from main import IndiaFloodEngine, run_historical_mode

    class _Args:
        pass
    args = _Args()
    args.start_date = start_date
    args.end_date = end_date
    args.forecast_hours = 24
    args.output_dir = output_dir

    config = {"amc": amc, "save_html_map": True, "save_png_map": True, "fast_hand": True}
    engine = IndiaFloodEngine(bbox=bbox, output_dir=output_dir, config=config)
    return run_historical_mode(engine, args)


# ---------------------------------------------------------------------------
# Quick usage examples
# ---------------------------------------------------------------------------

EXAMPLE_SCENARIOS = {
    "kerala_monsoon": {
        "description": "Kerala flood scenario (Very Heavy Rain, AMC-III)",
        "bbox": (76.2, 9.9, 76.8, 10.4),
        "rainfall_mm": 200.0,
        "duration_hr": 24.0,
        "amc": "III",
    },
    "chennai_cyclone": {
        "description": "Chennai cyclone rainfall scenario",
        "bbox": (80.1, 12.8, 80.4, 13.2),
        "rainfall_mm": 300.0,
        "duration_hr": 12.0,
        "amc": "III",
    },
    "assam_flood": {
        "description": "Assam Brahmaputra valley flood",
        "bbox": (91.5, 26.0, 92.0, 26.5),
        "rainfall_mm": 150.0,
        "duration_hr": 48.0,
        "amc": "III",
    },
    "delhi_flash_flood": {
        "description": "Delhi / NCR cloudburst flash flood",
        "bbox": (77.0, 28.5, 77.4, 28.9),
        "rainfall_mm": 120.0,
        "duration_hr": 3.0,
        "amc": "II",
    },
    "mumbai_urban_flood": {
        "description": "Mumbai urban flooding scenario",
        "bbox": (72.8, 19.0, 73.0, 19.2),
        "rainfall_mm": 250.0,
        "duration_hr": 6.0,
        "amc": "III",
    },
    "rajasthan_flash_flood": {
        "description": "Rajasthan desert flash flood (rare but intense)",
        "bbox": (74.5, 26.0, 75.0, 26.5),
        "rainfall_mm": 100.0,
        "duration_hr": 3.0,
        "amc": "I",   # Dry antecedent conditions
    },
}


def run_scenario(scenario_name: str, output_dir: str = None, **kwargs) -> Dict:
    """
    Run a pre-defined India flood scenario.

    Args:
        scenario_name: Key from EXAMPLE_SCENARIOS
        output_dir: Override output directory
        **kwargs: Override any scenario parameters

    Returns:
        Flood simulation results dict
    """
    if scenario_name not in EXAMPLE_SCENARIOS:
        available = ", ".join(EXAMPLE_SCENARIOS.keys())
        raise ValueError(f"Unknown scenario '{scenario_name}'. "
                         f"Available: {available}")

    s = {**EXAMPLE_SCENARIOS[scenario_name], **kwargs}
    print(f"\n🌧️  Scenario: {s['description']}")

    return run_flood_simulation(
        bbox=s["bbox"],
        rainfall_mm=s["rainfall_mm"],
        duration_hr=s["duration_hr"],
        output_dir=output_dir or f"outputs_{scenario_name}",
        amc=s.get("amc", "II"),
        **{k: v for k, v in kwargs.items()
           if k not in ("bbox", "rainfall_mm", "duration_hr", "amc", "description")},
    )
