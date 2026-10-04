"""
FastFlood 2D Inundation & Visualization Router.
Exposes high-resolution 2D inundation maps, NDMA risk classification,
and interactive Google/ESRI maps based on the hackathon FastFlood model.
"""

import os
import json
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from ..db import SessionLocal, Incident, Simulation
from ..security import require_role
from ..services.fastflood_dam_break import simulate_dam_break_fastflood

router = APIRouter(prefix="/api", tags=["fastflood"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

HTML_CACHE_DIR = Path("data/fastflood_maps")
HTML_CACHE_DIR.mkdir(parents=True, exist_ok=True)


@router.get("/simulations/{sim_id}/fastflood")
def get_simulation_fastflood(sim_id: str, db: Session = Depends(get_db), user=Depends(require_role("viewer"))):
    """
    Generate or return the high-resolution FastFlood 2D inundation and risk raster
    for a completed simulation.
    """
    sim = db.get(Simulation, sim_id)
    if not sim:
        raise HTTPException(404, "Simulation not found")
    if sim.status != "DONE" or not sim.results:
        raise HTTPException(400, "Simulation has not finished yet")

    results = json.loads(sim.results)
    params = json.loads(sim.params)
    inc = db.get(Incident, sim.incident_id)
    if not inc:
        raise HTTPException(404, "Incident associated with simulation not found")

    centerline = json.loads(inc.centerline or "[]")
    breach = results.get("breach", {})
    peak_q = breach.get("peak_Q_m3s") or breach.get("peak_discharge_m3s") or 1500.0

    html_file = HTML_CACHE_DIR / f"{sim_id}_fastflood.html"

    ff_res = simulate_dam_break_fastflood(
        dam_lat=inc.lat,
        dam_lon=inc.lon,
        centerline=centerline,
        peak_Q_m3s=peak_q,
        stored_volume_m3=params.get("stored_volume_m3", 5e6),
        dam_height_m=params.get("dam_height_m", 30.0),
        valley_width_m=params.get("valley_width_m", 90.0),
        bed_slope=params.get("bed_slope", 0.02),
        manning_n=params.get("manning_n", 0.045),
        debris_bulking=params.get("debris_bulking_factor", 1.0),
        dam_name=inc.name,
        output_html_path=str(html_file)
    )

    ff_res["interactive_html_url"] = f"/api/simulations/{sim_id}/fastflood/html"
    return ff_res


@router.get("/simulations/{sim_id}/fastflood/html")
def get_simulation_fastflood_html(sim_id: str, db: Session = Depends(get_db)):
    """
    Serve the standalone interactive FastFlood HTML map
    (Google Hybrid + ESRI World Imagery + NDMA Risk + Pixel Inspector).
    """
    html_file = HTML_CACHE_DIR / f"{sim_id}_fastflood.html"
    if not html_file.exists():
        # Trigger generation
        sim = db.get(Simulation, sim_id)
        if not sim or sim.status != "DONE":
            raise HTTPException(404, "Simulation not ready or not found")
        get_simulation_fastflood(sim_id, db=db, user={"sub": "viewer"})

    if not html_file.exists():
        raise HTTPException(500, "Failed to generate interactive map")

    return Response(content=html_file.read_text(encoding="utf-8"), media_type="text/html")


@router.post("/incidents/{iid}/fastflood-preview")
def preview_incident_fastflood(iid: str, db: Session = Depends(get_db), user=Depends(require_role("viewer"))):
    """
    Instant 2D FastFlood inundation preview for any incident or major dam,
    even before running a full multi-stage simulation.
    """
    inc = db.get(Incident, iid)
    if not inc:
        raise HTTPException(404, "Incident not found")

    centerline = json.loads(inc.centerline or "[]")
    if len(centerline) < 2:
        raise HTTPException(422, "Incident requires a downstream centerline")

    html_file = HTML_CACHE_DIR / f"preview_{iid}_fastflood.html"

    # Default reasonable dam break peak Q based on location or default
    peak_q = 2200.0

    ff_res = simulate_dam_break_fastflood(
        dam_lat=inc.lat,
        dam_lon=inc.lon,
        centerline=centerline,
        peak_Q_m3s=peak_q,
        stored_volume_m3=1e7,
        dam_height_m=35.0,
        dam_name=inc.name,
        output_html_path=str(html_file)
    )
    ff_res["interactive_html_url"] = f"/api/incidents/{iid}/fastflood-preview/html"
    return ff_res


@router.get("/incidents/{iid}/fastflood-preview/html")
def get_incident_fastflood_preview_html(iid: str, db: Session = Depends(get_db)):
    """Serve the interactive HTML preview for an incident."""
    html_file = HTML_CACHE_DIR / f"preview_{iid}_fastflood.html"
    if not html_file.exists():
        preview_incident_fastflood(iid, db=db, user={"sub": "viewer"})

    if not html_file.exists():
        raise HTTPException(500, "Failed to generate interactive preview map")

    return Response(content=html_file.read_text(encoding="utf-8"), media_type="text/html")
