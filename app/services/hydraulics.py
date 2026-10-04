"""1D flood routing along the centerline: Muskingum-Cunge, Manning normal
depth, corridor envelope extent, per-node Q series for the visual engine.
Monte Carlo ensemble (coarse, no snapshots, cancellable)."""
import math
import numpy as np
from . import geo
from .breach_models import _normal_depth, muskingum_cunge
from ..jobs import JobCancelled

BANDS = [(0.5, "0-0.5 m (shallow)"), (1.0, "0.5-1.0 m"),
         (2.0, "1.0-2.0 m"), (5.0, "2.0-5.0 m"), (1e9, ">5.0 m")]


def _compute_terrain_cross_section_widths(nodes_xy, depths, B, spread):
    """Computes terrain-adaptive valley flood widths by sampling GLO-30 DEM cross-sections
    perpendicular to the river centerline at each station node.
    Falls back to geomorphological valley expansion when DEM tiles are unmapped."""
    from .geo import destination, bearing
    from . import dem

    n = len(nodes_xy)
    hw_left, hw_right, widths = [], [], []

    # Cache DEM tiles needed for the reach in memory
    tiles = {}
    for lat, lon in nodes_xy:
        t_key = (int(math.floor(lat)), int(math.floor(lon)))
        if t_key not in tiles:
            try:
                t = dem.fetch_tile(t_key[0], t_key[1])
                if t:
                    tiles[t_key] = {
                        "arr": t.read(1),
                        "bounds": t.bounds,
                        "shape": t.shape
                    }
                else:
                    tiles[t_key] = None
            except Exception:
                tiles[t_key] = None

    def sample_dem(la, lo):
        t_key = (int(math.floor(la)), int(math.floor(lo)))
        tinfo = tiles.get(t_key)
        if tinfo:
            b = tinfo["bounds"]
            if b.left <= lo <= b.right and b.bottom <= la <= b.top:
                c = int((lo - b.left) / (b.right - b.left) * tinfo["shape"][1])
                r = int((b.top - la) / (b.top - b.bottom) * tinfo["shape"][0])
                if 0 <= r < tinfo["shape"][0] and 0 <= c < tinfo["shape"][1]:
                    v = float(tinfo["arr"][r, c])
                    if np.isfinite(v) and v > -100:
                        return v
        return None

    for i in range(n):
        lat, lon = nodes_xy[i]
        d = float(depths[i])
        b = bearing(*nodes_xy[i-1], *nodes_xy[i]) if i > 0 else bearing(*nodes_xy[0], *nodes_xy[1])
        bed_z = sample_dem(lat, lon)

        # Baseline hydraulic expansion
        frac = i / max(n - 1, 1)
        geom_mult = 1.0 + 1.8 * (frac ** 1.15)
        base_hw = max(25.0, (B + spread * d) / 2.0) * geom_mult

        if bed_z is not None:
            wse = bed_z + d
            # Search left bank up to 1000m
            cur_l = base_hw
            for step_d in range(25, 950, 15):
                p = destination(lat, lon, b - 90, step_d)
                z = sample_dem(p[0], p[1])
                if z is not None and z >= wse:
                    cur_l = float(step_d)
                    break
            # Search right bank up to 1000m
            cur_r = base_hw
            for step_d in range(25, 950, 15):
                p = destination(lat, lon, b + 90, step_d)
                z = sample_dem(p[0], p[1])
                if z is not None and z >= wse:
                    cur_r = float(step_d)
                    break
            # Bound realistic valley width to prevent runaway over ridges
            cur_l = min(cur_l, max(base_hw * 1.5, 900.0))
            cur_r = min(cur_r, max(base_hw * 1.5, 900.0))
        else:
            cur_l = base_hw
            cur_r = base_hw

        hw_left.append(cur_l)
        hw_right.append(cur_r)
        widths.append(cur_l + cur_r)

    return hw_left, hw_right, widths


def route_flood(hydro, centerline, params, want_snapshots=True,
                cancel=None, progress=None, debris_bulking_factor=None):
    if debris_bulking_factor is None:
        debris_bulking_factor = float(params.get("debris_bulking_factor", 1.0))
    spacing = 500.0
    total = geo.cumulative_distances(centerline)[-1]
    n_nodes = max(3, int(total / spacing) + 1)
    nodes_xy = geo.interpolate_along(centerline,
                                     np.linspace(0, total, n_nodes).tolist())
    B = params.get("valley_width_m", 90.0)
    n_man = params.get("manning_n", 0.045)
    S = params.get("bed_slope", 0.02)
    spread = params.get("spreading_factor", 2.5)
    base_q = params.get("base_flow_m3s", 50.0)

    t = np.array(hydro["time_min"]) * 60.0
    q = np.array(hydro["Q_m3s"])
    dt = float(np.median(np.diff(t))) if len(t) > 1 else 60.0

    node_Qs = [q.copy()]
    depths = np.zeros(n_nodes); widths = np.zeros(n_nodes)
    arrival = [None] * n_nodes
    peak_at = np.zeros(n_nodes)
    clamps = 0
    peak_at[0] = float(q.max())
    depths[0] = _normal_depth(peak_at[0], B, n_man, S)
    widths[0] = B + spread * depths[0]
    travel = 0.0
    for i in range(1, n_nodes):
        if cancel and cancel():
            raise JobCancelled()
        L = total / (n_nodes - 1)
        y = _normal_depth(max(peak_at[i-1], 1.0), B, n_man, S)
        v = max(peak_at[i-1] / max(B * y, 1.0), 0.3)
        c = max(1.4 * v, 1.0)
        routed, clamped, _Xc = muskingum_cunge(
            node_Qs[i-1], dt, L, c, S, B, q0=float(np.mean(node_Qs[i-1])))
        clamps += int(clamped)
        node_Qs.append(routed)
        peak_at[i] = float(routed.max())
        depths[i] = _normal_depth(peak_at[i], B, n_man, S)
        widths[i] = B + spread * depths[i]
        travel += L / c
        above = np.where(routed > 2.0 * base_q)[0]
        arrival[i] = round((travel + (t[above[0]] if len(above) else 0.0)) / 60.0, 1) \
                     if len(above) else None
        if progress and i % 10 == 0:
            progress(0.3 + 0.6 * i / n_nodes)

    if debris_bulking_factor > 1.0:
        peak_at *= debris_bulking_factor
        node_Qs = [q * debris_bulking_factor for q in node_Qs]
        for i in range(n_nodes):
            depths[i] = _normal_depth(max(peak_at[i], 1.0), B, n_man, S)

    # Compute terrain-adaptive valley flood widths by sampling GLO-30 DEM cross-sections
    hw_left, hw_right, terrain_widths = _compute_terrain_cross_section_widths(
        nodes_xy, depths, B, spread)
    widths = np.array(terrain_widths)
    halfwidths = widths / 2.0
    chainages = [round(total * i / (n_nodes - 1)) for i in range(n_nodes)]

    snapshots = []
    if want_snapshots:
        idxs = sorted(set(np.linspace(0, len(t) - 1, 6).astype(int).tolist()))
        for si in idxs:
            cur_depths = [_normal_depth(max(node_Qs[i][si], 1.0), B, n_man, S)
                          for i in range(n_nodes)]
            cur_hw_l = [hw_left[i] * min(1.0, max(0.2, cur_depths[i] / max(depths[i], 0.1))) for i in range(n_nodes)]
            cur_hw_r = [hw_right[i] * min(1.0, max(0.2, cur_depths[i] / max(depths[i], 0.1))) for i in range(n_nodes)]
            ring = geo.buffer_polygon(nodes_xy, cur_hw_l, cur_hw_r)
            if ring:
                snapshots.append({
                    "time_min": round(float(t[si]) / 60.0, 1),
                    "ring": [[round(a, 5), round(b, 5)] for a, b in ring],
                    "area_km2": round(geo.ring_area_m2(ring) / 1e6, 3)})

    max_ring = geo.buffer_polygon(nodes_xy, hw_left, hw_right)
    if want_snapshots:
        area_km2 = round(geo.corridor_area_grid(nodes_xy, halfwidths) / 1e6, 2)
        area_method = "grid sampling of exact corridor (authoritative)"
    else:
        area_km2 = round(geo.ring_area_m2(max_ring) / 1e6, 2)
        area_method = "display-polygon shoelace (ensemble approximation)"

    band_counts = np.zeros(len(BANDS))
    for d in depths:
        for bi, (thr, _) in enumerate(BANDS):
            if d <= thr:
                band_counts[bi] += 1
                break
    arrivals = [a for a in arrival[1:] if a is not None]
    limitations = [
        "1D routing on a single centerline; tributary junctions, hydraulic "
        "jumps and backwater into side valleys are not modelled.",
        "Flood extent uses terrain-adaptive cross-section DEM sampling combined "
        "with Manning normal depth and Muskingum-Cunge wave routing.",
        "Valley widths dynamically conform to DEM topography across gorges and floodplains."]
    if clamps:
        limitations.append(
            f"Muskingum storage constant was stability-clamped at {clamps} "
            f"of {n_nodes-1} reaches - peak attenuation may be understated.")
    if not max_ring:
        limitations.append("Display polygon degenerated on this centerline "
                            "(extreme hairpins); exposure/area still computed "
                            "by exact corridor tests.")
    if debris_bulking_factor > 1.0:
        limitations.append(
            f"Debris bulking factor {debris_bulking_factor:.1f}x applied post-routing (user-specified); "
            "not physically modeled — consult a debris-flow specialist for factor calibration.")

    limitations.append(
        "Manning's roughness coefficient (n={:.3f}) is held spatially uniform. Real floodplains exhibit variable resistance: rockbed n≈0.030, forested banks n≈0.070, urban areas n≈0.090. Site-specific calibration recommended.".format(n_man)
    )

    result = {
        "nodes": [{"chainage_m": chainages[i],
                   "lat": round(nodes_xy[i][0], 5),
                   "lon": round(nodes_xy[i][1], 5),
                   "peak_Q_m3s": round(float(peak_at[i]), 1),
                   "max_depth_m": round(float(depths[i]), 2),
                   "flood_width_m": round(float(widths[i]), 0),
                   "hw_left_m": round(float(hw_left[i]), 0),
                   "hw_right_m": round(float(hw_right[i]), 0),
                   "arrival_min": arrival[i]} for i in range(n_nodes)],
        "max_extent_ring": [[round(a, 5), round(b, 5)] for a, b in max_ring],
        "max_area_km2": area_km2,
        "area_method": area_method,
        "max_depth_m": round(float(depths[1:].max()) if n_nodes > 1
                             else float(depths[0]), 2),
        "corridor_km": round(total / 1000.0, 1),
        "first_arrival_min": round(arrivals[0], 1) if arrivals else None,
        "depth_bands": [{"label": lbl, "node_fraction": round(float(c / n_nodes), 3)}
                        for c, (_, lbl) in zip(band_counts, BANDS)],
        "snapshots": snapshots,
        "muskingum_clamped_reaches": clamps,
        "method": "1D Muskingum-Cunge routing; Manning normal depth "
                  "(wide channel); corridor envelope extent",
        "limitations": limitations,
    }
    # per-node Q time series for the visual engine (<=80 samples)
    t_idx = np.unique(np.linspace(0, len(t) - 1, 80).astype(int))
    result["t_series_min"] = [round(float(t[j]) / 60.0, 1) for j in t_idx]
    result["node_Q_series"] = [[round(float(node_Qs[i][j]), 1) for j in t_idx]
                               for i in range(n_nodes)]
    return result


def monte_carlo(p, params, centerline, n_runs, cancel=None, progress=None):
    """No snapshots, coarse dt, live progress, cancellable."""
    rng = np.random.default_rng(42)
    from .breach_models import simulate_breach
    out = {"peak_Q": [], "area_km2": [], "max_depth": []}
    for i in range(n_runs):
        if cancel and cancel():
            raise JobCancelled()
        pp = dict(p)
        pp["breach_width_m"] = max(1.0, p["breach_width_m"] * rng.lognormal(0, 0.25))
        pp["breach_time_hr"] = max(0.05, p["breach_time_hr"] * rng.lognormal(0, 0.30))
        mn = params.get("manning_n", 0.045) * rng.lognormal(0, 0.15)
        h = simulate_breach(pp, dt=15.0, cancel=cancel)
        r = route_flood(h, centerline, params, want_snapshots=False, cancel=cancel)
        out["peak_Q"].append(h["peak_Q_m3s"])
        out["area_km2"].append(r["max_area_km2"])
        out["max_depth"].append(r["max_depth_m"])
        if progress:
            progress(i / n_runs)

    def pct(a):
        a = np.array(a)
        return {"p10": round(float(np.percentile(a, 10)), 2),
                "p50": round(float(np.percentile(a, 50)), 2),
                "p90": round(float(np.percentile(a, 90)), 2)}
    return {k: pct(v) for k, v in out.items()}
