import json
import logging
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Response, Query
from sqlalchemy.orm import Session
from ..db import (SessionLocal, Incident, Simulation, Asset, DamageReport,
                   Upload, new_id)
from ..schemas import BreachParams, ManualRunIn
from ..security import require_role, audit
from .. import jobs
from ..services import hydraulics, assessment, breach_models, india
from ..services.geo import destination
from ..services.inundation_2d import try_2d_then_fallback

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["simulations"])

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()


def _run_pipeline(sim_id, rec):
    """Worker thread: erosion/overtopping breach + Cunge routing + visual +
    evacuation, all from the SAME stored parameters. Progress + cancel."""
    db = SessionLocal()
    try:
        sim = db.get(Simulation, sim_id)
        params = json.loads(sim.params)
        inc = db.get(Incident, sim.incident_id)
        centerline = json.loads(inc.centerline or "[]")
        cancel = lambda: rec["cancel"]

        hyp = None
        if inc.dem_upload_id:
            up = db.get(Upload, inc.dem_upload_id)
            if up and up.kind == "dem_csv":
                hyp = json.loads(up.meta or "{}").get("hypsometry")

        p = {k: params[k] for k in
             ("stored_volume_m3", "lake_area_m2", "dam_height_m",
              "dam_crest_len_m", "breach_width_m", "breach_depth_m",
              "breach_time_hr", "inflow_m3s", "dam_material")}
        p["incident_id"] = sim.incident_id
        rec["progress"] = 5
        breach = breach_models.simulate_breach(
            p, hypsometry=hyp, cancel=cancel,
            progress=lambda v: rec.__setitem__("progress", 5 + 25 * v))
        breach["empirical_ensemble"] = breach_models.empirical_peak_discharge(
            p["stored_volume_m3"], p["dam_height_m"])
        breach["literature_breach_geometry"] = \
            breach_models.empirical_breach_geometry(
                p["stored_volume_m3"], p["dam_height_m"])
        breach["empirical_froehlich1995_Qp"] = \
            breach["empirical_ensemble"]["equations"]["Froehlich (1995)"]
        rec["progress"] = 35
        # ---- Attempt to load cached GLO-30 DEM bytes for 2D routing ----------
        dem_bytes = None
        try:
            from ..config import cfg as _cfg
            from ..services import dem as dem_svc
            zone_lat = int(inc.lat) if inc.lat is not None else 0
            zone_lon = int(inc.lon) if inc.lon is not None else 0
            cache_path = (Path(_cfg.DB_PATH).parent /
                          f"dem_cache/{zone_lat}_{zone_lon}_dem.tif")
            alt_tile = (Path(_cfg.DB_PATH).parent /
                        f"dem_cache/{dem_svc._tile_name(zone_lat, zone_lon)}.tif")
            if cache_path.exists():
                dem_bytes = cache_path.read_bytes()
                log.info("Loaded DEM from cache: %s", cache_path)
            elif alt_tile.exists():
                dem_bytes = alt_tile.read_bytes()
                log.info("Loaded DEM from alt tile: %s", alt_tile)
            else:
                clats = [p[0] for p in centerline] if centerline else [inc.lat]
                clons = [p[1] for p in centerline] if centerline else [inc.lon]
                pad = 0.05
                minlat, maxlat = min(clats) - pad, max(clats) + pad
                minlon, maxlon = min(clons) - pad, max(clons) + pad
                try:
                    import rasterio                          # noqa: F401
                    import rasterio.transform
                    import io as _io
                    grid = dem_svc.dem_for_bbox(minlat, minlon, maxlat, maxlon)
                    if grid is not None:
                        h, w = grid.shape
                        xform = rasterio.transform.from_bounds(
                            minlon, minlat, maxlon, maxlat, w, h)
                        buf = _io.BytesIO()
                        with rasterio.open(buf, "w", driver="GTiff",
                                           height=h, width=w, count=1,
                                           dtype="float32", crs="EPSG:4326",
                                           transform=xform) as dst:
                            dst.write(grid.astype("float32"), 1)
                        dem_bytes = buf.getvalue()
                        log.info("Fetched fresh DEM; bytes=%d", len(dem_bytes))
                except Exception as _dem_err:
                    log.info("DEM fetch/encode skipped (%s); 1D routing used.",
                             _dem_err)
        except Exception as _outer_err:
            log.info("DEM prep failed (%s); 1D routing used.", _outer_err)

        inun = try_2d_then_fallback(
            breach, centerline, params,
            dem_bytes=dem_bytes, cancel=cancel,
            progress=lambda v: rec.__setitem__("progress", 35 + 30 * v),
            debris_bulking_factor=params.get("debris_bulking_factor", 1.0))
        rec["progress"] = 65
        assets = db.query(Asset).filter(
            Asset.incident_id == sim.incident_id).all()
        expo = assessment.assess_exposure(inun, assets)
        rec["progress"] = 70
        simrec = {"params": params,
                  "results": {"breach": breach, "inundation": inun}}
        risk = assessment.calculate_tdri(simrec, expo)
        unc = None
        if params.get("with_uncertainty"):
            unc = hydraulics.monte_carlo(
                p, params, centerline, n_runs=120, cancel=cancel,
                progress=lambda v: rec.__setitem__("progress", 70 + 28 * v))
        rec["progress"] = 98
        n_verified = db.query(DamageReport).filter(
            DamageReport.incident_id == sim.incident_id,
            DamageReport.status == "VERIFIED").count()
        conf = assessment.compute_confidence(bool(unc), inc, len(assets),
                                             n_verified)
        # visual + evacuation (from the SAME routed results)
        from ..services import impact_models, evacuation
        asset_dicts = [{"kind": a.kind, "name": a.name, "lat": a.lat,
                        "lon": a.lon, "population": a.population,
                        "buildings": a.buildings, "livestock": a.livestock,
                        "critical": a.critical,
                        "attributes": json.loads(a.attributes or "{}")}
                       for a in assets]
        reg_obj = india.region_for(inc.lat, inc.lon) if (inc and inc.lat and inc.lon) else None
        region_key = reg_obj.key if reg_obj else None
        visual = impact_models.build_visual_simulation(
            breach, inun, params, asset_dicts,
            incident_id=sim.incident_id,
            region_key=region_key)
        ev = (evacuation.build_evacuation_overlay(
            visual, inun["nodes"], params, inc.lat, inc.lon)
            if visual else None)
        from ..services.hydrodynamic_solvers import compare_hydrodynamic_scenarios
        try:
            hydro_comp = compare_hydrodynamic_scenarios(
                breach, inun.get("nodes", []), expo.get("settlements", []), params
            )
        except Exception as _hc_err:
            log.warning("Hydrodynamic comparison generation skipped: %s", _hc_err)
            hydro_comp = None

        results = {"breach": breach, "inundation": inun, "exposure": expo,
                   "risk": risk, "uncertainty": unc, "confidence": conf,
                   "visual": visual, "evacuation": ev,
                   "hydrodynamic_comparison": hydro_comp,
                   "used_2d": inun.get("used_2d", False),
                   "engine_version": "4.2"}
        if inc.is_manual:
            results["entry_mode"] = "MANUAL_OFFICIAL_INPUT"
        sim.results = json.dumps(results)
        sim.status = "DONE"
        db.commit()
        rec["progress"] = 100
    except jobs.JobCancelled:
        db.rollback()
        sim = db.get(Simulation, sim_id)
        if sim:
            sim.status, sim.error = "CANCELLED", "Cancelled by user"
            db.commit()
        raise
    except Exception:
        db.rollback()
        sim = db.get(Simulation, sim_id)
        if sim:
            sim.status, sim.error = "FAILED", "server error (see logs)"
            db.commit()
        raise
    finally:
        db.close()


@router.post("/simulations", status_code=201)
def create_simulation(incident_id: str, params: BreachParams,
                      db=Depends(get_db),
                      user=Depends(require_role("analyst"))):
    inc = db.get(Incident, incident_id)
    if not inc:
        raise HTTPException(404, "Incident not found")
    if len(json.loads(inc.centerline or "[]")) < 2:
        raise HTTPException(422, "Draw a downstream centerline first")
    sim = Simulation(id=new_id("SIM"), incident_id=incident_id,
                     label=f"{params.scenario} breach",
                     params=params.model_dump_json(),
                     created_by=user["sub"])
    db.add(sim); audit(db, user["sub"], "sim.create", sim.id); db.commit()
    jid = jobs.submit(lambda rec: _run_pipeline(sim.id, rec))
    return {"simulation_id": sim.id, "job_id": jid}


@router.post("/simulations/manual", status_code=201)
def create_manual_simulation(body: ManualRunIn, db=Depends(get_db),
                             user=Depends(require_role("analyst"))):
    from ..services import manual as manual_svc
    resolved = manual_svc.resolve_manual_params(
        body.model_dump(exclude={"name", "auto_bearing_deg", "auto_length_km"}))
    cl = []
    if body.auto_bearing_deg is not None:
        for d in range(0, int(body.auto_length_km * 1000) + 1, 500):
            la, lo = destination(body.lat, body.lon,
                                 body.auto_bearing_deg, d)
            cl.append([round(la, 5), round(lo, 5)])
    if not cl:
        raise HTTPException(422, "Provide auto_bearing_deg for an automatic "
                                 "centerline, or draw one on the map first")
    inc_id = new_id("JR")
    db.add(Incident(id=inc_id, name=f"[MANUAL] {body.name}",
                    incident_type="Manual Scenario", river_name="",
                    lat=body.lat, lon=body.lon,
                    region=resolved["region"]["name"], status="MANUAL_RUN",
                    is_manual=True, created_by=user["sub"],
                    centerline=json.dumps(cl)))
    db.commit()
    params = BreachParams(**resolved["params"])
    sim = Simulation(id=new_id("SIM"), incident_id=inc_id,
                     label=f"manual:{body.scenario}",
                     params=params.model_dump_json(),
                     created_by=user["sub"])
    db.add(sim)
    audit(db, user["sub"], "sim.manual.create", f"{inc_id}/{sim.id}")
    db.commit()
    jid = jobs.submit(lambda rec: _run_pipeline(sim.id, rec))
    return {"simulation_id": sim.id, "incident_id": inc_id, "job_id": jid,
            "resolved_params": resolved["params"],
            "provenance": resolved["provenance"],
            "region": resolved["region"],
            "note": "Manual incidents persist - upload an exposure CSV or "
                    "redraw the centerline, then re-run, to upgrade this "
                    "estimate into a full assessment."}


@router.get("/simulations/{sid}")
def get_simulation(sid: str, db=Depends(get_db),
                   user=Depends(require_role("viewer"))):
    sim = db.get(Simulation, sid)
    if not sim:
        raise HTTPException(404, "Not found")
    return {"id": sim.id, "incident_id": sim.incident_id, "label": sim.label,
            "status": sim.status, "error": sim.error,
            "created_at": sim.created_at.isoformat(),
            "params": json.loads(sim.params),
            "results": json.loads(sim.results) if sim.status == "DONE" else None}

@router.get("/simulations")
def list_simulations(incident_id: str, db=Depends(get_db),
                     user=Depends(require_role("viewer")),
                     limit: int = Query(50, ge=1, le=200),
                     offset: int = Query(0, ge=0)):
    q = db.query(Simulation).filter(
        Simulation.incident_id == incident_id
    ).order_by(Simulation.created_at.desc())
    total = q.count()
    items = []
    for s in q.limit(limit).offset(offset).all():
        r = json.loads(s.results) if s.status == "DONE" else {}
        items.append({"id": s.id, "label": s.label, "status": s.status,
                      "created_at": s.created_at.isoformat(),
                      "peak_q": r.get("breach", {}).get("peak_Q_m3s"),
                      "max_area_km2": r.get("inundation", {})
                                     .get("max_area_km2")})
    return {"total": total, "items": items}

@router.delete("/simulations/{sid}")
def delete_simulation(sid: str, db=Depends(get_db),
                      user=Depends(require_role("analyst"))):
    sim = db.get(Simulation, sid)
    if not sim:
        raise HTTPException(404, "Not found")
    if user["role"] != "admin" and sim.created_by != user["sub"]:
        raise HTTPException(403, "Not your simulation")
    db.delete(sim); audit(db, user["sub"], "sim.delete", sid); db.commit()
    return {"ok": True}

@router.get("/jobs/{jid}")
def job_status(jid: str, user=Depends(require_role("viewer"))):
    return jobs.get(jid)

@router.post("/jobs/{jid}/cancel")
def job_cancel(jid: str, user=Depends(require_role("viewer"))):
    return {"ok": jobs.cancel(jid)}

@router.get("/simulations/{sid}/report")
def report(sid: str, db=Depends(get_db), user=Depends(require_role("viewer"))):
    sim = db.get(Simulation, sid)
    if not sim or sim.status != "DONE":
        raise HTTPException(404, "Simulation not found or not complete")
    res = json.loads(sim.results)
    b, inun = res.get("breach", {}), res.get("inundation", {})
    return {"title": f"JAL-RAKSHA Simulation Report - {sim.id}",
            "generated_from_simulation": sim.id,
            "parameters_used": json.loads(sim.params),
            "breach": {"peak_Q": b.get("peak_Q_m3s"),
                       "time_to_peak_min": b.get("time_to_peak_min"),
                       "Froehlich_check": b.get("empirical_froehlich1995_Qp"),
                       "drained_volume_m3": b.get("drained_volume_m3"),
                       "engine": b.get("engine")},
            "inundation_summary": {k: inun.get(k) for k in
                ("max_area_km2", "max_depth_m", "first_arrival_min",
                 "corridor_km", "method")},
            "limitations": (b.get("limitations", []) +
                            inun.get("limitations", [])),
            "note": "DEPRECATED - prefer /api/incidents/{id}/full-report"}

@router.get("/simulations/{sid}/provenance")
def get_provenance(sid: str, db=Depends(get_db),
                   user=Depends(require_role("viewer"))):
    sim = db.get(Simulation, sid)
    if not sim:
        raise HTTPException(404, "Not found")
    inc = db.get(Incident, sim.incident_id)
    if not (inc and inc.is_manual):
        return {"manual": False, "params": json.loads(sim.params)}
    from ..services.manual import resolve_manual_params
    stored = json.loads(sim.params)
    region = resolve_manual_params({
        "lat": inc.lat, "lon": inc.lon,
        "stored_volume_m3": stored["stored_volume_m3"],
        "dam_height_m": stored["dam_height_m"]})
    prov = {}
    for k, v in region["params"].items():
        prov[k] = ("USER/ADJUSTED" if k in stored and stored[k] != v
                   else "REGION_PRESET")
    prov["stored_volume_m3"] = "USER"
    prov["dam_height_m"] = "USER"
    return {"manual": True, "params": stored, "provenance": prov,
            "region": region["region"]}

@router.get("/simulations/{sid}/visual")
def get_visual(sid: str, db=Depends(get_db),
               user=Depends(require_role("viewer"))):
    sim = db.get(Simulation, sid)
    if not sim or sim.status != "DONE":
        raise HTTPException(404, "Simulation not found or not complete")
    res = json.loads(sim.results)
    if not res.get("visual"):
        raise HTTPException(404, "No visual payload (re-run the simulation)")
    return res["visual"]

@router.get("/simulations/{sid}/hydrodynamic-comparison")
def get_hydrodynamic_comparison(sid: str, db=Depends(get_db),
                                user=Depends(require_role("viewer"))):
    sim = db.get(Simulation, sid)
    if not sim or sim.status != "DONE":
        raise HTTPException(404, "Simulation not found or not complete")
    res = json.loads(sim.results)
    params = json.loads(sim.params)
    from ..services.hydrodynamic_solvers import compare_hydrodynamic_scenarios
    return compare_hydrodynamic_scenarios(
        res.get("breach", {}),
        res.get("inundation", {}).get("nodes", []),
        res.get("exposure", {}).get("settlements", []),
        params
    )

def _done_results(db, sid):
    sim = db.get(Simulation, sid)
    res = json.loads(sim.results or "{}") if sim else {}
    if "inundation" not in res and "exposure" not in res:
        raise HTTPException(404, "No results")
    return res, sid

@router.get("/simulations/{sid}/export/nodes.csv")
def export_nodes(sid: str, db=Depends(get_db),
                 user=Depends(require_role("viewer"))):
    res, sid = _done_results(db, sid)
    return Response(assessment.nodes_csv(res["inundation"]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={sid}_nodes.csv"})

@router.get("/simulations/{sid}/export/exposure.csv")
def export_exposure(sid: str, db=Depends(get_db),
                    user=Depends(require_role("viewer"))):
    res, sid = _done_results(db, sid)
    return Response(assessment.exposure_csv(res["exposure"]),
        media_type="text/csv",
        headers={"Content-Disposition":
                 f"attachment; filename={sid}_exposure.csv"})

@router.get("/simulations/{sid}/export/flood.geojson")
@router.get("/simulations/{sid}/export/geojson")
@router.get("/simulations/{sid}/geojson")
def export_geojson(sid: str, db=Depends(get_db),
                   user=Depends(require_role("viewer"))):
    res, sid = _done_results(db, sid)
    return Response(json.dumps(assessment.flood_geojson(res["inundation"])),
        media_type="application/geo+json",
        headers={"Content-Disposition":
                 f"attachment; filename={sid}_flood.geojson"})

@router.get("/simulations/{sid}/export/flood.kml")
@router.get("/simulations/{sid}/export/kml")
def export_kml(sid: str, db=Depends(get_db),
               user=Depends(require_role("viewer"))):
    res, sid = _done_results(db, sid)
    sim = db.get(Simulation, sid)
    inc = db.get(Incident, sim.incident_id) if sim else None
    inc_name = inc.name if inc else "Dam Break Scenario"
    assets_raw = res.get("visual", {}).get("impact", [])
    from ..services.export_gis import generate_kml
    kml = generate_kml(res, inc_name, res.get("inundation", {}), assets_raw)
    return Response(kml, media_type="application/vnd.google-earth.kml+xml",
        headers={"Content-Disposition": f"attachment; filename={sid}_flood_inundation.kml"})

@router.get("/simulations/{sid}/export/shapefile.zip")
@router.get("/simulations/{sid}/export/gis-package.zip")
def export_gis_package(sid: str, db=Depends(get_db),
                       user=Depends(require_role("viewer"))):
    res, sid = _done_results(db, sid)
    sim = db.get(Simulation, sid)
    inc = db.get(Incident, sim.incident_id) if sim else None
    inc_name = inc.name if inc else "Dam Break Scenario"
    assets_raw = res.get("visual", {}).get("impact", [])
    from ..services.export_gis import generate_shapefile_zip
    pkg = generate_shapefile_zip(res, inc_name, res.get("inundation", {}), assets_raw)
    return Response(pkg, media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={sid}_gis_shapefile_package.zip"})

@router.get("/incidents/{iid}/full-report")
def full_report(iid: str, run_id: str = None, db=Depends(get_db),
                user=Depends(require_role("viewer"))):
    if not db.get(Incident, iid):
        raise HTTPException(404, "Incident not found")
    from ..services import full_report
    rep = full_report.build_full_report(iid, run_id)
    if not rep.get("ok"):
        raise HTTPException(404, rep.get("error"))
    audit(db, user["sub"], "report.full", iid)
    db.commit()
    return rep

@router.get("/simulations/{sid}/scenario-extents")
def simulation_scenario_extents(sid: str, db=Depends(get_db)):
    from ..services.scenario_extents import get_simulation_scenario_extents
    sim = db.get(Simulation, sid)
    if not sim:
        raise HTTPException(404, "Simulation not found")
    data = get_simulation_scenario_extents(sid, db)
    if "error" in data:
        raise HTTPException(400, data["error"])
    return data

@router.get("/simulations/{sid}/export/gee-script.js")
def export_gee_script(sid: str, db=Depends(get_db),
                      user=Depends(require_role("viewer"))):
    res, sid = _done_results(db, sid)
    sim = db.get(Simulation, sid)
    inc = db.get(Incident, sim.incident_id) if sim else None
    inc_name = inc.name if inc else f"Simulation {sid}"
    lat = inc.lat if inc else 30.48
    lon = inc.lon if inc else 79.72
    inun = res.get("inundation", {})
    poly = inun.get("max_extent_ring")
    peak_q = res.get("breach", {}).get("peak_Q_m3s", 12000.0)
    max_d = inun.get("max_depth_m", 15.0)
    corridor_km = inun.get("corridor_km", 35.0)

    from ..services.gee_framework import generate_gee_javascript
    js_code = generate_gee_javascript(
        inc_name, lat, lon, poly,
        event_date=sim.created_at.isoformat() if sim and sim.created_at else None,
        corridor_km=corridor_km,
        peak_q_m3s=peak_q,
        max_depth_m=max_d
    )
    return Response(js_code, media_type="application/javascript",
        headers={"Content-Disposition": f"attachment; filename={sid}_gee_sentinel1_flood_verification.js"})

@router.get("/simulations/{sid}/gee-analysis")
def get_gee_analysis_summary(sid: str, db=Depends(get_db),
                             user=Depends(require_role("viewer"))):
    res, sid = _done_results(db, sid)
    sim = db.get(Simulation, sid)
    inc = db.get(Incident, sim.incident_id) if sim else None
    inun = res.get("inundation", {})
    return {
        "simulation_id": sid,
        "incident_name": inc.name if inc else "Dam Break Scenario",
        "coordinates": {"lat": inc.lat if inc else 30.48, "lon": inc.lon if inc else 79.72},
        "target_satellites": ["Copernicus Sentinel-1 SAR GRD (IW/VV)", "Copernicus Sentinel-2 MSI", "Copernicus GLO-30 DEM"],
        "sar_spec": {
            "polarization": "VV",
            "backscatter_threshold_db": -16.0,
            "change_detection_delta_db": -2.5,
            "slope_mask_deg": 6.0,
            "baseline_composite_days": 30
        },
        "model_extent_km2": inun.get("max_area_km2", 0.0),
        "corridor_km": inun.get("corridor_km", 0.0),
        "gee_code_editor_url": "https://code.earthengine.google.com/",
        "open_source_data_notice": "Open-access Copernicus data via ESA & Google Earth Engine catalog"
    }

