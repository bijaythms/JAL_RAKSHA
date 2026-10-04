import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..db import (SessionLocal, MonitoringZone, LakeCandidate, Incident,
                   new_id)
from ..schemas import ZoneIn, RoiIn, BufferIn, VerifyIn
from ..security import require_role, audit
from ..services import detection, roi, growth, water

router = APIRouter(prefix="/api/detection", tags=["detection"])

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

@router.get("/zones")
def list_zones(db=Depends(get_db), user=Depends(require_role("viewer"))):
    return [{"id": z.id, "name": z.name, "lat1": z.lat1, "lon1": z.lon1,
             "lat2": z.lat2, "lon2": z.lon2, "enabled": z.enabled,
             "lookback_days": z.lookback_days,
             "scan_interval_hr": z.scan_interval_hr,
             "river_buffer_m": z.river_buffer_m or 300.0,
             "roi_polygon": json.loads(z.roi_polygon) if z.roi_polygon
                            else None,
             "last_scan_at": z.last_scan_at.isoformat()
                             if z.last_scan_at else None,
             "candidates_open": db.query(LakeCandidate).filter(
                 LakeCandidate.zone_id == z.id,
                 LakeCandidate.status.in_(("DETECTED", "VERIFIED"))).count()}
            for z in db.query(MonitoringZone).order_by(MonitoringZone.name).all()]

@router.post("/zones", status_code=201)
def create_zone(body: ZoneIn, db=Depends(get_db),
                user=Depends(require_role("analyst"))):
    if abs(body.lat2 - body.lat1) > 2.0 or abs(body.lon2 - body.lon1) > 2.0:
        raise HTTPException(422, "Zone bbox too large (max 2x2 degrees)")
    z = MonitoringZone(id=new_id("MZ"), **body.model_dump(),
                       created_by=user["sub"])
    db.add(z); audit(db, user["sub"], "zone.create", z.id); db.commit()
    return {"id": z.id, "name": z.name}

@router.delete("/zones/{zid}")
def delete_zone(zid: str, db=Depends(get_db),
                user=Depends(require_role("admin"))):
    if not db.get(MonitoringZone, zid):
        raise HTTPException(404, "Zone not found")
    db.query(LakeCandidate).filter(LakeCandidate.zone_id == zid).delete()
    db.query(MonitoringZone).filter(MonitoringZone.id == zid).delete()
    audit(db, user["sub"], "zone.delete", zid); db.commit()
    return {"ok": True}

@router.post("/zones/{zid}/scan")
async def scan_now(zid: str, db=Depends(get_db),
                   user=Depends(require_role("analyst"))):
    if not db.get(MonitoringZone, zid):
        raise HTTPException(404, "Zone not found")
    try:
        result = await detection.scan_zone(zid)
    except Exception as exc:
        result = {"ok": False, "error": f"Scan failed: {exc}", "candidates": []}
    audit(db, user["sub"], "zone.scan", f"{zid}:{result.get('ok')}")
    db.commit()
    return result

@router.post("/zones/{zid}/baseline/rebuild")
async def rebuild_baseline(zid: str, db=Depends(get_db),
                           user=Depends(require_role("analyst"))):
    z = db.get(MonitoringZone, zid)
    if not z:
        raise HTTPException(404, "Zone not found")
    try:
        return await detection.build_baseline(z)
    except Exception as exc:
        return {"ok": False, "error": f"Baseline build failed: {exc}"}

@router.put("/zones/{zid}/roi")
def set_roi(zid: str, body: RoiIn, db=Depends(get_db),
            user=Depends(require_role("analyst"))):
    z = db.get(MonitoringZone, zid)
    if not z:
        raise HTTPException(404, "Zone not found")
    try:
        cleaned, warnings = roi.validate_roi_polygon(
            body.polygon, detection.zone_bbox(z))
    except ValueError as e:
        raise HTTPException(422, str(e))
    z.roi_polygon = json.dumps(cleaned)
    audit(db, user["sub"], "zone.roi.set",
          f"{zid} ({len(cleaned)} pts)")
    db.commit()
    return {"ok": True, "points": len(cleaned), "warnings": warnings,
            "area_km2": round(roi.polygon_area_km2(cleaned), 2),
            "note": "Effective next scan. Rebuild the baseline so its "
                    "statistics match the ROI."}

@router.delete("/zones/{zid}/roi")
def clear_roi(zid: str, db=Depends(get_db),
              user=Depends(require_role("analyst"))):
    z = db.get(MonitoringZone, zid)
    if not z:
        raise HTTPException(404, "Zone not found")
    z.roi_polygon = None
    audit(db, user["sub"], "zone.roi.clear", zid); db.commit()
    return {"ok": True}

@router.put("/zones/{zid}/buffer")
def set_buffer(zid: str, body: BufferIn, db=Depends(get_db),
               user=Depends(require_role("analyst"))):
    z = db.get(MonitoringZone, zid)
    if not z:
        raise HTTPException(404, "Zone not found")
    z.river_buffer_m = body.river_buffer_m
    audit(db, user["sub"], "zone.buffer.set", f"{zid}:{body.river_buffer_m}m")
    db.commit()
    return {"ok": True, "river_buffer_m": z.river_buffer_m}

@router.get("/zones/{zid}/sar-threshold")
def get_zone_sar_threshold(zid: str, db=Depends(get_db),
                           user=Depends(require_role("viewer"))):
    if not db.get(MonitoringZone, zid):
        raise HTTPException(404, "Zone not found")
    return {"zone_id": zid,
            "threshold_db": water.get_sar_threshold(zid),
            "default_db": water.S1_WATER_DB,
            "note": "sigma0 threshold for SAR water classification (dB)"}

@router.put("/zones/{zid}/sar-threshold")
def set_zone_sar_threshold(zid: str, body: dict, db=Depends(get_db),
                           user=Depends(require_role("analyst"))):
    if not db.get(MonitoringZone, zid):
        raise HTTPException(404, "Zone not found")
    thr = body.get("threshold_db")
    if thr is None:
        raise HTTPException(422, "threshold_db field required")
    try:
        updated = water.set_sar_threshold(zid, float(thr))
    except ValueError as e:
        raise HTTPException(422, str(e))
    audit(db, user["sub"], "zone.sar_threshold.set", f"{zid}:{updated}dB")
    db.commit()
    return {"ok": True, "zone_id": zid, "threshold_db": updated}

@router.get("/candidates")
def list_candidates(zone_id: str = None, status: str = None,
                    db=Depends(get_db), user=Depends(require_role("viewer")),
                    limit: int = Query(100, ge=1, le=300),
                    offset: int = Query(0, ge=0)):
    q = db.query(LakeCandidate)
    if zone_id:
        q = q.filter(LakeCandidate.zone_id == zone_id)
    if status:
        q = q.filter(LakeCandidate.status == status)
    q = q.order_by(LakeCandidate.score.desc(),
                   LakeCandidate.last_seen_at.desc())
    total = q.count()
    return {"total": total, "items": [{
        "id": c.id, "zone_id": c.zone_id, "lat": c.lat, "lon": c.lon,
        "bbox": json.loads(c.bbox), "area_m2": c.area_m2,
        "area_km2": round((c.area_m2 or 0) / 1e6, 4),
        "depth_m": c.depth_m, "volume_m3": c.volume_m3, "wse_m": c.wse_m,
        "score": c.score, "compactness": c.compactness,
        "river_adjacency": c.river_adjacency, "status": c.status,
        "growing": c.growing, "alert_level": c.alert_level,
        "first_seen_scene": c.first_seen_scene,
        "last_seen_scene": c.last_seen_scene,
        "first_seen_at": c.first_seen_at.isoformat(),
        "last_seen_at": c.last_seen_at.isoformat(),
        "incident_id": c.incident_id}
        for c in q.limit(limit).offset(offset).all()]}

@router.patch("/candidates/{cid}/verify")
def verify_candidate(cid: str, body: VerifyIn, db=Depends(get_db),
                     user=Depends(require_role("analyst"))):
    c = db.get(LakeCandidate, cid)
    if not c:
        raise HTTPException(404, "Candidate not found")
    c.status = body.status; c.verified_by = user["sub"]
    audit(db, user["sub"], f"candidate.{body.status.lower()}", cid)
    db.commit()
    return {"id": c.id, "status": c.status}

@router.post("/candidates/{cid}/promote", status_code=201)
def promote_to_incident(cid: str, db=Depends(get_db),
                        user=Depends(require_role("analyst"))):
    c = db.get(LakeCandidate, cid)
    if not c:
        raise HTTPException(404, "Candidate not found")
    if c.status != "VERIFIED":
        raise HTTPException(422, "Verify the candidate first")
    if c.incident_id:
        return {"incident_id": c.incident_id, "note": "already promoted"}
    inc = Incident(id=new_id("JR"),
                   name=f"Auto-detected lake {c.id} ({c.zone_id})",
                   incident_type="Temporary Lake", river_name="",
                   lat=c.lat, lon=c.lon, region="Auto-detection",
                   status="NEW_ANALYSIS",
                   created_by=f"detector:{user['sub']}", centerline="[]")
    db.add(inc)
    c.incident_id = inc.id
    audit(db, user["sub"], "candidate.promote", f"{cid}->{inc.id}")
    db.commit()
    return {"incident_id": inc.id,
            "prefill": {"lake_area_m2": c.area_m2,
                        "dam_height_m": c.depth_m,
                        "stored_volume_m3": c.volume_m3}}

@router.get("/candidates/{cid}/growth")
def candidate_growth(cid: str, db=Depends(get_db),
                     user=Depends(require_role("viewer"))):
    r = growth.analyze_growth(cid, db=db)
    if not r.get("ok"):
        raise HTTPException(404, r.get("error", "not found"))
    return r

@router.get("/alerts")
def alerts(db=Depends(get_db), user=Depends(require_role("viewer"))):
    return {"items": growth.open_alerts(db)}

@router.get("/growth-thresholds")
def get_growth_thresholds(user=Depends(require_role("viewer"))):
    return growth.get_growth_thresholds()

@router.put("/growth-thresholds")
def update_growth_thresholds(body: dict, user=Depends(require_role("analyst"))):
    try:
        growth.set_growth_thresholds(**body)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    return growth.get_growth_thresholds()

