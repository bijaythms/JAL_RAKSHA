# Methodology

## Pipeline
DETECT -> MEASURE -> SIMULATE -> VISUALIZE -> PROTECT -> DOCUMENT

### 1. Detection (detection.py, roi.py, baseline.py)
All masks are cropped to the zone grid via rasterio transforms immediately
after decode - georeferencing is exact. Baseline: 4-12 historical Landsat
scenes -> per-pixel water frequency. Current: S1 SAR sigma0<-17 dB
(preferred, all-weather) or S2/Landsat MNDWI>0 AND NDWI>0. New water =
currently wet where baseline freq < 0.10, minus river-exclusion buffer
(persistent water dilated 300 m default) and outside any analyst ROI.
Components rejected by boundary-adjacency (>=0.90), compactness
(4*pi*A/P^2), min area 5,000 m2. Void scenes (<15% valid pixels) leave
candidates unchanged.

### 2. Geometry (lake_geometry.py, dem.py)
WSE = 60th percentile of shoreline-ring DEM elevations (spread ->
uncertainty); depth = WSE - bed p10; volume = sum(max(WSE-z,0))*cell_area
over the lake window (Copernicus GLO-30, 30 m posting).

### 3. Breach (breach_models.py)
Erodible dams: level-pool mass balance + broad-crested weir
(Q = 1.7 b H^1.5) + excess-shear incision (Hanson & Temple 1997) +
side-slope widening. Concrete/Masonry: overtopping-only paradigm
(fixed section, no erosion) - explicitly a different failure physics.
Empirical ensemble (Kirkpatrick/SCS/USBR/Froehlich) reported alongside
with spread ratio. Mass-balance closure error computed and reported.

### 4. Routing (inundation_2d.py + hydraulics.py)
**Primary — 2D raster Priority-Flood bathtub (inundation_2d.py):** When a
GLO-30 GeoTIFF is available (cached tile or freshly fetched via `dem_for_bbox`),
the pipeline runs a raster flood-fill over the DEM.  D8 flow-direction is
pre-computed to identify downslope connectivity.  A Priority-Flood algorithm
(min-heap on cell elevation) then inundates cells in order of increasing
elevation, starting from the breach cell, until the cumulative released volume
V(t) is consumed.  Six time-stepped WSE maps are produced; the union mask gives
the maximum flood extent.  Cell areas × count give authoritative area in km².
Nodes are sampled at 500 m along the centerline for API compatibility.

**Bathtub limitations:** This is NOT a solution of the 2D shallow-water
equations.  No momentum, inertia, or backwater effects are modelled.  WSE
advances hydrostatically; results are suitable for broad valley flood-extent
mapping but not for near-dam hydraulic design.  GLO-30 vertical accuracy ±5 m.

**Fallback — 1D Muskingum-Cunge (hydraulics.py):** When DEM bytes are
unavailable (rasterio absent, network failure, or DEM outside coverage),
`try_2d_then_fallback` reverts to 1D Muskingum-Cunge on the centerline
(500 m nodes); Manning normal depth; corridor-envelope extent (grid-sampled
authoritative area); clamped-reach count surfaced.  The fallback is flagged in
`inundation.limitations` and in the top-level `used_2d: false` field.
NOT a 2D SWE solution — stated in every report.

### 5. Uncertainty
Monte Carlo (120 runs): width xLogN(0,.25), time xLogN(0,.30),
n xLogN(0,.15) -> p10/p50/p90. TDRI sensitivity: renormalized +/-20%
one-at-a-time weight perturbation. Confidence: additive provenance rubric
(max 90%), itemized per run.

### 6. Impacts & evacuation (impact_models.py, evacuation.py)
People: d*v classes (FD2320). Buildings: JRC Asia depth-damage curve.
Agriculture: depth-band x crop sensitivity x duration. Economics:
PLACEHOLDER unit rates (flagged everywhere). Evacuation: feasibility ratio
T_warn/(mobilization + walking-to-fringe); GREEN>=1.6, AMBER>=1.2,
RED<1.2 => vertical evacuation. Walking is a LOWER bound (no road network).

### 7. Reporting (full_report.py)
13-section dossier assembled from STORED artifacts only; freshness
manifest (FRESH<72h/STALE/MISSING); exact simulation parameters embedded;
limitations aggregated; recommendations keyed to TDRI band; stale items
echoed in the final summary.

## Data-integrity invariants (tested)
1. Reports derive from stored Simulation rows - cannot contradict runs.
2. Detection georeferencing round-trips through the zone grid.
3. Breach mass-balance closure < 1%.
4. Growth observations unique per (candidate, scene).
5. Every placeholder number (unit costs, k_d, CN) is labeled in payloads.
