"""India-wide regionalization: 8 physiographic presets, auto-selected by
lat/lon. Order-of-magnitude literature values, NOT site calibrations.
Snowmelt: temperature-index degree-day (Hock 2003 simplified)."""
import math
from dataclasses import dataclass, asdict


@dataclass
class RegionPreset:
    key: str
    name: str
    valley_width_m: float
    bed_slope: float
    manning_n: float
    spreading_factor: float
    base_flow_m3s: float
    material_prior: str
    dam_height_typical_m: float
    breach_time_typical_hr: float
    inflow_mode: str
    design_storm_24h_mm: float
    curve_number: float
    tc_hr_per_100km2: float
    ddf_mm_per_deg_day: float
    mobilization_min: float
    population_density_km2: int
    notes: str = ""


_WESTERN_HIMALAYA = RegionPreset(
    key="western_himalaya", name="Western Himalaya (J&K, HP, Uttarakhand)",
    valley_width_m=60, bed_slope=0.035, manning_n=0.050, spreading_factor=2.0,
    base_flow_m3s=40, material_prior="Ice/debris",
    dam_height_typical_m=35, breach_time_typical_hr=1.0,
    inflow_mode="both", design_storm_24h_mm=120, curve_number=74,
    tc_hr_per_100km2=0.5, ddf_mm_per_deg_day=5.0,
    mobilization_min=45, population_density_km2=120,
    notes="GLOF + landslide-dam belt. Debris bulking risk highest in India.")
_EASTERN_HIMALAYA = RegionPreset(
    key="eastern_himalaya", name="Eastern Himalaya (Sikkim, Arunachal, Darjeeling)",
    valley_width_m=70, bed_slope=0.030, manning_n=0.048, spreading_factor=2.2,
    base_flow_m3s=80, material_prior="Ice/debris",
    dam_height_typical_m=30, breach_time_typical_hr=0.8,
    inflow_mode="both", design_storm_24h_mm=180, curve_number=78,
    tc_hr_per_100km2=0.6, ddf_mm_per_deg_day=5.5,
    mobilization_min=40, population_density_km2=90,
    notes="Highest GLOF density in India. Rain-on-snow produces fastest breaches.")
_NE_HILLS = RegionPreset(
    key="ne_hills", name="NE Hills (Meghalaya, Mizoram, Manipur, Nagaland)",
    valley_width_m=50, bed_slope=0.025, manning_n=0.055, spreading_factor=2.0,
    base_flow_m3s=60, material_prior="Landslide debris",
    dam_height_typical_m=25, breach_time_typical_hr=1.2,
    inflow_mode="monsoon", design_storm_24h_mm=220, curve_number=80,
    tc_hr_per_100km2=0.7, ddf_mm_per_deg_day=0.0,
    mobilization_min=35, population_density_km2=130,
    notes="World-record rainfall belt; landslide dams form and fail within "
          "a single monsoon.")
_WESTERN_GHATS = RegionPreset(
    key="western_ghats", name="Western Ghats (Maharashtra, Kerala, Karnataka coast)",
    valley_width_m=45, bed_slope=0.020, manning_n=0.045, spreading_factor=2.4,
    base_flow_m3s=50, material_prior="Landslide debris",
    dam_height_typical_m=20, breach_time_typical_hr=1.5,
    inflow_mode="monsoon", design_storm_24h_mm=250, curve_number=76,
    tc_hr_per_100km2=0.6, ddf_mm_per_deg_day=0.0,
    mobilization_min=30, population_density_km2=350,
    notes="Monsoon landslide dams + tank failures. Dense downstream population.")
_PENINSULAR = RegionPreset(
    key="peninsular", name="Deccan Plateau & Peninsular India",
    valley_width_m=120, bed_slope=0.004, manning_n=0.035, spreading_factor=3.0,
    base_flow_m3s=30, material_prior="Earth",
    dam_height_typical_m=25, breach_time_typical_hr=3.0,
    inflow_mode="monsoon", design_storm_24h_mm=100, curve_number=72,
    tc_hr_per_100km2=1.0, ddf_mm_per_deg_day=0.0,
    mobilization_min=60, population_density_km2=300,
    notes="Earthen tanks and irrigation dams. Flat: wider, slower floods.")
_GANGETIC = RegionPreset(
    key="gangetic", name="Indo-Gangetic Plains",
    valley_width_m=300, bed_slope=0.0008, manning_n=0.030, spreading_factor=3.5,
    base_flow_m3s=150, material_prior="Earth",
    dam_height_typical_m=15, breach_time_typical_hr=6.0,
    inflow_mode="monsoon", design_storm_24h_mm=130, curve_number=78,
    tc_hr_per_100km2=1.5, ddf_mm_per_deg_day=0.0,
    mobilization_min=90, population_density_km2=900,
    notes="Embankment breaches. Huge areas, slow arrival, hard mobilization.")
_ARID = RegionPreset(
    key="arid", name="Arid West (Rajasthan, Kachchh)",
    valley_width_m=100, bed_slope=0.006, manning_n=0.035, spreading_factor=3.0,
    base_flow_m3s=10, material_prior="Earth",
    dam_height_typical_m=20, breach_time_typical_hr=4.0,
    inflow_mode="monsoon", design_storm_24h_mm=70, curve_number=68,
    tc_hr_per_100km2=1.2, ddf_mm_per_deg_day=0.0,
    mobilization_min=75, population_density_km2=150,
    notes="Flashy rare storms on tanks; desiccation cracking => piping-prone.")
_COASTAL = RegionPreset(
    key="coastal", name="Coastal Deltas (Odisha, AP, Bengal, TN)",
    valley_width_m=400, bed_slope=0.0005, manning_n=0.030, spreading_factor=3.5,
    base_flow_m3s=200, material_prior="Earth",
    dam_height_typical_m=10, breach_time_typical_hr=8.0,
    inflow_mode="monsoon", design_storm_24h_mm=200, curve_number=80,
    tc_hr_per_100km2=2.0, ddf_mm_per_deg_day=0.0,
    mobilization_min=120, population_density_km2=700,
    notes="Embankment/cyclone compound flooding; plan shelters, not routes.")


def _poly(*coords):
    return [list(c) for c in coords]

# Order matters: Himalaya/NE first, plains/arid/coastal fallbacks last.
# Gangetic polygon extended west to lon 76.0 above lat 27.5 (Delhi fix).
_REGIONS = [
    (_poly((36.5, 73.5), (36.5, 80.5), (32.5, 80.2), (30.2, 80.3),
           (30.2, 77.8), (32.0, 73.8), (35.0, 73.5)), _WESTERN_HIMALAYA),
    (_poly((28.3, 88.0), (28.3, 97.5), (26.0, 97.0), (26.5, 92.0),
           (26.8, 88.4)), _EASTERN_HIMALAYA),
    (_poly((26.5, 88.0), (26.3, 95.5), (21.8, 93.5), (21.5, 90.5),
           (23.5, 89.5)), _NE_HILLS),
    (_poly((21.5, 72.5), (20.0, 76.0), (12.5, 76.2), (8.2, 77.2),
           (16.0, 73.6), (20.5, 72.6)), _WESTERN_GHATS),
    (_poly((30.2, 77.8), (30.5, 80.3), (29.0, 80.0), (27.5, 84.0),
           (23.0, 88.0), (21.5, 88.5), (24.5, 79.0), (27.5, 77.0),
           (27.5, 76.0)), _GANGETIC),
    (_poly((28.5, 73.0), (27.5, 76.0), (27.5, 77.0), (24.0, 78.5),
           (22.0, 74.0), (24.5, 71.0), (27.5, 70.5)), _ARID),
    (_poly((22.0, 86.0), (21.0, 88.5), (15.0, 88.0), (10.0, 80.0),
           (13.5, 77.0), (17.0, 82.0), (19.0, 84.3), (21.0, 86.2)), _COASTAL),
    (_poly((24.5, 71.0), (24.0, 78.5), (17.0, 78.5), (12.0, 76.0),
           (16.0, 73.6), (20.5, 72.6)), _PENINSULAR),
]

INDIA_BBOX = (6.5, 68.0, 37.5, 97.5)
_REGION_OVERRIDES = {}      # admin corrections: (lat,lon) -> preset


def _point_in_poly(lat, lon, poly):
    inside = False
    n = len(poly)
    for i in range(n):
        la1, lo1 = poly[i]
        la2, lo2 = poly[(i + 1) % n]
        if (la1 > lat) != (la2 > lat):
            lon_int = (lo2 - lo1) * (lat - la1) / (la2 - la1) + lo1
            if lon < lon_int:
                inside = not inside
    return inside


def region_for(lat, lon):
    key = _REGION_OVERRIDES.get((round(lat, 3), round(lon, 3)))
    if key:
        for _, p in _REGIONS:
            if p.key == key:
                return p
    in_india = (INDIA_BBOX[0] <= lat <= INDIA_BBOX[2] and
                INDIA_BBOX[1] <= lon <= INDIA_BBOX[3])
    for poly, preset in _REGIONS:
        if _point_in_poly(lat, lon, poly):
            out = RegionPreset(**asdict(preset))
            if not in_india:
                out.notes = ("WARNING: outside the India bounding box - "
                             "preset is nearest-analogy only. " + out.notes)
            return out
    if in_india:
        if lat > 28:
            return _EASTERN_HIMALAYA if lon > 84 else _WESTERN_HIMALAYA
        if lon < 74.5:
            return _ARID
        return _PENINSULAR
    return _PENINSULAR


def set_override(lat, lon, region_key):
    valid = {p.key for _, p in _REGIONS}
    if region_key not in valid:
        raise ValueError(f"region must be one of {sorted(valid)}")
    _REGION_OVERRIDES[(round(lat, 3), round(lon, 3))] = region_key
    return True


def clear_override(lat, lon):
    key = (round(lat, 3), round(lon, 3))
    if key in _REGION_OVERRIDES:
        del _REGION_OVERRIDES[key]
        return True
    return False


def snowmelt_inflow(catchment_km2, t_mean_c, ddf=5.0, t0=0.0,
                    rain_on_snow_mm=0.0, cn=74.0):
    if t_mean_c <= t0:
        melt_mm = 0.0
    else:
        melt_mm = ddf * (t_mean_c - t0)
    rain_runoff_mm = 0.0
    if rain_on_snow_mm > 0:
        from .hydrology import scs_runoff_mm
        rain_runoff_mm = scs_runoff_mm(rain_on_snow_mm, cn)
    total_mm = melt_mm + rain_runoff_mm
    q_m3s = total_mm / 1000.0 * catchment_km2 * 1e6 / 86400.0
    return {"method": "Temperature-index degree-day melt (Hock 2003, "
                      "simplified) + SCS-CN rain-on-snow",
            "t_mean_c": t_mean_c, "ddf_mm_per_deg_day": ddf,
            "melt_mm_day": round(melt_mm, 1),
            "rain_on_snow_runoff_mm": round(rain_runoff_mm, 1),
            "inflow_m3s": round(q_m3s, 1),
            "limitations": [
                "Degree-day model ignores aspect/altitude distribution.",
                "Assumes uniform catchment melt."]}


# National scenario library: (name, lat, lon, _, V m3, H m, type)
NATIONAL_SCENARIO_SITES = [
    ("Tehri Dam (worst-case breach)", 30.38, 78.48, None, 3.5e9, 260, "Earth"),
    ("Lakhwar Dam (under construction)", 30.45, 77.85, None, 3.3e8, 192, "Earth"),
    ("South Lhonak Lake (Sikkim GLOF)", 27.94, 88.13, None, 6.5e7, 60, "Ice/debris"),
    ("Gya Lake complex (Ladakh)", 32.95, 77.62, None, 3.0e6, 25, "Ice/debris"),
    ("Pareechu temporary lake (Spiti)", 31.95, 78.58, None, 8.0e6, 35, "Landslide debris"),
    ("Rishiganga landslide dam (Chamoli)", 30.48, 79.72, None, 5.0e6, 38, "Ice/debris"),
    ("Dhauliganga gorge blockage", 30.35, 80.05, None, 4.0e6, 30, "Landslide debris"),
    ("Hirakud Dam (Odisha)", 21.53, 83.75, None, 8.1e9, 60, "Earth"),
    ("Mullaperiyar Dam (Kerala)", 9.54, 77.14, None, 4.4e8, 53, "Masonry"),
    ("Idukki Dam (Kerala)", 9.85, 76.98, None, 2.0e9, 169, "Concrete"),
    ("Sardar Sarovar (Gujarat)", 21.83, 73.75, None, 9.5e9, 163, "Concrete"),
    ("Nagarjuna Sagar (Telangana/AP)", 16.57, 79.31, None, 1.2e10, 124, "Masonry"),
    ("Mettur Dam (Tamil Nadu)", 11.80, 77.80, None, 2.6e9, 65, "Earth"),
    ("Tungabhadra Dam (Karnataka)", 15.26, 76.36, None, 3.7e9, 50, "Earth"),
    ("Umiam Dam (Meghalaya)", 25.60, 91.90, None, 1.6e8, 40, "Earth"),
    ("Kosi embankment breach point (Bihar)", 26.15, 86.90, None, 2.0e8, 8, "Earth"),
]

_MATERIAL_MAP = {"Earth/Rockfill": "Earth"}
_VALID = ("Earth", "Rock", "Landslide debris", "Sediment", "Ice/debris",
          "Mixed", "Unknown", "Concrete", "Masonry")


def national_scenario_params(site, breach_fraction=0.5):
    name, lat, lon, _, V, H, mat = site
    preset = region_for(lat, lon)
    mat = _MATERIAL_MAP.get(mat, mat if mat in _VALID else preset.material_prior)
    A = max(V / (0.6 * H), 1e4)
    return {
        "name": name, "lat": lat, "lon": lon,
        "region": preset.key, "region_name": preset.name,
        "params": {
            "stored_volume_m3": V, "lake_area_m2": round(A, 0),
            "dam_height_m": H,
            "dam_crest_len_m": max(preset.valley_width_m * 1.2, 60.0),
            "dam_material": mat, "scenario": "major",
            "breach_width_m": max(preset.valley_width_m * breach_fraction, 15.0),
            "breach_depth_m": round(H * 0.75, 1),
            "breach_time_hr": preset.breach_time_typical_hr,
            "inflow_m3s": preset.base_flow_m3s,
            "valley_width_m": preset.valley_width_m,
            "bed_slope": preset.bed_slope,
            "manning_n": preset.manning_n,
            "spreading_factor": preset.spreading_factor,
            "base_flow_m3s": preset.base_flow_m3s,
            "with_uncertainty": False},
        "mobilization_min": preset.mobilization_min,
        "preset_notes": preset.notes}
