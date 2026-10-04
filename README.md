# 🌊 JAL-RAKSHA (जल रक्षा) v4.1
### Autonomous Hydrodynamic Dam-Break, GLOF & Flash Flood Inundation Decision Support System for Humanitarian Assistance and Disaster Relief (HADR)

[![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com)
[![Tests](https://img.shields.io/badge/tests-24%20passed%20(100%25)-brightgreen.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CWC & NDMA Aligned](https://img.shields.io/badge/Guidelines-CWC%20%26%20NDMA-orange.svg)]()

> **Problem Statement ID:** SIH26161 (NTRO HADR Priority Deliverable)  
> **Theme:** Disaster Management, Water Resources & Defense Space Technology  
> **Mission:** Detect. Measure. Simulate. Visualize. Protect. Document.

---

## 📌 Overview

**Jal-Raksha** is an autonomous, web-based, end-to-end Hydrodynamic Decision Support System (DSS) purpose-built for tactical HADR command, dam safety monitoring, and emergency evacuation management across the Indian subcontinent.

It eliminates manual bathymetric data wrangling by unifying open-source global elevation data (**Copernicus GLO-30 30m DEM**), pre-configured river networks across Indian basins, dual hydrodynamic computational solvers, and automated satellite verification via **Google Earth Engine (GEE)**.

```
┌──────────┐     ┌───────────┐     ┌────────────┐     ┌─────────────┐     ┌───────────┐     ┌──────────────┐
│  DETECT  │ ──> │  MEASURE  │ ──> │  SIMULATE  │ ──> │  VISUALIZE  │ ──> │  PROTECT  │ ──> │   DOCUMENT   │
└──────────┘     └───────────┘     └────────────┘     └─────────────┘     └───────────┘     └──────────────┘
  S1 SAR / S2      GLO-30 WSE        2D Bathtub/SWE      Dynamic Time       Human Triage      13-Sec Dossier
  Change Radar     Lake Geometry     SPH Particles       Slider Maps        & Evacuation      SHP/KML Export
```

---

## ✨ Key Capabilities

1. **Dual Hydrodynamic Solver Architecture:**
   - **2D Depth-Averaged SWE (Delft3D-Equivalent):** Continuum-scale shallow water equations modeling diffusive backwater, valley spreading, and dynamic Manning bed resistance.
   - **Smoothed-Particle Hydrodynamics (SPH):** Lagrangian particle model capturing violent, highly transient near-field dam breach wavefront shocks.
   - **Adaptive Rapid Fallback Engine:** 2D DEM Priority-Flood bathtub solver combined with 1D Muskingum-Cunge diffusion routing (computes 50km river corridors in under 15 seconds).
2. **Geotechnical Breach Mechanics & Debris Bulking:**
   - Erodible dams: Hanson & Temple (1997) excess shear stress incision ($E_r = k_d(\tau - \tau_c)$) + side-slope widening.
   - Concrete/Masonry dams: Structural overtopping failure paradigm.
   - Dynamic debris-flow bulking factor ($1.0\times$ to $15.0\times$) for sediment-laden Himalayan flash floods.
3. **Pan-India Dam Registry (65+ Dams):**
   - Pre-loaded with major Indian dams across all river basins (Tehri, Bhakra, Idukki, Mullaperiyar, Sardar Sarovar, Hirakud, Mettur, etc.).
   - Interactive Centerline Drawing Tool & automated **D8 flow-direction algorithm** on Copernicus GLO-30 DEM for arbitrary river points.
4. **Interactive Command Console:**
   - Dark-themed operational GIS dashboard (Google Hybrid, ESRI Satellite, Topo basemaps).
   - Time-slider playback animating flood wave progression minute-by-minute.
   - Multi-scenario risk envelope: Minor ($0.4\times$), Moderate ($0.7\times$), Major ($1.0\times$), and Catastrophic PMF ($1.4\times$).
5. **Humanitarian Protection & Evacuation Triage:**
   - Socio-economic exposure triage via OpenStreetMap (OSM) footprints and demographic clusters.
   - People hazard rating via DEFRA FD2320 ($d \cdot v$ hazard categories).
   - Evacuation feasibility ratio ($T_{\text{warn}} / T_{\text{evac}}$) categorizing zones into Green ($\ge 1.6$), Amber ($\ge 1.2$), and Red ($< 1.2$, triggering vertical evacuation).
6. **Automated GIS & Emergency Exports:**
   - **ESRI Shapefile Package (`.zip`):** Authoritative `.shp`, `.shx`, `.dbf`, `.prj` layers for QGIS and ArcGIS.
   - **Google Earth 3D KML (`.kml`):** Terrain-clamped 3D vector files.
   - **13-Section Disaster Dossier:** Comprehensive executive report with data freshness manifest and CWC/NDMA compliance.
7. **Satellite Ground-Truth Validation via GEE (NTRO Deliverable iv):**
   - Cloud-ready Google Earth Engine script generator using Sentinel-1 SAR (IW/VV) change detection ($\Delta\sigma^0 < -2.5\text{ dB}$) to calculate Critical Success Index (CSI).

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.11, 3.12, or 3.13
- Git

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/your-username/jal-raksha.git
cd jal-raksha

# Create and activate virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment
```bash
cp .env.example .env
# Edit .env to set your JWT_SECRET and ADMIN_PASSWORD
```

### 4. Run Automated Tests
```bash
pytest tests/ -q
# All 24 test suites must pass
```

### 5. Launch Application
```bash
python run.py
```
Open your browser and navigate to:
- **Interactive UI:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive API Documentation:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## ⚙️ Environment Variables

Configure `.env` using `.env.example`:

| Variable | Default | Description |
|---|---|---|
| `JWT_SECRET` | `change-me...` | Secret key for JWT authentication |
| `JR_ENV` | `development` | `development` or `production` |
| `ADMIN_USERNAME` | `admin` | Default platform administrator username |
| `ADMIN_PASSWORD` | `ChangeMeNow123` | Default administrator password |
| `CORS_ORIGINS` | `http://localhost:8000` | Allowed CORS origins |
| `DB_PATH` | `data/jalraksha.db` | SQLite database file location |
| `MC_RUNS` | `120` | Number of Monte Carlo uncertainty iterations |
| `CDSE_USERNAME` | *(optional)* | Copernicus Data Space credentials |
| `CDSE_PASSWORD` | *(optional)* | Copernicus Data Space credentials |

---

## 📂 Project Structure

```
jal-raksha/
├── app/
│   ├── main.py                   # FastAPI application & middleware
│   ├── config.py                 # Configuration loader & constants
│   ├── db.py                     # SQLAlchemy database models & connection pooling
│   ├── jobs.py                   # Async job queue with cancellation & progress
│   ├── schemas.py                # Pydantic validation schemas
│   ├── security.py              # JWT authentication & RBAC
│   ├── routers/                  # API endpoints (incidents, simulations, dams, etc.)
│   └── services/                 # Hydrodynamic solvers, DEM processing & impact models
├── frontend/
│   ├── index.html                # Operational command dashboard
│   ├── css/style.css             # Dark/Light responsive UI styling
│   └── js/
│       ├── app.js                # Core map, UI, and simulation controllers
│       └── app_ext.js            # Hydrodynamic suite & fastflood integration
├── data/                         # River networks, major dams registry, and DEM caches
├── docs/                         # Methodology, sources, limitations & API reference
├── tests/
│   └── test_platform.py          # 24 end-to-end integration & unit test suites
├── requirements.txt              # Production Python dependencies
└── run.py                        # Server runner
```

---

## 📖 Methodology & Documentation

Detailed scientific documentation is available in [`docs/`](docs/):
- [`01_SOURCES.md`](docs/01_SOURCES.md) — Remote sensing data sources, sensors, and DEM references.
- [`02_METHODOLOGY.md`](docs/02_METHODOLOGY.md) — Mathematical formulations for breach, routing, and evacuation.
- [`03_IMPLEMENTATION_PLAN.md`](docs/03_IMPLEMENTATION_PLAN.md) — Operational deployment phases.
- [`05_LIMITATIONS.md`](docs/05_LIMITATIONS.md) — Model limitations, assumptions, and validity boundaries.
- [`06_API_REFERENCE.md`](docs/06_API_REFERENCE.md) — REST API endpoint definitions.

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
