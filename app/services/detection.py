"""Automated temporary-lake detection.

CRITICAL DESIGN: all masks are CROPPED TO THE ZONE GRID immediately after
decode, using each raster's geotransform. Every downstream index maps
through the grid, so candidate lat/lon is EXACT (no full-scene leakage).

Pipeline: scene search (SAR preferred) -> zone-cropped water mask ->
baseline frequency -> classify with ROI + river-exclusion -> components ->
morphology rejection -> GLO-30 geometry -> scoring -> upsert + observation.
Void scenes (<15% valid pixels) leave candidates UNCHANGED.
"""
import asyncio, json, logging, math
from datetime import datetime, timedelta, timezone
import numpy as np
from ..db import (SessionLocal, MonitoringZone, LakeCandidate,
                  LakeObservation, new_id, utcnow)
from . import water, baseline as bl, roi as _roi, growth as _growth
from . import satellite
from .dem import dem_for_bbox
from .lake_geometry import lake_geometry_from_bbox

logger = logging.getLogger(__name__)

S1_COLLECTION = "SENTINEL1-GRD"
MIN_AREA_M2 = 5000.0
RIVER_ADJ_REJECT = 0.90      # buffer is the primary filter now
COMPACT_MIN = 0.08


# ---------------------------------------------------------- zone grid -------
class _Grid:
    """Zone analysis grid. Row 0 = maxlat; pixel centres; exact geo."""
    def __init__(self, minlat, minlon, maxlat, maxlon, res_m):
        self.minlat, self.minlon = minlat, minlon
        self.maxlat, self.maxlon = maxlat, maxlon
        self.lat_res = res_m / 110540.0
        self.lon_res = res_m / (111320.0 *
                                np.cos(np.radians((minlat + maxlat) / 2)))
        self.h = max(4, int((maxlat - minlat) / self.lat_res))
        self.w = max(4, int((maxlon - minlon) / self.lon_res))
    def lat(self, row): return self.maxlat - (np.asarray(row) + 0.5) * self.lat_res
    def lon(self, col): return self.minlon + (np.asarray(col) + 0.5) * self.lon_res
    def shape(self): return (self.h, self.w)


def zone_bbox(zone):
    return (min(zone.lat1, zone.lat2), min(zone.lon1, zone.lon2),
            max(zone.lat1, zone.lat2), max(zone.lon1, zone.lon2))


def crop_to_grid(arr, transform, grid):
    """Crop decoded raster (array + geotransform) to zone grid, exact."""
    h, w = grid.shape()
    out = np.zeros((h, w), dtype=arr.dtype)
    inv = ~transform
    rows = np.arange(h); cols = np.arange(w)
    LA = np.asarray(grid.lat(rows))[:, None] * np.ones((1, w))
    LO = np.ones((h, 1)) * np.asarray(grid.lon(cols))[None, :]
    XS, YS = inv @ (LO, LA)
    ri = np.floor(YS - 0.5).astype(int)
    ci = np.floor(XS - 0.5).astype(int)
    valid = ((ri >= 0) & (ri < arr.shape[0]) &
             (ci >= 0) & (ci < arr.shape[1]))
    out[valid] = arr[ri[valid], ci[valid]]
    return out


_crop_to_grid = crop_to_grid


# ---------------------------------------------------------- scene search -----
async def latest_scene(lat, lon, days=30, prefer_sar=True):
    try:
        now = datetime.now(timezone.utc)
        end = now.strftime("%Y-%m-%dT23:59:59Z")
        start = (now - timedelta(days=days)).strftime("%Y-%m-%dT00:00:00Z")
        if prefer_sar:
            token = await satellite._cdse_token()
            if token:
                s = await _search_s1(lat, lon, start, end, token)
                if s:
                    return s
        opt = await satellite.search_scenes(lat, lon, start, end,
                                            source="usgs_landsat",
                                            cloud_max=40, limit=1)
        if opt.get("ok") and opt.get("items"):
            return opt["items"][0]
    except Exception as e:
        logger.warning(f"latest_scene lookup error: {e}")
    return None


async def _search_s1(lat, lon, start, end, token):
    import httpx
    dt_start = str(start) if "T" in str(start) else f"{start}T00:00:00Z"
    dt_end = str(end) if "T" in str(end) else f"{end}T23:59:59Z"
    body = {"collections": [S1_COLLECTION],
            "bbox": [lon - 0.15, lat - 0.15, lon + 0.15, lat + 0.15],
            "datetime": f"{dt_start}/{dt_end}", "limit": 1}
    try:
        async with httpx.AsyncClient(timeout=30) as cl:
            r = await cl.post(satellite.CDSE_STAC, json=body,
                              headers={"Authorization": f"Bearer {token}"})
            r.raise_for_status()
            feats = r.json().get("features", [])
    except Exception as e:
        logger.warning(f"S1 STAC search failed: {e}")
        return None
    if not feats:
        return None
    it = feats[0]
    vv = satellite._asset_href(it.get("assets", {}).get("vv"))
    if not vv:
        return None
    return {"scene_id": it["id"], "datetime": it["properties"].get("datetime"),
            "source": "Sentinel-1 GRD", "platform": "Sentinel-1",
            "assets": {"vv": vv}, "thumbnail": None, "cloud_pct": None}


# ---------------------------------------------------------- water mask -------
async def current_water_mask(scene, zone):
    """Fetch bands, CROP TO ZONE GRID, extract water. Exact georeferencing."""
    bbox = zone_bbox(zone)
    if scene["source"].startswith("Sentinel-1"):
        raw = await satellite.fetch_band_bytes(scene["assets"]["vv"])
        if raw is None:
            return None, "SAR download failed"
        try:
            import io as _io, rasterio
            with rasterio.open(_io.BytesIO(raw)) as src:
                arr = src.read(1); transform = src.transform
        except Exception:
            return None, "SAR decode failed (rasterio required)"
        grid = _Grid(*bbox, 10.0)
        dn = _crop_to_grid(arr.astype("float32"), transform, grid)
        with np.errstate(divide="ignore", invalid="ignore"):
            sigma_db = 10.0 * np.log10(np.maximum(dn, 1e-6) ** 2) - 83.0
        thr = water.get_sar_threshold(getattr(zone, "id", None))
        m = water.sar_water(sigma_db, threshold_db=thr)
        return {"water": m, "valid": np.ones_like(m, bool), "grid": grid,
                "res_m": 10.0, "scene": scene}, None
    # optical: 3 bands
    try:
        import io as _io, rasterio
    except ImportError:
        return None, "rasterio required for optical band decoding"
    bands = await asyncio.gather(*[
        satellite.fetch_band_bytes(scene["assets"][b])
        for b in ("green", "nir", "swir")], return_exceptions=True)
    if any(isinstance(b, Exception) or b is None for b in bands):
        return None, "optical band download failed"
    decoded = []
    for raw in bands:
        try:
            with rasterio.open(_io.BytesIO(raw)) as src:
                decoded.append((src.read(1), src.transform))
        except Exception:
            return None, "optical decode failed"
    res = 30.0 if "landsat" in scene["source"].lower() else 10.0
    grid = _Grid(*bbox, res)
    arrs = [_crop_to_grid(a, t, grid) for a, t in decoded]
    wm, valid = water.optical_water(arrs[0], arrs[1], arrs[2], scene["source"])
    if float(valid.mean()) < 0.15:
        return None, (f"scene void: only {float(valid.mean()):.0%} valid "
                      "pixels (clouds/void) - candidate status NOT changed")
    return {"water": wm, "valid": valid, "grid": grid, "res_m": res,
            "scene": scene}, None


def resample_like(mask, target_shape):
    if mask.shape == tuple(target_shape):
        return mask
    h, w = target_shape
    ys = (np.arange(h) + 0.5) * (mask.shape[0] / h)
    xs = (np.arange(w) + 0.5) * (mask.shape[1] / w)
    return mask[ys.astype(int)][:, xs.astype(int)]


# ---------------------------------------------------------- components -------
def connected_components(mask):
    h, w = mask.shape
    lab = np.zeros((h, w), dtype="int32")
    comps = []
    nxt = 0
    for r, c in zip(*np.where(mask)):
        if lab[r, c]:
            continue
        nxt += 1
        stack = [(r, c)]
        lab[r, c] = nxt
        pix = []
        while stack:
            y, x = stack.pop()
            pix.append((y, x))
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = y + dy, x + dx
                if (0 <= ny < h and 0 <= nx < w and mask[ny, nx]
                        and not lab[ny, nx]):
                    lab[ny, nx] = nxt
                    stack.append((ny, nx))
        comps.append((nxt, pix))
    return lab, comps


def compactness(area_px, peri_px):
    return 4 * math.pi * area_px / max(peri_px * peri_px, 1.0)


def component_perimeter(pix, shape):
    s = set(pix)
    h, w = shape
    peri = 0
    for y, x in pix:
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if not (0 <= ny < h and 0 <= nx < w) or (ny, nx) not in s:
                peri += 1
    return peri


def boundary_river_fraction(pix, persistent):
    s = set(pix)
    h, w = persistent.shape
    touch, total = 0, 0
    for y, x in pix:
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1),
                       (1, 1), (1, -1), (-1, 1), (-1, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and (ny, nx) not in s:
                total += 1
                if persistent[ny, nx]:
                    touch += 1
    return (touch / total) if total else 0.0


# ---------------------------------------------------------- main scan --------
async def scan_zone(zone_id):
    db = SessionLocal()
    try:
        zone = db.get(MonitoringZone, zone_id)
        if not zone:
            return {"ok": False, "error": "zone not found"}
        minlat, minlon, maxlat, maxlon = zone_bbox(zone)
        scene = await latest_scene((minlat + maxlat) / 2,
                                   (minlon + maxlon) / 2,
                                   days=zone.lookback_days)
        if not scene:
            return {"ok": False, "error": "no usable scene in lookback window"}
        cur, err = await current_water_mask(scene, zone)
        if err:
            # void scene: candidates UNCHANGED
            return {"ok": False, "error": err, "scene": scene["scene_id"],
                    "candidates_unchanged": True}
        grid = cur["grid"]

        b = bl.load_baseline(zone.id)
        if bl.is_stale(b) or tuple(b["freq"].shape) != grid.shape():
            built = await build_baseline(zone)
            if not built.get("ok"):
                return {"ok": False, "error": "baseline build failed: " +
                        built.get("error", ""), "scene": scene["scene_id"]}
            b = bl.load_baseline(zone.id)

        cur_w = resample_like(cur["water"], b["freq"].shape)

        # ROI + river exclusion (variables in scope - always defined above)
        roi_mask = None
        if zone.roi_polygon:
            try:
                poly = json.loads(zone.roi_polygon)
                roi_mask = _roi.rasterize_polygon(
                    poly, b["freq"].shape,
                    (minlat, minlon, maxlat, maxlon))
            except Exception:
                roi_mask = None
        persistent_water = b["freq"] >= 0.50
        excl_mask, buf_px = _roi.river_exclusion(
            persistent_water, cur["res_m"], zone.river_buffer_m or 300.0)
        cls = _roi.classify_with_exclusion(b["freq"], cur_w,
                                           roi_mask=roi_mask,
                                           exclusion_mask=excl_mask)
        new_water = cls == 3
        persistent = cls == 1
        coverage = _roi.coverage_stats(cls, roi_mask)

        if not new_water.any():
            _close_resolved(db, zone.id)
            zone.last_scan_at = utcnow()
            db.commit()
            return {"ok": True, "scene": scene["scene_id"],
                    "candidates": 0, "coverage": coverage,
                    "river_buffer_px": buf_px,
                    "note": "no new water detected (after ROI/exclusion masking)"}

        _, comps = connected_components(new_water)
        px_area = cur["res_m"] ** 2
        H, W = new_water.shape
        candidates = []
        for _, pix in comps:
            area_m2 = len(pix) * px_area
            if area_m2 < MIN_AREA_M2:
                continue
            ys = [p[0] for p in pix]; xs = [p[1] for p in pix]
            peri = component_perimeter(pix, new_water.shape)
            comp = compactness(len(pix), peri)
            river_frac = boundary_river_fraction(pix, persistent)
            if river_frac >= RIVER_ADJ_REJECT:
                continue
            if comp < COMPACT_MIN and river_frac > 0.5:
                continue
            # EXACT georeferencing via the baseline grid + zone bbox
            lat_lo = maxlat - (max(ys) + 1) * (maxlat - minlat) / H
            lat_hi = maxlat - min(ys) * (maxlat - minlat) / H
            lon_lo = minlon + min(xs) * (maxlon - minlon) / W
            lon_hi = minlon + (max(xs) + 1) * (maxlon - minlon) / W
            candidates.append({
                "lat": round((lat_lo + lat_hi) / 2, 6),
                "lon": round((lon_lo + lon_hi) / 2, 6),
                "bbox": [round(lon_lo, 5), round(lat_lo, 5),
                         round(lon_hi, 5), round(lat_hi, 5)],
                "area_m2": round(area_m2, 0),
                "compactness": round(comp, 3),
                "river_adjacency": round(river_frac, 3)})

        results = []
        for c in candidates:
            c["score"] = _score(c, scene)
            geom = await lake_geometry_from_bbox(c["bbox"], c["area_m2"])
            c.update(geom or {})
            results.append(c)
            row = _upsert_candidate(db, zone, scene, c)
            db.commit()
            target_id = row.id if row else _find_candidate_id(db, zone.id, c)
            if target_id:
                _growth.record_observation(
                    db, target_id, scene["scene_id"], c["area_m2"],
                    wse_m=c.get("wse_m"), volume_m3=c.get("volume_m3"))
                g = _growth.analyze_growth(target_id, db=db)
                c["alert"] = g.get("alert", {})

        zone.last_scan_at = utcnow()
        db.commit()
        return {"ok": True, "scene": scene["scene_id"], "source": scene["source"],
                "candidates": results, "coverage": coverage,
                "river_buffer_px": buf_px}
    except Exception as e:
        logger.error(f"Error scanning zone {zone_id}: {e}", exc_info=True)
        return {"ok": False, "error": f"Scan error: {e}", "candidates": []}
    finally:
        db.close()


def _score(c, scene):
    s = 40.0
    s += min(25.0, 25.0 * math.log10(max(c["area_m2"], 1) / MIN_AREA_M2) / 2)
    s += 15.0 * (1.0 - min(c["river_adjacency"], 1.0))
    s += 10.0 * min(c["compactness"] / 0.6, 1.0)
    if scene["source"].startswith("Sentinel-1"):
        s += 10.0
    return round(min(s, 100.0), 1)


def _upsert_candidate(db, zone, scene, c):
    existing = db.query(LakeCandidate).filter(
        LakeCandidate.zone_id == zone.id,
        LakeCandidate.status.in_(("DETECTED", "VERIFIED"))).all()
    for e in existing:
        if abs(e.lat - c["lat"]) < 0.005 and abs(e.lon - c["lon"]) < 0.005:
            e.area_m2 = c["area_m2"]
            e.depth_m = c.get("depth_m"); e.volume_m3 = c.get("volume_m3")
            e.wse_m = c.get("wse_m"); e.score = c["score"]
            e.last_seen_scene = scene["scene_id"]; e.last_seen_at = utcnow()
            return e
    db.add(LakeCandidate(
        id=new_id("LK"), zone_id=zone.id, lat=c["lat"], lon=c["lon"],
        bbox=json.dumps(c["bbox"]), area_m2=c["area_m2"],
        depth_m=c.get("depth_m"), volume_m3=c.get("volume_m3"),
        wse_m=c.get("wse_m"), score=c["score"],
        compactness=c["compactness"], river_adjacency=c["river_adjacency"],
        status="DETECTED", first_seen_scene=scene["scene_id"],
        last_seen_scene=scene["scene_id"]))
    return None


def _find_candidate_id(db, zone_id, c):
    e = db.query(LakeCandidate).filter(
        LakeCandidate.zone_id == zone_id,
        LakeCandidate.status.in_(("DETECTED", "VERIFIED")),
        abs(LakeCandidate.lat - c["lat"]) < 0.005,
        abs(LakeCandidate.lon - c["lon"]) < 0.005).first()
    return e.id if e else None


def _close_resolved(db, zone_id):
    for c in db.query(LakeCandidate).filter(
            LakeCandidate.zone_id == zone_id,
            LakeCandidate.status == "DETECTED").all():
        c.status = "RESOLVED"


async def build_baseline(zone):
    """Historical water-frequency baseline (optical Landsat, cached)."""
    bbox = zone_bbox(zone)
    lat, lon = (bbox[2] + bbox[0]) / 2, (bbox[3] + bbox[1]) / 2
    now = datetime.now(timezone.utc)
    scenes = []
    for ydelta in (1, 2):
        start = (now - timedelta(days=365 * ydelta)).date().isoformat()
        end = (datetime.fromisoformat(start).date() +
               timedelta(days=90)).isoformat()
        j = await satellite.search_scenes(lat, lon, start, end,
                                          source="usgs_landsat",
                                          cloud_max=30, limit=6)
        if j.get("ok"):
            scenes += j["items"]
    scenes = scenes[:bl.MAX_SCENES]
    if len(scenes) < bl.MIN_SCENES:
        return {"ok": False, "error":
                f"only {len(scenes)} historical scenes "
                f"(need {bl.MIN_SCENES})"}
    masks, res, shape = [], None, None
    for s in scenes:
        cur, err = await current_water_mask(s, zone)
        if err or cur is None:
            continue
        masks.append(cur["water"]); res = cur["res_m"]
        shape = shape or cur["grid"].shape()
    if len(masks) < bl.MIN_SCENES:
        return {"ok": False, "error": "too few decodable historical scenes"}
    shape = shape or masks[0].shape
    masks = [resample_like(m, shape) for m in masks]
    stack = np.stack(masks)
    freq = stack.mean(axis=0).astype("float32")
    valid = (stack.sum(axis=0) >= len(masks) / 2).astype("uint8")
    bl.save_baseline(zone.id, freq, valid, len(masks),
                     [bbox[0], bbox[1], bbox[2], bbox[3]],
                     [s["scene_id"] for s in scenes[:len(masks)]], shape)
    return {"ok": True, "n_scenes": len(masks),
            "note": "Baseline built from OPTICAL scenes while current scans "
                    "prefer SAR - persistent cloud areas may inflate new-"
                    "water detections (documented limitation)."}
