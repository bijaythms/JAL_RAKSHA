"""
Dams API Router.
Provides search, filtering, and 1-click activation/incident-sync
for all 60+ major dams across India.
"""

import json
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..db import SessionLocal, Incident, new_id
from ..security import require_role, audit
from ..services import major_dams, india
from ..services.geo import destination
from ..services.dem_flow_router import trace_dambreak_valley_dem

router = APIRouter(prefix="/api/dams", tags=["dams"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("")
def list_dams(
    q: Optional[str] = Query(None, description="Search by dam name, river, state, or notes"),
    state: Optional[str] = Query(None, description="Filter by state name"),
    region: Optional[str] = Query(None, description="Filter by physiographic region"),
    material: Optional[str] = Query(None, description="Filter by dam material (Earth, Concrete, etc.)"),
    user=Depends(require_role("viewer"))
):
    """Return all matching major dams in India with full technical parameters."""
    dams = major_dams.get_major_dams(q=q, state=state, region=region, material=material)
    return {
        "total": len(dams),
        "items": dams
    }


@router.get("/{dam_id}")
def get_dam(dam_id: str, user=Depends(require_role("viewer"))):
    """Retrieve detailed profile for a specific major dam."""
    dam = major_dams.get_dam_by_id(dam_id)
    if not dam:
        raise HTTPException(404, f"Dam with ID '{dam_id}' not found")
    return dam


@router.post("/{dam_id}/activate")
def activate_dam_as_incident(dam_id: str, db: Session = Depends(get_db), user=Depends(require_role("viewer"))):
    """
    Ensure the selected major dam exists as an Incident in the database
    with its downstream corridor pre-computed, and return its Incident ID.
    """
    dam = major_dams.get_dam_by_id(dam_id)
    if not dam:
        raise HTTPException(404, f"Dam with ID '{dam_id}' not found")

    # Check if incident already exists with this name or dam_id tag
    inc_name = f"[MAJOR DAM] {dam['name']} ({dam['state']})"
    existing = db.query(Incident).filter(Incident.name == inc_name).first()

    # Generate DEM-derived downstream river valley flow corridor
    bearing = dam.get("bearing_deg", 130.0)
    pts = trace_dambreak_valley_dem(dam["lat"], dam["lon"], initial_bearing=bearing, total_km=20.0, dam_name=dam["name"])

    if existing:
        existing.lat = dam["lat"]
        existing.lon = dam["lon"]
        existing.centerline = json.dumps(pts)
        db.commit()
        return {
            "ok": True,
            "incident_id": existing.id,
            "name": existing.name,
            "lat": existing.lat,
            "lon": existing.lon,
            "already_existed": True,
            "dam": dam
        }

    reg = india.region_for(dam["lat"], dam["lon"]).name
    inc_id = new_id("JR")
    new_inc = Incident(
        id=inc_id,
        name=inc_name,
        incident_type="Natural Dam",
        river_name=dam["river"],
        lat=dam["lat"],
        lon=dam["lon"],
        region=reg,
        status="ACTIVE_MONITORING",
        created_by=user.get("sub", "analyst") if isinstance(user, dict) else "analyst",
        centerline=json.dumps(pts)
    )
    db.add(new_inc)
    db.commit()

    return {
        "ok": True,
        "incident_id": inc_id,
        "name": inc_name,
        "lat": dam["lat"],
        "lon": dam["lon"],
        "already_existed": False,
        "dam": dam
    }


@router.post("/sync-all")
def sync_all_dams(db: Session = Depends(get_db), user=Depends(require_role("analyst"))):
    """
    Seed/sync all 60+ major dams into the Incidents registry
    so they appear seamlessly across the entire application with accurate GPS coordinates.
    """
    created_count = 0
    updated_count = 0

    for dam in major_dams.MAJOR_DAMS:
        inc_name = f"[MAJOR DAM] {dam['name']} ({dam['state']})"
        existing = db.query(Incident).filter(Incident.name == inc_name).first()

        # Generate DEM-derived downstream river valley flow corridor
        bearing = dam.get("bearing_deg", 130.0)
        pts = trace_dambreak_valley_dem(dam["lat"], dam["lon"], initial_bearing=bearing, total_km=20.0, dam_name=dam["name"])

        if existing:
            existing.lat = dam["lat"]
            existing.lon = dam["lon"]
            existing.centerline = json.dumps(pts)
            updated_count += 1
            continue

        reg = india.region_for(dam["lat"], dam["lon"]).name
        inc_id = new_id("JR")
        new_inc = Incident(
            id=inc_id,
            name=inc_name,
            incident_type="Natural Dam",
            river_name=dam["river"],
            lat=dam["lat"],
            lon=dam["lon"],
            region=reg,
            status="ACTIVE_MONITORING",
            created_by="system:seed",
            centerline=json.dumps(pts)
        )
        db.add(new_inc)
        created_count += 1

    db.commit()
    return {
        "ok": True,
        "created": created_count,
        "updated": updated_count,
        "total": len(major_dams.MAJOR_DAMS)
    }
