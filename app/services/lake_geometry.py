"""Lake geometry from GLO-30 + detected water bbox.
WSE = 60th percentile of shoreline-ring elevations; depth = WSE - bed p10;
volume = sum(max(WSE - z, 0)) * cell_area. Uncertainty from shoreline spread."""
import numpy as np
from .dem import dem_for_bbox, CELL_M


def _dilate(mask):
    p = np.pad(mask, 1)
    out = np.zeros_like(mask)
    h, w = mask.shape
    out |= (p[0:h, 0:w] | p[2:h+2, 2:w+2] | p[0:h, 2:w+2] | p[2:h+2, 0:w]
            | p[1:h+1, 1:w+1])
    return out


def lake_geometry_from_bbox(bbox, area_m2):
    minlon, minlat, maxlon, maxlat = bbox
    pad = 0.004
    grid = dem_for_bbox(minlat - pad, minlon - pad, maxlat + pad, maxlon + pad)
    if grid is None:
        return {"depth_m": None, "volume_m3": None, "wse_m": None,
                "dem_available": False,
                "geom_note": "Copernicus GLO-30 unavailable - area only. "
                             "Install rasterio and ensure network access."}
    H, W = grid.shape
    def y_of(lat): return int((maxlat + pad - lat) / (maxlat - minlat + 2*pad) * H)
    def x_of(lon): return int((lon - (minlon - pad)) / (maxlon - minlon + 2*pad) * W)
    y0, y1 = max(0, y_of(maxlat)), min(H, y_of(minlat))
    x0, x1 = max(0, x_of(minlon)), min(W, x_of(maxlon))
    if y1 <= y0 or x1 <= x0:
        return {"depth_m": None, "volume_m3": None, "wse_m": None,
                "dem_available": False, "geom_note": "empty DEM window"}
    inside = np.zeros((H, W), dtype=bool)
    inside[y0:y1, x0:x1] = True
    ring = _dilate(inside) & ~inside
    shore = grid[ring & ~np.isnan(grid)]
    bed = grid[inside & ~np.isnan(grid)]
    if shore.size < 5 or bed.size < 5:
        return {"depth_m": None, "volume_m3": None, "wse_m": None,
                "dem_available": False, "geom_note": "too few valid DEM pixels"}
    wse = float(np.percentile(shore, 60))
    shore_spread = float(np.percentile(shore, 90) - np.percentile(shore, 10))
    bed_p10 = float(np.percentile(bed, 10))
    depth = max(wse - bed_p10, 0.0)
    cell_area = CELL_M * CELL_M
    vol = float(np.nansum(np.clip(wse - grid[inside], 0, None)) * cell_area)
    dem_area = float(inside.sum()) * cell_area
    area_ratio = dem_area / max(area_m2, 1.0)
    note = (f"WSE from shoreline ring (p60, spread +/-{shore_spread:.1f} m); "
            f"volume by hypsometric integration at {CELL_M:.0f} m posting.")
    if area_ratio < 0.5:
        note += (" WARNING: image area >> DEM-window area - treat volume as "
                 "a lower bound.")
    return {
        "wse_m": round(wse, 1), "bed_elev_m": round(bed_p10, 1),
        "depth_m": round(depth, 1), "volume_m3": round(vol, 0),
        "depth_uncertainty_m": round(max(shore_spread, CELL_M * 0.5), 1),
        "volume_uncertainty_m3": round(
            vol * min(0.6, max(shore_spread, 5.0) / max(depth, 1.0)), 0),
        "dem_available": True, "dem": "Copernicus GLO-30",
        "geom_note": note,
        "limitations": [
            "GLO-30 posting is 30 m - lakes < ~1 ha cannot be resolved.",
            "WSE assumes the shoreline ring is at the water line.",
            "Bed DEM represents PRE-lake terrain only if the DEM predates "
            "the impoundment (2011-2015 era); post-event DEMs underestimate.",
            "Volume integrates over the bbox rectangle, not the exact water "
            "polygon."]}
