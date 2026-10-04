from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Literal
from ..services import hydrology
from ..security import require_role

router = APIRouter(prefix="/api/hydrology", tags=["hydrology"])

class InflowIn(BaseModel):
    catchment_km2: float = Field(gt=0, le=50000)
    rainfall_mm: float = Field(ge=0, le=1000)
    curve_number: float = Field(ge=30, lt=100)
    tc_hr: float = Field(gt=0.05, le=48)
    amc: Literal["dry", "average", "wet"] = "average"
    baseflow_m3s: float = Field(ge=0, default=0)

@router.post("/inflow")
def inflow(body: InflowIn, user=Depends(require_role("viewer"))):
    return hydrology.model_inflow(**body.model_dump())

@router.get("/cn-table")
def cn_table(user=Depends(require_role("viewer"))):
    return hydrology.CN_TABLE

@router.get("/usgs-gauge/{site_id}")
async def gauge(site_id: str, days: int = 7,
                user=Depends(require_role("viewer"))):
    return await hydrology.fetch_usgs_gauge(site_id, days)

@router.get("/breach-estimates")
def breach_estimates(volume_m3: float, height_m: float,
                     mode: Literal["overtopping", "piping"] = "overtopping",
                     user=Depends(require_role("viewer"))):
    if volume_m3 <= 0 or height_m <= 0:
        raise HTTPException(422, "volume and height must be positive")
    from ..services import breach_models
    return {"peak_Q_ensemble": breach_models.empirical_peak_discharge(
                volume_m3, height_m, mode),
            "breach_geometry": breach_models.empirical_breach_geometry(
                volume_m3, height_m, mode)}
