"""River-exclusion buffers + analyst ROI polygons.
Exclusion overrides all classes (defense in depth). Exact even-odd
rasterization - no bbox approximation."""
import math
import numpy as np


def dilate_mask(mask, px):
    if px <= 0:
        return mask.astype(bool).copy()
    m = mask.astype(bool).copy()
    for _ in range(int(px)):
        p = np.pad(m, 1, constant_values=False)
        m = (p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:] |
             p[:-2, :-2] | p[:-2, 2:] | p[2:, :-2] | p[2:, 2:] | m)
    return m


def river_exclusion(persistent, res_m, buffer_m):
    px = max(3, int(math.ceil(buffer_m / max(res_m, 1.0))))
    return dilate_mask(persistent, px), px


def rasterize_polygon(polygon, shape, bbox):
    h, w = shape
    if len(polygon) < 3:
        raise ValueError("ROI polygon needs >= 3 [lat, lon] vertices")
    minlat, minlon, maxlat, maxlon = bbox
    ys = maxlat - (np.arange(h) + 0.5) * (maxlat - minlat) / h
    xs = minlon + (np.arange(w) + 0.5) * (maxlon - minlon) / w
    Y, X = np.meshgrid(ys, xs, indexing="ij")
    inside = np.zeros((h, w), dtype=bool)
    n = len(polygon)
    for i in range(n):
        la1, lo1 = float(polygon[i][0]), float(polygon[i][1])
        la2, lo2 = float(polygon[(i + 1) % n][0]), float(polygon[(i + 1) % n][1])
        if la1 == la2:
            continue
        cond = (la1 > Y) != (la2 > Y)
        with np.errstate(divide="ignore", invalid="ignore"):
            lon_int = (lo2 - lo1) * (Y - la1) / (la2 - la1) + lo1
        inside ^= cond & (X < lon_int)
    return inside


def validate_roi_polygon(polygon, zone_bbox, max_vertices=200):
    warnings = []
    if not isinstance(polygon, list) or len(polygon) < 3:
        raise ValueError("ROI polygon needs a list of >= 3 [lat, lon] vertices")
    if len(polygon) > max_vertices:
        warnings.append(f"Truncated to first {max_vertices} vertices.")
        polygon = polygon[:max_vertices]
    cleaned = []
    for p in polygon:
        if not isinstance(p, (list, tuple)) or len(p) != 2:
            raise ValueError("Each vertex must be [lat, lon]")
        la, lo = float(p[0]), float(p[1])
        if not (-90 <= la <= 90 and -180 <= lo <= 180):
            raise ValueError(f"Vertex out of range: [{la}, {lo}]")
        cleaned.append([round(la, 6), round(lo, 6)])
    dedup = [cleaned[0]]
    for p in cleaned[1:]:
        if p != dedup[-1]:
            dedup.append(p)
    if len(dedup) < 3:
        raise ValueError("Fewer than 3 distinct vertices after dedup")
    cleaned = dedup
    minlat, minlon, maxlat, maxlon = zone_bbox
    out = [p for p in cleaned
           if not (minlat - 0.02 <= p[0] <= maxlat + 0.02 and
                   minlon - 0.02 <= p[1] <= maxlon + 0.02)]
    if out:
        warnings.append(f"{len(out)} vertices fall outside the zone bbox "
                        "(+2 km tolerance) - the ROI will be clipped to the "
                        "zone grid at scan time.")
    area_km2 = polygon_area_km2(cleaned)
    if area_km2 < 0.05:
        raise ValueError(f"ROI area {area_km2:.4f} km2 is too small "
                         "(min 0.05 km2)")
    if area_km2 > 500:
        warnings.append(f"ROI is very large ({area_km2:.0f} km2) - consider "
                        "splitting.")
    return cleaned, warnings


def polygon_area_km2(polygon):
    la0 = sum(p[0] for p in polygon) / len(polygon)
    kx = 111_320 * math.cos(math.radians(la0))
    ky = 110_540
    x = [(p[1]) * kx for p in polygon]
    y = [(p[0]) * ky for p in polygon]
    s = sum(x[i] * y[i + 1] - x[i + 1] * y[i] for i in range(len(polygon) - 1))
    s += x[-1] * y[0] - x[0] * y[-1]
    return abs(s) / 2 / 1e6


def classify_with_exclusion(baseline_freq, current_water, roi_mask=None,
                            exclusion_mask=None,
                            new_water_thresh=0.10, persistent_thresh=0.50):
    """Classes: 0 land, 1 persistent, 2 seasonal, 3 NEW water,
    4 EXCLUDED (river buffer or outside ROI). EXCLUDED overrides all."""
    cls = np.zeros(baseline_freq.shape, dtype="uint8")
    cls[baseline_freq >= persistent_thresh] = 1
    cls[(baseline_freq >= new_water_thresh) &
        (baseline_freq < persistent_thresh)] = 2
    cls[current_water & (baseline_freq < new_water_thresh)] = 3
    if exclusion_mask is not None:
        cls[exclusion_mask & (cls != 1)] = 4
    if roi_mask is not None:
        cls[~roi_mask] = 4
    return cls


def coverage_stats(cls, roi_mask=None):
    total = cls.size
    roi_px = int(roi_mask.sum()) if roi_mask is not None else total
    return {
        "grid_pixels": int(total), "roi_pixels": roi_px,
        "roi_fraction": round(roi_px / max(total, 1), 3),
        "excluded_pixels": int((cls == 4).sum()),
        "excluded_fraction_of_roi": round(int((cls == 4).sum()) /
                                          max(roi_px, 1), 3),
        "new_water_pixels": int((cls == 3).sum()),
        "persistent_pixels_in_roi": int(((cls == 1) &
            (roi_mask if roi_mask is not None else
             np.ones_like(cls, bool))).sum())}
