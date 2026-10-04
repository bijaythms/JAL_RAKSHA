from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from ..security import require_role
from ..services import erosion_params
from ..services.erosion_params import KD_BY_MATERIAL

router = APIRouter(prefix="/api", tags=["calibration"])

class ErosionParamIn(BaseModel):
    material: str
    k_d: float = Field(gt=1e-9, lt=1e-3, description="Detachability coeff m3/(N.s)")
    tau_c: float = Field(gt=0.1, lt=1000, description="Critical shear stress Pa")
    source: Optional[str] = "user-calibrated"

@router.get("/incidents/{iid}/erosion-params")
def get_erosion_params(iid: str, user=Depends(require_role("viewer"))):
    return {"incident_id": iid, "calibrations": erosion_params.list_calibrations(iid),
            "note": "Flagged entries use literature order-of-magnitude values "
                    "(Hanson & Temple 1997). Provide lab-measured k_d and tau_c "
                    "for site-specific accuracy."}

@router.put("/incidents/{iid}/erosion-params")
def set_erosion_params(iid: str, body: ErosionParamIn,
                       user=Depends(require_role("analyst"))):
    if body.material not in KD_BY_MATERIAL:
        raise HTTPException(400, f"Unknown material. Valid: {list(KD_BY_MATERIAL)}")
    return erosion_params.set_params(iid, body.material, body.k_d, body.tau_c,
                                     body.source or "user-calibrated")

@router.delete("/incidents/{iid}/erosion-params/{material}")
def delete_erosion_param(iid: str, material: str,
                         user=Depends(require_role("analyst"))):
    removed = erosion_params.delete_params(iid, material)
    return {"ok": True, "removed": removed, "reverted_to": "literature"}
