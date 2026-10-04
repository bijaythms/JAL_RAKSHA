from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
from ..security import require_role
from ..services import unit_costs

router = APIRouter(prefix="/api/costs", tags=["costs"])

class CostOverrideIn(BaseModel):
    level: str = Field(..., description="'default' | 'region' | 'incident'")
    key: str = Field(..., description="Region key or incident ID, or 'default'")
    building: Optional[float] = Field(None, ge=0)
    crop_per_ha: Optional[float] = Field(None, ge=0)
    livestock_per_head: Optional[float] = Field(None, ge=0)

@router.get("")
def get_all_costs(user=Depends(require_role("viewer"))):
    return unit_costs.all_rates()

@router.get("/resolve")
def resolve_costs(incident_id: Optional[str] = Query(None),
                  region_key: Optional[str] = Query(None),
                  user=Depends(require_role("viewer"))):
    return unit_costs.get_costs(incident_id=incident_id, region_key=region_key)

@router.post("")
def update_costs(body: CostOverrideIn, user=Depends(require_role("analyst"))):
    try:
        updated = unit_costs.set_costs(
            level=body.level,
            key=body.key,
            building=body.building,
            crop_per_ha=body.crop_per_ha,
            livestock_per_head=body.livestock_per_head,
        )
        return {"ok": True, "level": body.level, "key": body.key, "costs": updated}
    except ValueError as e:
        raise HTTPException(400, str(e))
