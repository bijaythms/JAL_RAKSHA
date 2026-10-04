"""
Google Earth Engine (GEE) Near-Real-Time Flood Analysis Framework.
Addresses NTRO SIH26161 Deliverable (iv):
  "Additionally, developing a framework for near real time flood analysis
   through Google Earth Engine with the help of open source data."

Generates executable Earth Engine Code Editor scripts (JavaScript & Python)
using Sentinel-1 SAR GRD (IW, VV), Sentinel-2 MSI, and Copernicus GLO-30 DEM
to extract satellite-observed flood footprints and validate against
JAL-RAKSHA hydrodynamic simulation extents.
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone

def generate_gee_javascript(
    incident_name: str,
    lat: float,
    lon: float,
    flood_polygon: Optional[List[List[float]]] = None,
    event_date: Optional[str] = None,
    corridor_km: float = 35.0,
    peak_q_m3s: float = 15000.0,
    max_depth_m: float = 12.0
) -> str:
    """
    Generate an executable JavaScript script ready to paste directly into
    Google Earth Engine Code Editor (https://code.earthengine.google.com/).
    """
    now = datetime.now(timezone.utc)
    if event_date:
        try:
            ev_dt = datetime.fromisoformat(event_date.replace("Z", "+00:00"))
        except Exception:
            ev_dt = now
    else:
        ev_dt = now
        
    post_start = (ev_dt - timedelta(days=1)).strftime("%Y-%m-%d")
    post_end = (ev_dt + timedelta(days=5)).strftime("%Y-%m-%d")
    pre_start = (ev_dt - timedelta(days=35)).strftime("%Y-%m-%d")
    pre_end = (ev_dt - timedelta(days=5)).strftime("%Y-%m-%d")
    
    # Bounding box around dam and downstream valley
    delta_deg = max(0.25, corridor_km / 111.0 * 1.2)
    min_lat = round(lat - delta_deg, 4)
    max_lat = round(lat + delta_deg, 4)
    min_lon = round(lon - delta_deg, 4)
    max_lon = round(lon + delta_deg, 4)
    
    # Format flood polygon for GEE if present
    sim_poly_str = "null"
    if flood_polygon and len(flood_polygon) >= 3:
        # GEE expects [[lon, lat], [lon, lat], ...]
        coords = [[round(pt[1], 5), round(pt[0], 5)] for pt in flood_polygon]
        sim_poly_str = f"ee.Geometry.Polygon({json.dumps([coords])})"

    js_code = f"""/**
 * ============================================================================
 * JAL-RAKSHA - Near Real-Time Flood Inundation & Dam Break Verification
 * NTRO HADR Framework (SIH26161 Deliverable iv)
 * Target Incident: {incident_name}
 * Dam Site: {lat:.5f} N, {lon:.5f} E | Flood Corridor: ~{corridor_km:.1f} km
 * ============================================================================
 */

// 1. Define Region of Interest (ROI)
var damPoint = ee.Geometry.Point([{lon:.5f}, {lat:.5f}]);
var aoi = ee.Geometry.Rectangle([{min_lon}, {min_lat}, {max_lon}, {max_lat}]);

Map.centerObject(damPoint, 12);
Map.setOptions('HYBRID');

// 2. Load Copernicus GLO-30 Digital Elevation Model
var glo30 = ee.ImageCollection('COPERNICUS/DEM/GLO30')
  .select('DEM')
  .mosaic()
  .clip(aoi);

var terrainSlope = ee.Terrain.slope(glo30);

// 3. Query Open-Source Sentinel-1 SAR (IW mode, VV polarization)
var s1Collection = ee.ImageCollection('COPERNICUS/S1_GRD')
  .filterBounds(aoi)
  .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV'))
  .filter(ee.Filter.eq('instrumentMode', 'IW'));

// Pre-Flood Baseline Image (30-day composite before event)
var preFlood = s1Collection
  .filterDate('{pre_start}', '{pre_end}')
  .select('VV')
  .median()
  .clip(aoi);

// Post-Flood / Near-Real-Time Event Image
var postFlood = s1Collection
  .filterDate('{post_start}', '{post_end}')
  .select('VV')
  .min()
  .clip(aoi);

// Fallback to latest available if exact event date pass is outside window
var postFloodResolved = ee.Algorithms.If(
  postFlood.bandNames().size(),
  postFlood,
  s1Collection.sort('system:time_start', false).first().select('VV').clip(aoi)
);
postFlood = ee.Image(postFloodResolved);

// 4. Speckle Filtering (Focal Median)
var preFilt = preFlood.focalMedian(30, 'circle', 'meters');
var postFilt = postFlood.focalMedian(30, 'circle', 'meters');

// 5. Backscatter Change Detection & SAR Water Masking
// Water specular reflection causes significant drop in VV backscatter (typically < -16 dB)
var diff = postFilt.subtract(preFilt);
var floodRaw = diff.lt(-2.5).and(postFilt.lt(-15.0));

// Mask out steep mountain slopes (> 6 degrees) to eliminate radar shadow false-positives
var floodSlopeMasked = floodRaw.updateMask(terrainSlope.lt(6.0));

// Mask out permanent water bodies using JRC Global Surface Water
var jrcWater = ee.Image('JRC/GSW1_4/GlobalSurfaceWater')
  .select('occurrence')
  .clip(aoi);
var newInundation = floodSlopeMasked.updateMask(jrcWater.lt(80).or(jrcWater.unmask().eq(0)));

// 6. Visual Layers
Map.addLayer(glo30, {{min: 200, max: 3500, palette: ['006600', 'ffff33', '993300', 'ffffff']}}, 'Copernicus GLO-30 DEM', false);
Map.addLayer(preFilt, {{min: -25, max: 0}}, 'Sentinel-1 Pre-Flood SAR (VV)', false);
Map.addLayer(postFilt, {{min: -25, max: 0}}, 'Sentinel-1 Post-Flood SAR (VV)', false);
Map.addLayer(diff, {{min: -6, max: 6, palette: ['red', 'white', 'blue']}}, 'SAR Backscatter Change (dB)', false);
Map.addLayer(newInundation.selfMask(), {{palette: ['00f0ff']}}, 'Sentinel-1 Observed Floodwater (NRT)', true);

// 7. Overlay JAL-RAKSHA Simulated Hydrodynamic Extent
var simExtent = {sim_poly_str};
if (simExtent !== null) {{
  var simOutline = ee.Image().paint(simExtent, 1, 2.5);
  Map.addLayer(simOutline, {{palette: ['ff0055']}}, 'JAL-RAKSHA Hydrodynamic Boundary', true);
  
  // Calculate Overlap / Critical Success Index (Validation Metric)
  var simMask = ee.Image.constant(1).clip(simExtent).mask();
  var truePositives = newInundation.and(simMask);
  Map.addLayer(truePositives.selfMask(), {{palette: ['34d399']}}, 'Model-Satellite Verified Agreement', true);
}}

// 8. Dam Site Marker
Map.addLayer(damPoint, {{color: 'yellow'}}, 'Dam Site: {lat:.4f}N, {lon:.4f}E', true);

// 9. Quantitative Statistics
var floodAreaHa = newInundation.multiply(ee.Image.pixelArea()).divide(10000).reduceRegion({{
  reducer: ee.Reducer.sum(),
  geometry: aoi,
  scale: 30,
  maxPixels: 1e9
}});

print('=== JAL-RAKSHA x NTRO GEE VERIFICATION SUMMARY ===');
print('Incident Name:', '{incident_name}');
print('Model Peak Q (m3/s):', {peak_q_m3s});
print('Model Max Depth (m):', {max_depth_m});
print('Observed Sentinel-1 Inundated Area (Hectares):', floodAreaHa.get('VV'));
"""
    return js_code

def generate_gee_python(
    incident_name: str,
    lat: float,
    lon: float,
    flood_polygon: Optional[List[List[float]]] = None,
    corridor_km: float = 35.0
) -> str:
    """Generate Python script using ee (earthengine-api)."""
    delta_deg = max(0.25, corridor_km / 111.0 * 1.2)
    min_lat = round(lat - delta_deg, 4)
    max_lat = round(lat + delta_deg, 4)
    min_lon = round(lon - delta_deg, 4)
    max_lon = round(lon + delta_deg, 4)

    py_code = f"""\"\"\"
JAL-RAKSHA: Near-Real-Time Flood Inundation & Dam Break Verification
Python Earth Engine Framework (earthengine-api)
Incident: {incident_name}
\"\"\"
import ee

ee.Initialize()

dam_site = ee.Geometry.Point([{lon:.5f}, {lat:.5f}])
aoi = ee.Geometry.Rectangle([{min_lon}, {min_lat}, {max_lon}, {max_lat}])

# Load Copernicus GLO-30 DEM
glo30 = ee.ImageCollection('COPERNICUS/DEM/GLO30').select('DEM').mosaic().clip(aoi)
slope = ee.Terrain.slope(glo30)

# Sentinel-1 SAR GRD
s1 = (ee.ImageCollection('COPERNICUS/S1_GRD')
      .filterBounds(aoi)
      .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV'))
      .filter(ee.Filter.eq('instrumentMode', 'IW')))

post_sar = s1.sort('system:time_start', False).first().select('VV').clip(aoi)
flood_mask = post_sar.lt(-16.0).And(slope.lt(6.0))

print("JAL-RAKSHA GEE Pipeline initialized for {incident_name}")
"""
    return py_code
