"""
Weather Forecast Integration — Open-Meteo API

Fetches rainfall forecasts from Open-Meteo (free, no API key required for
non-commercial use, up to 10,000 calls/day).

Supports:
  - Point forecasts for lat/lon
  - Spatial gridded forecasts over a bounding box
  - Historical reanalysis (ERA5) for past events
  - Rainfall aggregation for flood model input
  - Multiple weather models (ECMWF IFS, GFS, IMD-NWP proxy)

Open-Meteo API: https://open-meteo.com/en/docs
ERA5 Historical: https://open-meteo.com/en/docs/historical-weather-api

India-specific:
  - Best models for India: ECMWF IFS, CFS (NOAA)
  - Monsoon season (June–September): typically higher reliability
  - IMD NWP data: available via India's MOSDAC portal (separate integration)
"""

import requests
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import Tuple, List, Optional, Dict
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Open-Meteo API Configuration
# ---------------------------------------------------------------------------

OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_HISTORICAL_URL = "https://archive-api.open-meteo.com/v1/archive"
OPEN_METEO_ENSEMBLE_URL = "https://ensemble-api.open-meteo.com/v1/ensemble"

# Available weather models with India suitability notes
WEATHER_MODELS = {
    "ecmwf_ifs025": "ECMWF IFS (best for India monsoon, 0.25° grid)",
    "gfs_global":   "NOAA GFS (global, 0.25° grid)",
    "icon_global":  "DWD ICON Global (Germany)",
    "cfs":          "NOAA CFS (seasonal, useful for monsoon)",
    "era5":         "ERA5 reanalysis (historical data only)",
    "era5_land":    "ERA5-Land (higher resolution, historical)",
}

# India timezone
INDIA_TIMEZONE = "Asia/Kolkata"


@dataclass
class WeatherForecast:
    """Container for weather forecast data."""
    lat: float
    lon: float
    model: str
    times: List[str]            # ISO datetime strings
    precipitation_mm: List[float]   # Hourly precipitation (mm)
    rain_mm: List[float]           # Rain component (mm)
    snowfall_cm: List[float]       # Snowfall (cm, relevant for Himalayas)
    source: str = "open-meteo"

    @property
    def total_precipitation_mm(self) -> float:
        """Total accumulated precipitation (mm)."""
        return sum(self.precipitation_mm)

    def aggregate_hours(self, n_hours: int) -> float:
        """Sum precipitation over first n_hours."""
        return sum(self.precipitation_mm[:n_hours])

    def peak_intensity_mm_hr(self) -> float:
        """Peak hourly rainfall intensity (mm/hr)."""
        return max(self.precipitation_mm) if self.precipitation_mm else 0.0

    def to_event_rainfall(self, duration_hr: int = 24) -> Tuple[float, float]:
        """
        Extract event rainfall for flood modelling.

        Returns:
            (total_mm, duration_hr) — suitable for SCS-CN input
        """
        rain = self.precipitation_mm[:duration_hr]
        total = sum(rain)
        # Find actual duration (last hour with significant rain > 0.1mm)
        actual_dur = next(
            (i for i in range(len(rain)-1, -1, -1) if rain[i] > 0.1),
            1
        ) + 1
        return total, actual_dur


# ---------------------------------------------------------------------------
# Forecast Fetching
# ---------------------------------------------------------------------------

def fetch_point_forecast(
    lat: float,
    lon: float,
    model: str = "ecmwf_ifs025",
    forecast_days: int = 7,
    include_historical_hours: int = 0,
) -> WeatherForecast:
    """
    Fetch hourly rainfall forecast for a point location.

    Args:
        lat: Latitude (decimal degrees)
        lon: Longitude (decimal degrees)
        model: Weather model key (default: ECMWF IFS)
        forecast_days: Number of days to forecast (1–16)
        include_historical_hours: Hours of past data to include

    Returns:
        WeatherForecast object
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "precipitation,rain,snowfall",
        "timezone": INDIA_TIMEZONE,
        "forecast_days": min(forecast_days, 16),
        "models": model,
    }

    if include_historical_hours > 0:
        params["past_hours"] = include_historical_hours

    logger.info(f"Fetching forecast: lat={lat}, lon={lon}, model={model}, "
                f"days={forecast_days}")

    try:
        response = requests.get(OPEN_METEO_FORECAST_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        raise RuntimeError(f"Open-Meteo API error: {e}")

    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    precip = hourly.get("precipitation", [0.0] * len(times))
    rain = hourly.get("rain", [0.0] * len(times))
    snow = hourly.get("snowfall", [0.0] * len(times))

    # Replace None with 0
    precip = [v if v is not None else 0.0 for v in precip]
    rain = [v if v is not None else 0.0 for v in rain]
    snow = [v if v is not None else 0.0 for v in snow]

    fc = WeatherForecast(
        lat=data.get("latitude", lat),
        lon=data.get("longitude", lon),
        model=model,
        times=times,
        precipitation_mm=precip,
        rain_mm=rain,
        snowfall_cm=snow,
        source=f"open-meteo/{model}",
    )

    total = fc.total_precipitation_mm
    peak = fc.peak_intensity_mm_hr()
    logger.info(f"Forecast received: {len(times)} hours, "
                f"total={total:.1f}mm, peak={peak:.1f}mm/hr")
    return fc


def fetch_historical_rainfall(
    lat: float,
    lon: float,
    start_date: str,
    end_date: str,
) -> WeatherForecast:
    """
    Fetch historical rainfall from ERA5 reanalysis.

    Args:
        lat: Latitude
        lon: Longitude
        start_date: 'YYYY-MM-DD'
        end_date: 'YYYY-MM-DD'

    Returns:
        WeatherForecast with ERA5 historical data
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": "precipitation,rain,snowfall",
        "timezone": INDIA_TIMEZONE,
    }

    logger.info(f"Fetching ERA5 historical: {start_date} → {end_date}")
    try:
        response = requests.get(OPEN_METEO_HISTORICAL_URL, params=params, timeout=60)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        raise RuntimeError(f"ERA5 API error: {e}")

    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    precip = [v if v is not None else 0.0 for v in hourly.get("precipitation", [])]
    rain = [v if v is not None else 0.0 for v in hourly.get("rain", [])]
    snow = [v if v is not None else 0.0 for v in hourly.get("snowfall", [])]

    return WeatherForecast(
        lat=lat, lon=lon, model="era5",
        times=times, precipitation_mm=precip,
        rain_mm=rain, snowfall_cm=snow,
        source="open-meteo/era5",
    )


# ---------------------------------------------------------------------------
# Spatial Gridded Forecast
# ---------------------------------------------------------------------------

def fetch_spatial_forecast(
    bbox: Tuple[float, float, float, float],
    model: str = "ecmwf_ifs025",
    forecast_days: int = 3,
    grid_points: int = 5,
) -> Dict:
    """
    Fetch rainfall forecasts over a spatial grid within a bounding box.

    Samples `grid_points × grid_points` locations within bbox and
    returns a spatial rainfall map.

    Args:
        bbox: (min_lon, min_lat, max_lon, max_lat)
        model: Weather model
        forecast_days: Forecast horizon
        grid_points: Number of sample points per dimension

    Returns:
        Dict with:
          - 'lats': array of latitudes
          - 'lons': array of longitudes
          - 'rainfall_mm': 2D array of total forecast rainfall (mm)
          - 'peak_intensity_mm_hr': 2D array of peak intensity
          - 'duration_hr': representative event duration
    """
    min_lon, min_lat, max_lon, max_lat = bbox
    lats = np.linspace(min_lat, max_lat, grid_points)
    lons = np.linspace(min_lon, max_lon, grid_points)

    rainfall_grid = np.zeros((grid_points, grid_points))
    peak_grid = np.zeros((grid_points, grid_points))

    total_hours = min(forecast_days * 24, 72)
    durations = []

    for i, lat in enumerate(lats):
        for j, lon in enumerate(lons):
            try:
                fc = fetch_point_forecast(lat, lon, model, forecast_days)
                total_rain, dur = fc.to_event_rainfall(total_hours)
                rainfall_grid[i, j] = total_rain
                peak_grid[i, j] = fc.peak_intensity_mm_hr()
                durations.append(dur)
            except Exception as e:
                logger.warning(f"Failed to fetch for ({lat:.2f}, {lon:.2f}): {e}")
                rainfall_grid[i, j] = 0.0

    avg_duration = float(np.mean(durations)) if durations else total_hours

    logger.info(
        f"Spatial forecast grid ({grid_points}×{grid_points}): "
        f"mean rain={np.mean(rainfall_grid):.1f}mm, "
        f"max rain={np.max(rainfall_grid):.1f}mm, "
        f"avg duration={avg_duration:.1f}hr"
    )

    return {
        "lats": lats,
        "lons": lons,
        "rainfall_mm": rainfall_grid,
        "peak_intensity_mm_hr": peak_grid,
        "duration_hr": avg_duration,
        "model": model,
        "bbox": bbox,
    }


def interpolate_rainfall_to_grid(
    spatial_forecast: Dict,
    target_shape: Tuple[int, int],
    bbox: Tuple[float, float, float, float],
) -> np.ndarray:
    """
    Bilinearly interpolate the sparse spatial forecast to the DEM grid.

    Args:
        spatial_forecast: Output from fetch_spatial_forecast()
        target_shape: (rows, cols) of DEM grid
        bbox: (min_lon, min_lat, max_lon, max_lat)

    Returns:
        2D numpy array of interpolated rainfall (mm) at DEM resolution
    """
    from scipy.interpolate import RegularGridInterpolator

    lats = spatial_forecast["lats"]
    lons = spatial_forecast["lons"]
    rain_grid = spatial_forecast["rainfall_mm"]

    # Create interpolator (note: rasterio uses row=lat,col=lon convention)
    interp = RegularGridInterpolator(
        (lats, lons), rain_grid,
        method="linear", bounds_error=False,
        fill_value=np.mean(rain_grid),
    )

    min_lon, min_lat, max_lon, max_lat = bbox
    nrows, ncols = target_shape
    target_lats = np.linspace(max_lat, min_lat, nrows)  # N→S
    target_lons = np.linspace(min_lon, max_lon, ncols)

    grid_lons, grid_lats = np.meshgrid(target_lons, target_lats)
    points = np.column_stack([grid_lats.ravel(), grid_lons.ravel()])

    interpolated = interp(points).reshape(target_shape)
    logger.info(f"Interpolated rainfall to {target_shape}: "
                f"mean={np.mean(interpolated):.1f}mm, max={np.max(interpolated):.1f}mm")
    return interpolated.astype(np.float32)


# ---------------------------------------------------------------------------
# IMD Rainfall Categories and Flood Alert Logic
# ---------------------------------------------------------------------------

def assess_flood_risk_from_forecast(
    fc: WeatherForecast,
    duration_hr: int = 24,
) -> Dict:
    """
    Assess flood risk level from forecast data using IMD thresholds.

    Args:
        fc: WeatherForecast object
        duration_hr: Event duration to evaluate

    Returns:
        Dict with risk assessment
    """
    total_rain, actual_dur = fc.to_event_rainfall(duration_hr)
    peak_intensity = fc.peak_intensity_mm_hr()

    # IMD 24-hour rainfall thresholds
    if total_rain > 204.5:
        risk_level = "EXTREME"
        alert = "🔴 RED ALERT — Extremely Heavy Rain. Severe flooding expected."
    elif total_rain > 115.6:
        risk_level = "HIGH"
        alert = "🟠 ORANGE ALERT — Very Heavy Rain. Significant flooding likely."
    elif total_rain > 64.5:
        risk_level = "MEDIUM"
        alert = "🟡 YELLOW ALERT — Heavy Rain. Localised flooding possible."
    elif total_rain > 35.5:
        risk_level = "LOW"
        alert = "🟢 WATCH — Moderate to heavy rain. Monitor low-lying areas."
    else:
        risk_level = "MINIMAL"
        alert = "ℹ️  Light to moderate rain. Minimal flood risk."

    return {
        "total_rainfall_mm": round(total_rain, 1),
        "peak_intensity_mm_hr": round(peak_intensity, 1),
        "event_duration_hr": actual_dur,
        "risk_level": risk_level,
        "imd_alert": alert,
        "suitable_for_simulation": total_rain >= 15.0,
    }
