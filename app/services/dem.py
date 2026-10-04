"""Copernicus GLO-30 DEM via public AWS bucket (no credentials).
Tiles 1x1 deg named by SW corner; local cache with 30-day TTL."""
import math, time
from pathlib import Path
import numpy as np
from ..config import cfg

BUCKET = "https://copernicus-dem-30m.s3.amazonaws.com"
CACHE = Path(cfg.DB_PATH).parent / "dem_cache"
CACHE.mkdir(parents=True, exist_ok=True)
CELL_M = 30.0
_TTL = 30 * 86400


def _tile_name(lat, lon):
    la, lo = math.floor(lat), math.floor(lon)
    ns, ew = ("N" if la >= 0 else "S", "E" if lo >= 0 else "W")
    return f"Copernicus_DSM_COG_10_{ns}{abs(la):02d}_00_{ew}{abs(lo):03d}_00_DEM"


def fetch_tile(lat, lon):
    try:
        import rasterio
    except ImportError:
        return None
    name = _tile_name(lat, lon)
    local = CACHE / f"{name}.tif"
    if not local.exists() or time.time() - local.stat().st_mtime > _TTL:
        url = f"{BUCKET}/{name}/{name}.tif"
        try:
            with rasterio.open(f"/vsicurl/{url}") as src:
                profile = src.profile
                data = src.read(1)
            with rasterio.open(local, "w", **profile) as dst:
                dst.write(data, 1)
        except Exception:
            return None
    try:
        return rasterio.open(local)
    except Exception:
        return None


def dem_for_bbox(minlat, minlon, maxlat, maxlon):
    """-> elevation grid [m] for a small bbox, mosaiced from 1-4 tiles.
    Returns None if DEM unavailable (callers degrade gracefully)."""
    try:
        import rasterio
        from rasterio.windows import from_bounds
    except ImportError:
        return None
    tiles = []
    for la in {math.floor(minlat), math.floor(maxlat)}:
        for lo in {math.floor(minlon), math.floor(maxlon)}:
            ds = fetch_tile(la + 0.5, lo + 0.5)
            if ds:
                tiles.append(ds)
    if not tiles:
        return None
    w = max(2, int((maxlon - minlon) * 3600))
    h = max(2, int((maxlat - minlat) * 3600))
    grid = np.full((h, w), np.nan, dtype="float32")
    got = False
    dlon = (maxlon - minlon) / w
    dlat = (maxlat - minlat) / h
    for ds in tiles:
        try:
            win = from_bounds(minlon, minlat, maxlon, maxlat, ds.transform)
            win = win.round_offsets().round_lengths()
            if win.width <= 0 or win.height <= 0:
                continue
            data = ds.read(1, window=win).astype("float32")
            col0 = int((float(ds.transform.c) - minlon) / dlon)
            row0 = int((maxlat - float(ds.transform.f)) / dlat)
            r0, c0 = max(0, -row0), max(0, -col0)
            r1 = min(data.shape[0], h - max(0, row0))
            c1 = min(data.shape[1], w - max(0, col0))
            if r1 > r0 and c1 > c0:
                sub = data[r0:r1, c0:c1]
                gr, gc = max(0, row0), max(0, col0)
                m = np.isnan(grid[gr:gr+sub.shape[0], gc:gc+sub.shape[1]])
                grid[gr:gr+sub.shape[0], gc:gc+sub.shape[1]][m] = sub[m]
                got = True
        except Exception:
            continue
    if not got:
        return None
    grid[grid < -1000] = np.nan
    return grid
