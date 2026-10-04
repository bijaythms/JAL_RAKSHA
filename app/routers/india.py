import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from ..db import SessionLocal, Incident, Simulation, new_id
from ..security import require_role, audit
from .. import jobs
from ..services import india

router = APIRouter(prefix="/api/india", tags=["india"])

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

@router.get("/region")
def region(lat: float, lon: float, user=Depends(require_role("viewer"))):
    p = india.region_for(lat, lon)
    return p.__dict__

class RegionOverrideIn(BaseModel):
    lat: float
    lon: float
    region_key: Optional[str] = None

@router.put("/region-override")
@router.post("/region-override")
def region_override(body: Optional[RegionOverrideIn] = None,
                    lat: Optional[float] = Query(None),
                    lon: Optional[float] = Query(None),
                    region_key: Optional[str] = Query(None),
                    user=Depends(require_role("analyst"))):
    r_lat = body.lat if body else lat
    r_lon = body.lon if body else lon
    r_key = body.region_key if (body and body.region_key) else region_key
    if r_lat is None or r_lon is None or not r_key:
        raise HTTPException(422, "lat, lon, and region_key are required")
    try:
        india.set_override(r_lat, r_lon, r_key)
        return {"ok": True, "lat": r_lat, "lon": r_lon, "region_key": r_key}
    except ValueError as e:
        raise HTTPException(422, str(e))

@router.delete("/region-override")
def clear_region_override(body: Optional[RegionOverrideIn] = None,
                          lat: Optional[float] = Query(None),
                          lon: Optional[float] = Query(None),
                          user=Depends(require_role("analyst"))):
    r_lat = body.lat if body else lat
    r_lon = body.lon if body else lon
    if r_lat is None or r_lon is None:
        raise HTTPException(422, "lat and lon are required")
    cleared = india.clear_override(r_lat, r_lon)
    return {"ok": True, "cleared": cleared}

@router.get("/sites")
def sites(user=Depends(require_role("viewer"))):
    return [{"name": s[0], "lat": s[1], "lon": s[2], "volume_m3": s[4],
             "height_m": s[5], "material": s[6],
             "region": india.region_for(s[1], s[2]).name}
            for s in india.NATIONAL_SCENARIO_SITES]

class SnowIn(BaseModel):
    catchment_km2: float = Field(gt=0, le=20000)
    t_mean_c: float = Field(ge=-40, le=40)
    rain_on_snow_mm: float = Field(ge=0, le=500, default=0)
    ddf: float = Field(ge=1, le=10, default=5.0)

@router.post("/snowmelt-inflow")
def snowmelt(body: SnowIn, user=Depends(require_role("viewer"))):
    return india.snowmelt_inflow(**body.model_dump())

@router.post("/national-run", status_code=201)
def national_run(db=Depends(get_db), user=Depends(require_role("analyst")),
                 breach_fraction: float = 0.5):
    from ..routers.simulations import _run_pipeline
    from ..schemas import BreachParams
    from ..services.geo import destination
    created = []
    for site in india.NATIONAL_SCENARIO_SITES:
        spec = india.national_scenario_params(site, breach_fraction)
        inc_id = new_id("JR")
        pts = [[spec["lat"], spec["lon"]]]
        for d in range(500, int(10 * 1000) + 1, 500):
            la, lo = destination(spec["lat"], spec["lon"], 120, d)
            pts.append([round(la, 5), round(lo, 5)])
        db.add(Incident(id=inc_id, name=f"[NATIONAL] {spec['name']}",
                        incident_type="Natural Dam", river_name="",
                        lat=spec["lat"], lon=spec["lon"],
                        region=spec["region_name"], status="NATIONAL_EXERCISE",
                        created_by=f"national:{user['sub']}",
                        centerline=json.dumps(pts)))
        db.commit()
        sim = Simulation(id=new_id("SIM"), incident_id=inc_id,
                         label=f"national:{spec['name']}",
                         params=BreachParams(**spec["params"]).model_dump_json(),
                         created_by=user["sub"])
        db.add(sim); db.commit()
        jobs.submit(lambda rec, sid=sim.id: _run_pipeline(sid, rec))
        created.append({"incident": inc_id, "simulation": sim.id,
                        "name": spec["name"]})
    audit(db, user["sub"], "national.run", f"{len(created)} sites")
    db.commit()
    return {"queued": len(created), "items": created,
            "warning": "Placeholder straight centerlines and regional "
                       "presets; no exposure layers - reports show breach/"
                       "inundation only. Replace per site for decision-grade "
                       "runs."}
