import csv, io, json, uuid, math
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Response
from sqlalchemy.orm import Session
from ..db import SessionLocal, Incident, Asset, Upload, Simulation,     DamageReport, new_id
from ..schemas import IncidentIn, IncidentPatch, CenterlineIn
from ..security import require_role, audit, sanitize_text
from ..config import cfg, UPLOADS_DIR
from ..services.geo import validate_centerline, haversine, destination
from ..services.dem_flow_router import trace_dambreak_valley_dem
import numpy as np

router = APIRouter(prefix="/api", tags=["incidents"])

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

@router.get("/incidents")
def list_incidents(db=Depends(get_db), user=Depends(require_role("viewer")),
                   limit: int = Query(50, ge=1, le=200),
                   offset: int = Query(0, ge=0)):
    q = db.query(Incident).order_by(Incident.created_at.desc())
    total = q.count()
    return {"total": total, "items": [
        {"id": i.id, "name": i.name, "incident_type": i.incident_type,
         "river_name": i.river_name, "lat": i.lat, "lon": i.lon,
         "region": i.region, "status": i.status,
         "is_manual": bool(i.is_manual),
         "has_centerline": len(json.loads(i.centerline or "[]")) >= 2,
         "has_dem": bool(i.dem_upload_id)}
        for i in q.limit(limit).offset(offset).all()]}

@router.post("/incidents", status_code=201)
def create_incident(body: IncidentIn, db=Depends(get_db),
                    user=Depends(require_role("analyst"))):
    inc = Incident(id=new_id("JR"), **body.model_dump(),
                   created_by=user["sub"])
    db.add(inc); audit(db, user["sub"], "incident.create", inc.id); db.commit()
    return {"id": inc.id, "name": inc.name}

@router.get("/incidents/{iid}")
def get_incident(iid: str, db=Depends(get_db),
                 user=Depends(require_role("viewer"))):
    inc = db.get(Incident, iid)
    if not inc:
        raise HTTPException(404, "Incident not found")
    return {"id": inc.id, "name": inc.name, "lat": inc.lat, "lon": inc.lon,
            "centerline": json.loads(inc.centerline or "[]"),
            "status": inc.status, "region": inc.region,
            "river_name": inc.river_name, "incident_type": inc.incident_type}

@router.patch("/incidents/{iid}")
def patch_incident(iid: str, body: IncidentPatch, db=Depends(get_db),
                   user=Depends(require_role("analyst"))):
    inc = db.get(Incident, iid)
    if not inc:
        raise HTTPException(404, "Incident not found")
    old_lat, old_lon = inc.lat, inc.lon
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(inc, k, v)

    # If location moved, shift centerline to keep it anchored at new dam position
    if (body.lat is not None or body.lon is not None) and inc.centerline:
        try:
            pts = json.loads(inc.centerline)
            if pts:
                d_lat = inc.lat - old_lat
                d_lon = inc.lon - old_lon
                pts = [[round(p[0] + d_lat, 5), round(p[1] + d_lon, 5)] for p in pts]
                pts[0] = [round(inc.lat, 5), round(inc.lon, 5)]
                inc.centerline = json.dumps(pts)
        except Exception:
            pass

    audit(db, user["sub"], "incident.patch", iid)
    db.commit()
    return {"ok": True, "lat": inc.lat, "lon": inc.lon}

@router.delete("/incidents/{iid}")
def delete_incident(iid: str, db=Depends(get_db),
                    user=Depends(require_role("admin"))):
    if not db.get(Incident, iid):
        raise HTTPException(404, "Incident not found")
    for model in (Simulation, Asset, DamageReport, Upload):
        db.query(model).filter(model.incident_id == iid).delete()
    db.query(Incident).filter(Incident.id == iid).delete()
    audit(db, user["sub"], "incident.delete", iid); db.commit()
    return {"ok": True}

@router.put("/incidents/{iid}/centerline")
def set_centerline(iid: str, body: CenterlineIn, db=Depends(get_db),
                   user=Depends(require_role("analyst"))):
    inc = db.get(Incident, iid)
    if not inc:
        raise HTTPException(404, "Incident not found")
    cleaned, warnings = validate_centerline(body.centerline)
    if len(cleaned) < 2:
        raise HTTPException(422, "Centerline rejected: " +
                            (" ".join(warnings) or "too few points"))
    length_km = 0.0
    for i in range(1, len(cleaned)):
        length_km += haversine(*cleaned[i-1], *cleaned[i]) / 1000.0
    inc.centerline = json.dumps(cleaned)
    audit(db, user["sub"], "incident.centerline",
          f"{iid} ({len(cleaned)} pts, {length_km:.1f} km)")
    db.commit()
    return {"ok": True, "points": len(cleaned),
            "length_km": round(length_km, 1), "warnings": warnings}

@router.delete("/incidents/{iid}/centerline")
def clear_centerline(iid: str, db=Depends(get_db),
                     user=Depends(require_role("analyst"))):
    inc = db.get(Incident, iid)
    if not inc:
        raise HTTPException(404, "Incident not found")
    inc.centerline = "[]"
    audit(db, user["sub"], "incident.centerline.clear", iid)
    db.commit()
    return {"ok": True, "points": 0, "length_km": 0.0, "centerline": []}

@router.post("/incidents/{iid}/auto-centerline")
def auto_centerline(iid: str, bearing_deg: float = 135.0, length_km: float = 15.0,
                    method: str = "dem",
                    db=Depends(get_db), user=Depends(require_role("analyst"))):
    inc = db.get(Incident, iid)
    if not inc:
        raise HTTPException(404, "Incident not found")

    if method == "dem":
        pts = trace_dambreak_valley_dem(inc.lat, inc.lon, initial_bearing=bearing_deg, total_km=length_km, dam_name=inc.name)
    else:
        pts = [[round(inc.lat, 5), round(inc.lon, 5)]]
        total_m = int(max(1.0, length_km) * 1000)
        for d in range(500, total_m + 1, 500):
            la, lo = destination(inc.lat, inc.lon, bearing_deg, d)
            pts.append([round(la, 5), round(lo, 5)])

    length_km_calc = 0.0
    for i in range(1, len(pts)):
        length_km_calc += haversine(*pts[i-1], *pts[i]) / 1000.0

    inc.centerline = json.dumps(pts)
    audit(db, user["sub"], "incident.centerline.auto", f"{iid}:{len(pts)}pts:{method}")
    db.commit()
    return {"ok": True, "points": len(pts), "length_km": round(length_km_calc, 1), "centerline": pts, "method": method}

@router.get("/incidents/{iid}/assets")
def incident_assets(iid: str, db=Depends(get_db),
                    user=Depends(require_role("viewer"))):
    q = db.query(Asset).filter(Asset.incident_id == iid)
    return [{"kind": a.kind, "name": a.name, "lat": a.lat, "lon": a.lon,
             "population": a.population, "buildings": a.buildings,
             "critical": a.critical, "source": a.source,
             "attributes": json.loads(a.attributes or "{}")} for a in q.all()]

@router.get("/incidents/{iid}/dem")
def get_dem(iid: str, db=Depends(get_db), user=Depends(require_role("viewer"))):
    inc = db.get(Incident, iid)
    if not inc or not inc.dem_upload_id:
        return {"has_dem": False}
    up = db.get(Upload, inc.dem_upload_id)
    if not up:
        return {"has_dem": False}
    meta = json.loads(up.meta or "{}")
    return {"has_dem": True, "points": meta.get("points"),
            "cell_size_m": meta.get("cell_size_m"),
            "elev_range_m": meta.get("elev_range_m"),
            "hypsometry": meta.get("hypsometry", [])}

ALLOWED = {".geojson", ".json", ".csv"}

@router.post("/incidents/{iid}/uploads")
async def upload(iid: str, file: UploadFile = File(...), db=Depends(get_db),
                 user=Depends(require_role("analyst"))):
    if not db.get(Incident, iid):
        raise HTTPException(404, "Incident not found")
    ext = "." + (file.filename or "").rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED:
        raise HTTPException(400, f"Unsupported '{ext}'. Allowed: GeoJSON, CSV")
    raw = await file.read()
    if len(raw) > cfg.MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, f"Max upload size is {cfg.MAX_UPLOAD_MB} MB")
    stored = f"{uuid.uuid4().hex}{ext}"
    (UPLOADS_DIR / stored).write_bytes(raw)
    kind, meta = "other", {}
    if ext in (".geojson", ".json"):
        kind, meta = _parse_geojson(raw, db, iid)
    else:
        head = raw[:4096].decode("utf-8", errors="ignore")
        cols = {c.strip().lower() for c in
                (head.splitlines() or [""])[0].split(",")}
        if ({"lat", "lon", "elev"} <= cols) or \
           ({"latitude", "longitude", "elevation"} <= cols):
            kind, meta = _parse_dem_csv(raw)
        elif "name" in cols and ("lat" in cols or "latitude" in cols):
            kind, meta = _parse_assets_csv(raw, db, iid)
        else:
            raise HTTPException(400, "CSV must be a DEM grid (lat,lon,elev) "
                                     "or an asset list (name,lat,lon,...)")
    up = Upload(kind=kind, original_name=(file.filename or "upload")[:255],
                stored_name=stored, incident_id=iid, meta=json.dumps(meta))
    db.add(up)
    if kind == "dem_csv":
        db.get(Incident, iid).dem_upload_id = up.id
    audit(db, user["sub"], "upload", f"{kind}:{file.filename}")
    db.commit()
    return {"upload_id": up.id, "kind": kind, "meta": meta}

def _parse_geojson(raw, db, iid):
    try:
        gj = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid JSON")
    feats = gj.get("features", []) if gj.get("type") == "FeatureCollection" else [gj]
    added = 0
    for f in feats:
        g = f.get("geometry") or {}
        if g.get("type") != "Point":
            raise HTTPException(400, "Only Point features supported")
        try:
            lon, lat = g.get("coordinates", [None, None])[:2]
            lat, lon = float(lat), float(lon)
        except (TypeError, ValueError):
            continue
        p = f.get("properties", {}) or {}
        kind = sanitize_text(str(p.get("kind", "")), 20) or \
               ("infrastructure" if p.get("critical") else
                "agriculture" if p.get("area_ha") else "settlement")
        db.add(Asset(incident_id=iid, kind=kind,
                     name=sanitize_text(str(p.get("name", f"Feature {added+1}")), 120),
                     lat=lat, lon=lon,
                     population=int(float(p.get("population", 0) or 0)),
                     buildings=int(float(p.get("buildings", 0) or 0)),
                     livestock=int(float(p.get("livestock", 0) or 0)),
                     critical=bool(p.get("critical", False)),
                     attributes=json.dumps({k: v for k, v in p.items()
                        if k not in ("name", "population", "buildings")}),
                     source="upload"))
        added += 1
    return ("assets" if added else "other"), {"features_ingested": added}

def _parse_assets_csv(raw, db, iid):
    rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8", errors="ignore"))))
    added = 0
    for r in rows:
        try:
            lat = float(r.get("lat") or r.get("latitude") or "nan")
            lon = float(r.get("lon") or r.get("longitude") or "nan")
            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                continue
        except (TypeError, ValueError):
            continue
        db.add(Asset(incident_id=iid,
                     kind=sanitize_text(r.get("kind", ""), 20) or "settlement",
                     name=sanitize_text(r.get("name", f"Row {added+1}"), 120),
                     lat=lat, lon=lon,
                     population=int(float(r.get("population", 0) or 0)),
                     buildings=int(float(r.get("buildings", 0) or 0)),
                     critical=str(r.get("critical", "")).lower() in
                              ("1", "true", "yes"),
                     attributes=json.dumps(
                         {k: v for k, v in r.items()
                          if k in ("area_ha", "crop", "type") and v}),
                     source="upload"))
        added += 1
    return "assets", {"features_ingested": added}

def _parse_dem_csv(raw):
    rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8", errors="ignore"))))
    pts = []
    for r in rows:
        try:
            la = float(r.get("lat") or r.get("latitude"))
            lo = float(r.get("lon") or r.get("longitude"))
            e = float(r.get("elev") or r.get("elevation"))
            if -90 <= la <= 90 and -180 <= lo <= 180:
                pts.append((la, lo, e))
        except (TypeError, ValueError):
            continue
    if len(pts) < 50:
        raise HTTPException(400, f"DEM CSV needs >= 50 valid rows (got {len(pts)})")
    lats = sorted(p[0] for p in pts); lons = sorted(p[1] for p in pts)
    med = lambda a: a[len(a)//2]
    cell = max((med(lats[1:]) - med(lats[:-1])) * 111000,
               (med(lons[1:]) - med(lons[:-1])) * 111000 *
               math.cos(math.radians(med(lats))), 1.0)
    elevs = np.array([p[2] for p in pts])
    levels = np.linspace(elevs.min(), elevs.max(), 40)
    curve = []
    for lv in levels:
        area = float((elevs >= lv).sum()) * cell * cell
        curve.append({"elev_m": round(float(lv), 1), "area_m2": round(area, 0)})
    vol = 0.0
    for i in range(1, len(curve)):
        vol += 0.5 * (curve[i]["area_m2"] + curve[i-1]["area_m2"]) * \
               (curve[i]["elev_m"] - curve[i-1]["elev_m"])
        curve[i-1]["cum_volume_m3"] = round(vol, 0)
    curve[-1]["cum_volume_m3"] = round(vol, 0)
    return "dem_csv", {"points": len(pts), "cell_size_m": round(cell, 1),
                       "elev_range_m": [round(float(elevs.min()), 1),
                                        round(float(elevs.max()), 1)],
                       "hypsometry": curve}

@router.get("/incidents/{iid}/population-clusters")
def incident_population_clusters(iid: str, db=Depends(get_db)):
    from ..services.population_clusters import get_population_clusters
    inc = db.get(Incident, iid)
    if not inc:
        raise HTTPException(404, "Incident not found")
    clusters = get_population_clusters(iid, db)
    return {"incident_id": iid, "incident_name": inc.name, "clusters": clusters, "total_clusters": len(clusters)}

@router.get("/incidents/{iid}/scenario-extents")
def incident_scenario_extents(iid: str, db=Depends(get_db)):
    from ..services.scenario_extents import get_simulation_scenario_extents
    inc = db.get(Incident, iid)
    if not inc:
        raise HTTPException(404, "Incident not found")
    sim = (db.query(Simulation)
           .filter(Simulation.incident_id == iid, Simulation.status == "DONE")
           .order_by(Simulation.created_at.desc())
           .first())
    if not sim:
        raise HTTPException(404, "No completed simulation found for this incident")
    return get_simulation_scenario_extents(sim.id, db)

@router.get("/incidents/{iid}/export/shapefile.zip")
@router.get("/incidents/{iid}/export/gis-package.zip")
def incident_export_shapefile(iid: str, db=Depends(get_db)):
    inc = db.get(Incident, iid)
    if not inc:
        raise HTTPException(404, "Incident not found")
    sim = (db.query(Simulation)
           .filter(Simulation.incident_id == iid, Simulation.status == "DONE")
           .order_by(Simulation.created_at.desc())
           .first())
    if not sim or not sim.results:
        raise HTTPException(404, "No completed simulation found for this incident. Run a breach simulation first.")
    
    from ..services.export_gis import generate_shapefile_zip
    res = json.loads(sim.results) if isinstance(sim.results, str) else sim.results
    assets_raw = res.get("visual", {}).get("impact", [])
    pkg = generate_shapefile_zip(res, inc.name, res.get("inundation", {}), assets_raw)
    safe_name = "".join(c if c.isalnum() else "_" for c in inc.name[:30]).strip("_")
    return Response(pkg, media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={safe_name}_shapefile_package.zip"})

@router.get("/incidents/{iid}/export/flood.kml")
@router.get("/incidents/{iid}/export/kml")
def incident_export_kml(iid: str, db=Depends(get_db)):
    inc = db.get(Incident, iid)
    if not inc:
        raise HTTPException(404, "Incident not found")
    sim = (db.query(Simulation)
           .filter(Simulation.incident_id == iid, Simulation.status == "DONE")
           .order_by(Simulation.created_at.desc())
           .first())
    if not sim or not sim.results:
        raise HTTPException(404, "No completed simulation found for this incident.")
    
    from ..services.export_gis import generate_kml
    res = json.loads(sim.results) if isinstance(sim.results, str) else sim.results
    assets_raw = res.get("visual", {}).get("impact", [])
    kml = generate_kml(res, inc.name, res.get("inundation", {}), assets_raw)
    safe_name = "".join(c if c.isalnum() else "_" for c in inc.name[:30]).strip("_")
    return Response(kml, media_type="application/vnd.google-earth.kml+xml",
        headers={"Content-Disposition": f"attachment; filename={safe_name}_flood_simulation.kml"})

@router.get("/incidents/{iid}/export/gee-script.js")
def incident_export_gee(iid: str, db=Depends(get_db)):
    inc = db.get(Incident, iid)
    if not inc:
        raise HTTPException(404, "Incident not found")
    sim = (db.query(Simulation)
           .filter(Simulation.incident_id == iid, Simulation.status == "DONE")
           .order_by(Simulation.created_at.desc())
           .first())
    
    from ..services.gee_framework import generate_gee_javascript
    poly = None
    peak_q = 12000.0
    max_d = 15.0
    corridor_km = 35.0
    if sim and sim.results:
        res = json.loads(sim.results) if isinstance(sim.results, str) else sim.results
        inun = res.get("inundation", {})
        poly = inun.get("max_extent_ring")
        peak_q = res.get("breach", {}).get("peak_Q_m3s", 12000.0)
        max_d = inun.get("max_depth_m", 15.0)
        corridor_km = inun.get("corridor_km", 35.0)
        
    js_code = generate_gee_javascript(
        inc.name, inc.lat, inc.lon, poly,
        event_date=inc.created_at.isoformat() if inc.created_at else None,
        corridor_km=corridor_km,
        peak_q_m3s=peak_q,
        max_depth_m=max_d
    )
    safe_name = "".join(c if c.isalnum() else "_" for c in inc.name[:30]).strip("_")
    return Response(js_code, media_type="application/javascript",
        headers={"Content-Disposition": f"attachment; filename={safe_name}_google_earth_engine_sentinel1.js"})

@router.get("/incidents/{iid}/export/flood.geojson")
@router.get("/incidents/{iid}/export/geojson")
@router.get("/incidents/{iid}/geojson")
def incident_export_geojson(iid: str, db=Depends(get_db)):
    inc = db.get(Incident, iid)
    if not inc:
        raise HTTPException(404, "Incident not found")
    sim = (db.query(Simulation)
           .filter(Simulation.incident_id == iid, Simulation.status == "DONE")
           .order_by(Simulation.created_at.desc())
           .first())
    if not sim or not sim.results:
        raise HTTPException(404, "No completed simulation found for this incident")
    res = json.loads(sim.results) if isinstance(sim.results, str) else sim.results
    from ..services import assessment
    safe_name = "".join(c if c.isalnum() else "_" for c in inc.name[:30]).strip("_")
    return Response(json.dumps(assessment.flood_geojson(res.get("inundation", {}))),
        media_type="application/geo+json",
        headers={"Content-Disposition": f"attachment; filename={safe_name}_flood.geojson"})


