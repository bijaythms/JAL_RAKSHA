"""Pure-python geodesy, exact corridor tests, foldover-pruned display
buffers, centerline validation."""
import math
import numpy as np

R = 6371000.0

def haversine(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * R * math.asin(math.sqrt(a))

def bearing(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1)*math.sin(p2) - math.sin(p1)*math.cos(p2)*math.cos(dl)
    return math.degrees(math.atan2(y, x)) % 360

def destination(lat, lon, brg_deg, dist):
    p1, l1, b = map(math.radians, (lat, lon, brg_deg))
    p2 = math.asin(math.sin(p1)*math.cos(dist/R) +
                   math.cos(p1)*math.sin(dist/R)*math.cos(b))
    l2 = l1 + math.atan2(math.sin(b)*math.sin(dist/R)*math.cos(p1),
                         math.cos(dist/R) - math.sin(p1)*math.sin(p2))
    return math.degrees(p2), math.degrees(l2)

def cumulative_distances(pts):
    out = [0.0]
    for i in range(1, len(pts)):
        out.append(out[-1] + haversine(pts[i-1][0], pts[i-1][1],
                                       pts[i][0], pts[i][1]))
    return out

def interpolate_along(pts, dists):
    cum = cumulative_distances(pts); out = []
    for d in dists:
        d = max(0.0, min(d, cum[-1]))
        i = next((k for k in range(len(cum)) if cum[k] >= d), len(cum) - 1)
        if i == 0:
            out.append(pts[0]); continue
        seg = cum[i] - cum[i-1] or 1e-9
        f = (d - cum[i-1]) / seg
        out.append([pts[i-1][0] + f*(pts[i][0]-pts[i-1][0]),
                    pts[i-1][1] + f*(pts[i][1]-pts[i-1][1])])
    return out

def _project(lat0, lon0, lat, lon):
    x = math.radians(lon - lon0) * R * math.cos(math.radians(lat0))
    y = math.radians(lat - lat0) * R
    return x, y

def point_polyline_distance(lat, lon, pts):
    """-> (distance_m, chainage_m, nearest_vertex_index). Exact."""
    if not pts:
        return (1e18, 0.0, 0)
    if len(pts) == 1:
        return (haversine(lat, lon, pts[0][0], pts[0][1]), 0.0, 0)
    cum = cumulative_distances(pts)
    best_d2, best_ch, best_v = 1e18, 0.0, 0
    for i in range(len(pts) - 1):
        ax, ay = _project(lat, lon, pts[i][0], pts[i][1])
        bx, by = _project(lat, lon, pts[i+1][0], pts[i+1][1])
        dx, dy = bx - ax, by - ay
        L2 = dx*dx + dy*dy
        t = 0.0 if L2 == 0 else max(0.0, min(1.0, (-ax*dx - ay*dy) / L2))
        px, py = ax + t*dx, ay + t*dy
        d2 = px*px + py*py
        if d2 < best_d2:
            best_d2 = d2
            best_ch = cum[i] + t * math.sqrt(L2)
            best_v = i if t < 0.5 else i + 1
    return (math.sqrt(best_d2), best_ch, best_v)

def corridor_contains(lat, lon, pts, cum, halfwidths):
    d, ch, _ = point_polyline_distance(lat, lon, pts)
    hw = float(np.interp(ch, cum, halfwidths))
    return d <= hw

def corridor_area_grid(pts, halfwidths, cells_per_axis=200):
    """Authoritative area by grid sampling of corridor_contains."""
    if len(pts) < 2:
        return 0.0
    wmax = max(halfwidths) + 30.0
    lats = [p[0] for p in pts]; lons = [p[1] for p in pts]
    minlat = min(lats) - wmax/111000; maxlat = max(lats) + wmax/111000
    midlat = (min(lats) + max(lats)) / 2
    kx = 111000 * math.cos(math.radians(midlat))
    minlon = min(lons) - wmax/kx; maxlon = max(lons) + wmax/kx
    dlat = (maxlat - minlat) / cells_per_axis
    dlon = (maxlon - minlon) / cells_per_axis
    cum = cumulative_distances(pts)
    cell_area = dlat * 111000 * dlon * kx
    n = 0
    for i in range(cells_per_axis):
        la = minlat + (i + 0.5) * dlat
        for j in range(cells_per_axis):
            lo = minlon + (j + 0.5) * dlon
            if corridor_contains(la, lo, pts, cum, halfwidths):
                n += 1
    return n * cell_area

def _avg_bearing(b1, b2):
    x = math.sin(math.radians(b1)) + math.sin(math.radians(b2))
    y = math.cos(math.radians(b1)) + math.cos(math.radians(b2))
    return math.degrees(math.atan2(x, y)) % 360

def _nearest_vertex(lat, lon, pts):
    best, bi = 1e18, 0
    for i, p in enumerate(pts):
        d = haversine(lat, lon, p[0], p[1])
        if d < best:
            best, bi = d, i
    return bi

def buffer_polygon(pts, halfwidths, right_halfwidths=None):
    """Display polygon with foldover pruning and shapely topology validation.
    Supports asymmetric left and right bank half-widths for true terrain conformance.
    """
    n = len(pts)
    if n < 2:
        return []
    hw_l = halfwidths
    hw_r = right_halfwidths if right_halfwidths is not None else halfwidths
    left, right = [], []
    for i in range(n):
        if i == 0:
            b = bearing(*pts[0], *pts[1])
        elif i == n - 1:
            b = bearing(*pts[-2], *pts[-1])
        else:
            b = _avg_bearing(bearing(*pts[i-1], *pts[i]),
                             bearing(*pts[i], *pts[i+1]))
        wl = max(8.0, float(hw_l[i]))
        wr = max(8.0, float(hw_r[i]))
        lp = destination(pts[i][0], pts[i][1], b - 90, wl)
        rp = destination(pts[i][0], pts[i][1], b + 90, wr)
        left.append(lp)
        right.append(rp)
    if len(left) < 2 or len(right) < 2:
        return []

    raw_ring = left + right[::-1]
    # Validate and simplify geometry with shapely to eliminate foldovers/self-intersections
    try:
        from shapely.geometry import Polygon
        poly = Polygon(raw_ring)
        if not poly.is_valid:
            poly = poly.buffer(0)
        if poly.geom_type == 'Polygon' and len(poly.exterior.coords) >= 4:
            return [[round(p[0], 5), round(p[1], 5)] for p in poly.exterior.coords]
        elif poly.geom_type == 'MultiPolygon' and len(poly.geoms) > 0:
            largest = max(poly.geoms, key=lambda g: g.area)
            return [[round(p[0], 5), round(p[1], 5)] for p in largest.exterior.coords]
    except Exception:
        pass

    return [[round(p[0], 5), round(p[1], 5)] for p in raw_ring]

def ring_area_m2(ring):
    if not ring:
        return 0.0
    la0 = sum(p[0] for p in ring)/len(ring)
    lo0 = sum(p[1] for p in ring)/len(ring)
    kx = 111320*math.cos(math.radians(la0)); ky = 110540
    x = [(p[1]-lo0)*kx for p in ring]
    y = [(p[0]-la0)*ky for p in ring]
    s = sum(x[i]*y[i+1] - x[i+1]*y[i] for i in range(len(ring)-1))
    return abs(s)/2

def validate_centerline(pts, min_spacing_m=15.0, max_points=300):
    warnings, cleaned = [], []
    for p in pts:
        if len(p) != 2:
            warnings.append("Dropped malformed point.")
            continue
        try:
            la, lo = float(p[0]), float(p[1])
        except (TypeError, ValueError):
            warnings.append("Dropped non-numeric point.")
            continue
        if not (-90 <= la <= 90 and -180 <= lo <= 180):
            warnings.append("Dropped out-of-range coordinate.")
            continue
        if cleaned and haversine(la, lo, cleaned[-1][0], cleaned[-1][1]) \
                < min_spacing_m:
            continue
        cleaned.append([round(la, 6), round(lo, 6)])
    if len(pts) > max_points:
        warnings.append(f"Truncated to first {max_points} points.")
        cleaned = cleaned[:max_points]
    if len(cleaned) < 2:
        warnings.append("Need >= 2 valid, separated points.")
    return cleaned, warnings
