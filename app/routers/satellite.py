from fastapi import APIRouter, Depends, HTTPException
from datetime import date
from sqlalchemy.orm import Session
from ..db import SessionLocal, Incident
from ..security import require_role
from ..services import satellite

router = APIRouter(prefix="/api/satellite", tags=["satellite"])

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

@router.get("/search")
async def search(incident_id: str, start: date, end: date,
                 source: str = "usgs_landsat", cloud_max: int = 30,
                 db: Session = Depends(get_db),
                 user=Depends(require_role("viewer"))):
    inc = db.get(Incident, incident_id)
    if not inc:
        raise HTTPException(404, "Incident not found")
    if source not in ("usgs_landsat", "copernicus_s2"):
        raise HTTPException(400, "source must be usgs_landsat or copernicus_s2")
    return await satellite.search_scenes(
        inc.lat, inc.lon, start.isoformat(), end.isoformat(),
        source=source, cloud_max=cloud_max)

@router.post("/analyze")
async def analyze(scene: dict, user=Depends(require_role("analyst"))):
    if not scene.get("assets") or not scene["assets"].get("green"):
        raise HTTPException(400, "Scene has no downloadable assets")
    import numpy as np
    from ..services import water
    try:
        import io as _io, rasterio
        import asyncio
        bands = await asyncio.gather(*[
            satellite.fetch_band_bytes(scene["assets"][b])
            for b in ("green", "nir", "swir")], return_exceptions=True)
    except Exception as e:
        return {"ok": False, "error": str(e)}
    if any(isinstance(b, Exception) or b is None for b in bands):
        return {"ok": False, "error": "band download failed"}
    arrs = []
    for raw in bands:
        a = satellite.decode(raw)
        if a is None:
            return {"ok": False, "error": "decode failed (install rasterio)"}
        arrs.append(a)
    h = min(a.shape[0] for a in arrs); w = min(a.shape[1] for a in arrs)
    arrs = [a[:h, :w] for a in arrs]
    wm, valid = water.optical_water(arrs[0], arrs[1], arrs[2], scene["source"])
    res = 30.0 if "landsat" in scene["source"].lower() else 10.0
    return {"ok": True, "scene_id": scene["scene_id"],
            "datetime": scene["datetime"], "source": scene["source"],
            "water_area_m2": round(int(wm.sum()) * res * res, 0),
            "water_area_km2": round(int(wm.sum()) * res * res / 1e6, 4),
            "valid_pixel_fraction": round(float(valid.mean()), 3),
            "note": "Whole-tile water area - supply an ROI/zone for "
                    "lake-specific areas (see detection endpoints)."}

@router.post("/change")
async def change(before: dict, after: dict,
                 user=Depends(require_role("viewer"))):
    if not (before.get("ok") and after.get("ok")):
        return {"ok": False, "error": "Both scenes must be analyzed first."}
    d = after["water_area_m2"] - before["water_area_m2"]
    ratio = (after["water_area_m2"] / before["water_area_m2"]
             if before["water_area_m2"] else None)
    return {"ok": True,
            "before": {"date": before.get("datetime"),
                       "area_km2": before.get("water_area_km2")},
            "after": {"date": after.get("datetime"),
                      "area_km2": after.get("water_area_km2")},
            "delta_m2": round(d, 0), "delta_km2": round(d / 1e6, 4),
            "expansion_ratio": round(ratio, 2) if ratio else None,
            "interpretation": ("EXPANSION - potential impoundment growth"
                               if d > 0 else "REDUCTION / breach drainage")}
