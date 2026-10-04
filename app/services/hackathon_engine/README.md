# India Flood Inundation Engine 🌊

> **Hackathon Edition** | Based on van den Bout et al. (2026) — FastFlood Global Algorithm

A physics-based flood inundation modelling engine for India, implementing the **5-step FastFlood steady-state algorithm** with India-specific calibration. Produces interactive maps overlaid on **Google Hybrid** and **ESRI World Imagery** satellite basemaps.

---

## Quick Start

```bash
# Install dependencies
pip install numpy scipy rasterio folium matplotlib pillow requests branca tqdm

# Run demo (no internet needed — synthetic DEM)
python test_engine.py

# Run with your own rainfall values
python main.py --demo --rain 200 --dur 24

# Run with live weather forecast (needs internet)
python main.py --mode forecast --bbox 76.5 9.9 76.9 10.3

# Integrate into YOUR main.py (2 lines)
from flood_engine_api import run_flood_simulation
result = run_flood_simulation(bbox=(76.5, 9.9, 76.9, 10.3), rainfall_mm=150, duration_hr=12)
```

---

## Output Files

After running, find outputs in `outputs/` (or your custom output dir):

| File | Description |
|------|-------------|
| `flood_map_interactive.html` | **Interactive map** — open in browser |
| `flood_map.png` | Static 3-panel map (depth / risk / velocity) |
| `flood_depth_m.tif` | Flood depth GeoTIFF (metres) |
| `flood_velocity_ms.tif` | Flow velocity GeoTIFF (m/s) |
| `flood_hand_m.tif` | Height Above Nearest Drainage (m) |
| `flood_risk_class.tif` | Risk class raster (0–4) |
| `flood_report.json` | Simulation statistics |

---

## Interactive Map Features

The HTML map (`flood_map_interactive.html`) includes:

| Feature | Details |
|---------|---------|
| **Google Hybrid** | Satellite imagery + road labels (default) |
| **ESRI World Imagery** | Pure satellite basemap |
| **Google Satellite** | Satellite without labels |
| **OpenStreetMap** | Street map for context |
| **Flood Depth overlay** | Blue gradient, semi-transparent |
| **Risk Class overlay** | Yellow / Orange / Red / Purple (NDMA India) |
| **Flow Velocity overlay** | Yellow-to-red ramp |
| **IMD Alert Banner** | Red / Orange / Yellow based on rainfall |
| **Legend panel** | Depth scale + risk classes + simulation stats |
| **Fullscreen toggle** | Top-left button |
| **Measure tool** | Distance/area measurement |
| **Layer control** | Toggle basemaps and overlays |

---

## The 5-Step FastFlood Algorithm

```
Input: DEM, Rainfall, Land Cover, Soil Type
         │
Step 1: Terrain Conditioning (Fast Sweeping Algorithm)
         → Monotonically increasing DEM, slope computation
         │
Step 2: D8 Flow Routing
         → Flow direction + accumulation (upstream area)
         │
Step 3: Steady-State Discharge (SCS-CN Runoff)
         → Q_ss = q_eff × A   (effective rainfall × area)
         │
Step 4: Partial Steady-State Correction (SCS Lag Time)
         → Q_peak = Q_ss × f(t_event / T_c) × f_CWC
         │
Step 5: Depth Reconstruction (Manning's Inversion + HAND)
         → h = (Q·n / W·√S)^(3/5) at stream cells
         → flood_depth = max(0, h - HAND) at floodplain cells
         │
Output: Flood Depth Map, Risk Map, Velocity Map, Interactive HTML
```

---

## India Calibration

| Parameter | Standard (US) | India Adaptation |
|-----------|--------------|------------------|
| Initial abstraction λ | 0.2 | **0.1** (IS 5477, NIH Roorkee) |
| Unit hydrograph peak factor | 484 | **378** (CWC synthetic UH) |
| AMC-III CN adjustment | Standard | Monsoon pre-wetting |
| Channel width coefficients | Leopold & Maddock | **CWC regional surveys** |
| Soil HSG | USDA NRCS | Black cotton/Vertisol → D, Alluvial → B |

---

## Data Sources (All Free / Open)

| Data | Source | Resolution | API Key? |
|------|--------|-----------|----------|
| DEM (terrain) | NASADEM via OpenTopography | 30m | No (small areas) |
| Land Cover | ESA WorldCover 2021 (AWS S3) | 10m | No |
| Soil (HSG) | SoilGrids ISRIC | 250m | No |
| Rainfall Forecast | Open-Meteo (ECMWF IFS) | ~25km | No |
| Historical Rain | ERA5 via Open-Meteo | ~11km | No |

---

## Modes

```bash
# Mode 1: Manual rainfall
python main.py --mode manual --bbox 76.5 9.9 76.9 10.3 --rain 150 --dur 12

# Mode 2: Live weather forecast
python main.py --mode forecast --bbox 80.8 26.7 81.2 27.1

# Mode 3: Historical event (Kerala 2018)
python main.py --mode historical \
  --bbox 76.2 9.9 76.8 10.4 \
  --start-date 2018-08-01 --end-date 2018-08-20

# Mode 4: Quick demo (synthetic data, no internet)
python main.py --demo
```

---

## API Integration (into your existing main.py)

```python
from flood_engine_api import run_flood_simulation, run_with_forecast, run_scenario

# Manual rainfall
result = run_flood_simulation(
    bbox=(76.5, 9.9, 76.9, 10.3),
    rainfall_mm=150.0,
    duration_hr=12.0,
    amc="III",               # AMC-III for active monsoon
    output_dir="my_outputs",
)

# Live forecast
result = run_with_forecast(
    bbox=(76.5, 9.9, 76.9, 10.3),
    weather_model="ecmwf_ifs025",
)

# Pre-defined scenarios
result = run_scenario("kerala_monsoon")      # 200mm / 24hr
result = run_scenario("chennai_cyclone")     # 300mm / 12hr
result = run_scenario("assam_flood")         # 150mm / 48hr
result = run_scenario("delhi_flash_flood")   # 120mm / 3hr

# Access results
flood_depth   = result["flood_depth"]       # 2D numpy array (metres)
html_map_path = result["output_paths"]["html_map"]
stats         = result["stats"]
```

---

## Risk Classification (NDMA India)

| Class | Depth Range | Colour | Description |
|-------|------------|--------|-------------|
| 0 | < 10 cm | Transparent | No significant flood |
| 1 | 10–30 cm | 🟡 Yellow | Low — ankle-deep |
| 2 | 30–100 cm | 🟠 Orange | Medium — knee/waist |
| 3 | 1–2 m | 🔴 Red | High — above waist |
| 4 | > 2 m | 🟣 Purple | Extreme — life risk |

---

## File Structure

```
hackathon_flood_engine/
├── main.py                   # Main entry point (CLI + API)
├── flood_engine_api.py       # Clean API for your main.py
├── test_engine.py            # Quick demo (no internet)
├── requirements.txt
├── engine/
│   ├── dem_processor.py      # Step 1: Terrain conditioning (FSA)
│   ├── flow_router.py        # Step 2-3: D8 + discharge
│   ├── runoff_model.py       # SCS-CN runoff (India: λ=0.1)
│   ├── partial_correction.py # Step 4: SCS lag time + CWC
│   ├── depth_estimator.py    # Step 5: Manning's + HAND
│   └── inundation_mapper.py  # Output assembly + risk class
├── india_params/
│   ├── cn_table.py           # SCS-CN lookup (ESA class × HSG)
│   ├── manning_table.py      # Manning's n by land cover
│   └── monsoon_regions.py    # India monsoon region params
├── data/
│   ├── dem_downloader.py     # NASADEM / Copernicus download
│   ├── weather_forecast.py   # Open-Meteo API (free)
│   ├── soil_loader.py        # SoilGrids HSG
│   └── landcover_loader.py   # ESA WorldCover 2021
└── visualization/
    ├── flood_map_plot.py      # Google Hybrid + ESRI maps
    └── risk_classifier.py    # NDMA risk + flash flood index
```

---

## References

- van den Bout B., Kolaparambil F.J., van Roon K., Meijvogel D. (2026). *High-resolution interactive global flood forecast for past, present, and future.* EarthArXiv. [FastFlood Global]
- FastHazard B.V. FastFlood Core Algorithm Documentation. https://fastflood.org/documentation/fastflood_core.html
- SCS National Engineering Handbook Part 630 (2010). USDA-NRCS.
- Mishra S.K. & Singh V.P. (2003). Soil Conservation Service Curve Number (SCS-CN) Methodology. Springer.
- CWC (2017). Flood Estimation Reports — Subzone-wise (India). Central Water Commission.
- NDMA (2008). National Disaster Management Guidelines — Management of Floods. New Delhi.
- Nobre A.D. et al. (2011). Height Above the Nearest Drainage — a hydrologically relevant new terrain model. HESS.
