from typing import Optional, List, Literal
from pydantic import BaseModel, Field

BreachScenario = Literal["minor", "moderate", "major", "full"]
DamMaterial = Literal["Earth", "Rock", "Landslide debris", "Sediment",
                      "Ice/debris", "Mixed", "Unknown", "Concrete", "Masonry"]

class LoginIn(BaseModel):
    username: str
    password: str

class PasswordChange(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8)

class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64,
                          pattern=r"^[a-zA-Z0-9_.-]+$")
    password: str = Field(min_length=8)
    role: Literal["viewer", "reporter", "analyst", "admin"]

class IncidentIn(BaseModel):
    name: str = Field(min_length=3, max_length=200)
    incident_type: Literal["Natural Dam", "Landslide Dam", "Temporary Lake",
                           "River Blockage", "Manual Scenario"] = "Landslide Dam"
    river_name: str = ""
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    region: str = ""

class IncidentPatch(BaseModel):
    name: Optional[str] = Field(default=None, min_length=3, max_length=200)
    status: Optional[Literal["NEW_ANALYSIS", "ACTIVE_MONITORING", "ELEVATED_ALERT",
                             "SURVEILLANCE_ACTIVE", "CLOSED", "MANUAL_RUN",
                             "NATIONAL_EXERCISE"]] = None
    river_name: Optional[str] = None
    lat: Optional[float] = Field(default=None, ge=-90, le=90)
    lon: Optional[float] = Field(default=None, ge=-180, le=180)

class CenterlineIn(BaseModel):
    centerline: List[List[float]]

class BreachParams(BaseModel):
    stored_volume_m3: float = Field(gt=100, le=1e11)
    lake_area_m2: float = Field(gt=100)
    dam_height_m: float = Field(gt=0.5, le=400)
    dam_crest_len_m: float = Field(gt=2, le=3000)
    dam_material: DamMaterial = "Landslide debris"
    scenario: BreachScenario = "major"
    breach_width_m: float = Field(gt=1, le=600)
    breach_depth_m: float = Field(gt=0.5, le=400)
    breach_time_hr: float = Field(gt=0.02, le=24)
    inflow_m3s: float = Field(ge=0, le=2e5)
    valley_width_m: float = Field(gt=5, le=3000, default=90)
    bed_slope: float = Field(gt=0.0001, le=0.6, default=0.02)
    manning_n: float = Field(gt=0.01, le=0.2, default=0.045)
    spreading_factor: float = Field(gt=0.2, le=10, default=2.5)
    base_flow_m3s: float = Field(ge=0, default=50)
    with_uncertainty: bool = True
    debris_bulking_factor: float = Field(default=1.0, ge=1.0, le=15.0)

class ManualRunIn(BaseModel):
    name: str = Field(default="Manual run", min_length=3, max_length=120)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    stored_volume_m3: float = Field(gt=100, le=1e11)
    dam_height_m: float = Field(gt=0.5, le=400)
    dam_material: Optional[DamMaterial] = None
    scenario: BreachScenario = "major"
    lake_area_m2: Optional[float] = Field(default=None, gt=100)
    dam_crest_len_m: Optional[float] = Field(default=None, gt=2, le=3000)
    breach_width_m: Optional[float] = Field(default=None, gt=1, le=600)
    breach_depth_m: Optional[float] = Field(default=None, gt=0.5, le=400)
    breach_time_hr: Optional[float] = Field(default=None, gt=0.02, le=24)
    inflow_m3s: Optional[float] = Field(default=None, ge=0, le=2e5)
    valley_width_m: Optional[float] = Field(default=None, gt=5, le=3000)
    bed_slope: Optional[float] = Field(default=None, gt=0.0001, le=0.6)
    manning_n: Optional[float] = Field(default=None, gt=0.01, le=0.2)
    spreading_factor: Optional[float] = Field(default=None, gt=0.2, le=10)
    base_flow_m3s: Optional[float] = Field(default=None, ge=0, le=1e4)
    with_uncertainty: bool = True
    auto_bearing_deg: Optional[float] = Field(default=None, ge=0, le=360)
    auto_length_km: float = Field(default=10.0, ge=1, le=100)
    debris_bulking_factor: float = Field(default=1.0, ge=1.0, le=15.0)

class DamageFormIn(BaseModel):
    incident_id: str
    lat: float; lon: float
    incident_type: str = "Flood"
    water_depth_m: float = Field(ge=0, le=100, default=0.5)
    damage_description: str = Field(min_length=5, max_length=2000)
    infrastructure_damage: str = ""
    reporter_name: str = "Anonymous"

class VerifyIn(BaseModel):
    status: Literal["VERIFIED", "REJECTED"]

class ZoneIn(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    lat1: float; lon1: float; lat2: float; lon2: float
    lookback_days: int = Field(default=30, ge=1, le=365)
    scan_interval_hr: int = Field(default=12, ge=1, le=336)

class RoiIn(BaseModel):
    polygon: List[List[float]] = Field(min_length=3, max_length=200)

class BufferIn(BaseModel):
    river_buffer_m: float = Field(ge=50, le=2000, default=300)
