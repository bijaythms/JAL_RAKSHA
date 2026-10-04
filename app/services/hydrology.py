"""Upstream inflow hydrology.

  1. SCS Curve Number runoff (NRCS NEH-4 / NEH Part 630):
       S = 25400/CN - 254 [mm]; Ia = 0.2 S; Q = (P-Ia)^2/(P+0.8S)
  2. SCS triangular unit hydrograph (NEH-4 Ch. 16):
       Tp = dt/2 + 0.6 Tc; Qp = 2.08 A Qr / Tp; Tb = 2.67 Tp
  3. USGS NWIS instantaneous values (observed gauge discharge, USA only).

CN table values below follow NEH-4 Table 2-2 for HYDROLOGIC SOIL GROUP B
(fair hydrologic condition unless noted); group noted per row. [VERIFY
against the primary table for your site's HSG before operational use.]
"""
import math
from datetime import datetime, timedelta, timezone
import httpx

USGS_IV_URL = "https://waterservices.usgs.gov/nwis/iv"

# NEH-4 Table 2-2 subset, HSG B, fair condition unless noted
CN_TABLE = {
    # landcover: {condition: (CN_B, CN_C, CN_D)}  — B shown by default in suggest
    "woodland/forest":   {"good": 55, "fair": 60, "poor": 66},
    "meadow/pasture":    {"good": 49, "fair": 61, "poor": 71},
    "row crops":         {"good": 67, "fair": 78, "poor": 85},
    "fallow/bare":       {"good": 74, "fair": 82, "poor": 88},
    "urban/residential": {"good": 72, "fair": 81, "poor": 88},
}
AMC_FACTOR = {"dry": 0.87, "average": 1.0, "wet": 1.13}


def scs_runoff_mm(rainfall_mm: float, curve_number: float) -> float:
    if not (30.0 <= curve_number < 100.0):
        raise ValueError("Curve number must be in [30, 100)")
    S = 25400.0 / curve_number - 254.0
    Ia = 0.2 * S
    if rainfall_mm <= Ia:
        return 0.0
    return (rainfall_mm - Ia) ** 2 / (rainfall_mm + 0.8 * S)


def scs_unit_hydrograph(catchment_km2, runoff_mm, tc_hr, dt_hr=0.25):
    if catchment_km2 <= 0 or tc_hr <= 0:
        raise ValueError("catchment area and Tc must be positive")
    Tp = dt_hr / 2.0 + 0.6 * tc_hr
    Tb = 2.67 * Tp
    Qp = 2.08 * catchment_km2 * runoff_mm / Tp
    t, q, cur = [], [], 0.0
    while cur <= Tb:
        q_i = Qp * (cur / Tp) if cur <= Tp else \
              Qp * max(0.0, (Tb - cur) / (Tb - Tp))
        t.append(round(cur, 3)); q.append(round(q_i, 3))
        cur += dt_hr
    return t, q


def model_inflow(catchment_km2, rainfall_mm, curve_number, tc_hr,
                 amc="average", baseflow_m3s=0.0):
    cn_eff = min(99.0, curve_number * AMC_FACTOR.get(amc, 1.0))
    runoff_mm = scs_runoff_mm(rainfall_mm, cn_eff)
    t, q_uh = scs_unit_hydrograph(catchment_km2, runoff_mm, tc_hr)
    q = [baseflow_m3s + qi for qi in q_uh]
    return {
        "method": "SCS Curve Number + SCS triangular unit hydrograph",
        "citations": ["NRCS National Engineering Handbook Part 630, "
                      "Ch. 9-11 (formerly NEH-4, 1972)"],
        "inputs": {"catchment_km2": catchment_km2, "rainfall_mm": rainfall_mm,
                   "curve_number": round(cn_eff, 1), "tc_hr": tc_hr, "amc": amc},
        "runoff_mm": round(runoff_mm, 2),
        "volume_m3": round(runoff_mm / 1000.0 * catchment_km2 * 1e6, 0),
        "peak_inflow_m3s": round(max(q), 1),
        "t_hr": t, "q_m3s": q,
        "limitations": [
            "SCS-CN was developed for US agricultural catchments; Himalayan "
            "snow/glacier-melt basins are outside its calibration domain.",
            "No snowmelt, channel routing or baseflow recession components."],
    }


def suggest_cn(landcover, condition="fair"):
    if landcover not in CN_TABLE:
        raise ValueError(f"landcover must be one of {list(CN_TABLE)}")
    return CN_TABLE[landcover][condition]


async def fetch_usgs_gauge(site_id, days=7, parameter="00060"):
    """USGS NWIS observed discharge (USA only). 00060 = ft3/s."""
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    params = {"format": "json", "sites": site_id, "parameterCd": parameter,
              "startDT": start.strftime("%Y-%m-%d"),
              "endDT": end.strftime("%Y-%m-%d"), "siteStatus": "all"}
    try:
        async with httpx.AsyncClient(timeout=30) as cl:
            r = await cl.get(USGS_IV_URL, params=params)
            r.raise_for_status()
            data = r.json()
        ts = data["value"]["timeSeries"]
        if not ts:
            return {"ok": False, "error": "No data for this site/parameter"}
        vals = [(v["dateTime"], float(v["value"]))
                for v in ts[0]["values"][0]["value"] if v["value"] != "-999999"]
        q = [v for _, v in vals]
        return {"ok": True, "site": site_id, "n": len(vals),
                "discharge_cms": [round(v * 0.0283168, 2) for v in q],
                "mean_cms": round(sum(q)/len(q) * 0.0283168, 2) if q else None,
                "max_cms": round(max(q) * 0.0283168, 2) if q else None,
                "note": "ft3/s -> m3/s (x0.0283168). USGS NWIS is USA-only; "
                        "use modelled inflow elsewhere."}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def constant_inflow_from_gauge(gauge):
    return gauge.get("mean_cms") or 0.0
