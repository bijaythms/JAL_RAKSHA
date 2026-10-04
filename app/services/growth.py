"""Growth-rate analysis & alerting.

Metrics: exponential fit r = ln(A_n/A_0)/span [1/d]; T2 = ln2/r [d];
linear surge g = dA/dt [m2/d]; WSE rise [m/d].

Rules (explicit, auditable):
  R1 CONSECUTIVE GROWTH: area up >= 3 consecutive observations
  R2 RAPID DOUBLING: T2 <= 60 d (CRITICAL if <= 30 d), span >= 5 d
  R3 ABSOLUTE SURGE: g >= 20,000 m2/d, both obs >= 10,000 m2
  R4 WSE RISING + VOLUME: WSE rate > 0 and latest volume >= 1e6 m3
  R5 DRAINING: area <= 70% of series max

Levels: CRITICAL / WARNING / WATCH / NONE / DRAINING.
"""
import math
from datetime import timezone
from ..db import SessionLocal, LakeCandidate, LakeObservation

import json
from pathlib import Path

_THRESHOLDS_FILE = Path("data/growth_thresholds.json")

# Default thresholds — edit via set_growth_thresholds() or PUT endpoint.
GROWTH_THRESHOLDS = {
    "MIN_TRUST_AREA_M2":      10_000.0,
    "MIN_SPAN_DAYS":          5.0,
    "R1_MIN_CONSECUTIVE":     3,
    "R2_MAX_DOUBLING_DAYS":   60.0,
    "R2_CRITICAL_DAYS":       30.0,
    "R3_ABS_SURGE_M2_DAY":    20_000.0,
    "R5_DRAIN_FRACTION":      0.30,
    "R4_VOLUME_M3":           1e6,
}

_THRESHOLD_DESCRIPTIONS = {
    "MIN_TRUST_AREA_M2":     "Minimum water-body area [m²] for a detection to be trusted in growth rules.",
    "MIN_SPAN_DAYS":         "Minimum observation span [days] required for rate calculations (R2, R4).",
    "R1_MIN_CONSECUTIVE":    "Number of consecutive area-increasing observations to fire R1.",
    "R2_MAX_DOUBLING_DAYS":  "Doubling time [days] threshold that fires R2 WARNING.",
    "R2_CRITICAL_DAYS":      "Doubling time [days] threshold that escalates R2 to CRITICAL.",
    "R3_ABS_SURGE_M2_DAY":   "Absolute area growth rate [m²/day] threshold for R3 surge.",
    "R5_DRAIN_FRACTION":     "Fraction below series peak area that triggers R5 DRAINING (e.g. 0.30 = 70% of peak).",
    "R4_VOLUME_M3":          "Minimum latest volume [m³] required (alongside positive WSE rate) for R4.",
}

def _load_thresholds():
    if _THRESHOLDS_FILE.exists():
        try:
            overrides = json.loads(_THRESHOLDS_FILE.read_text())
            for k, v in overrides.items():
                if k in GROWTH_THRESHOLDS:
                    GROWTH_THRESHOLDS[k] = v
        except Exception:
            pass
_load_thresholds()

def get_growth_thresholds() -> dict:
    """Returns current threshold values with descriptions."""
    return {k: {"value": v, "description": _THRESHOLD_DESCRIPTIONS.get(k, "")}
            for k, v in GROWTH_THRESHOLDS.items()}

def set_growth_thresholds(**kwargs):
    """Validate, update live GROWTH_THRESHOLDS dict, and persist to JSON.

    Only keys already in GROWTH_THRESHOLDS are accepted.
    Numeric values must be positive; R1_MIN_CONSECUTIVE must be an int >= 2.
    """
    unknown = set(kwargs) - set(GROWTH_THRESHOLDS)
    if unknown:
        raise ValueError(f"Unknown threshold keys: {unknown}. "
                         f"Valid: {list(GROWTH_THRESHOLDS)}")
    for k, v in kwargs.items():
        if k == "R1_MIN_CONSECUTIVE":
            if not isinstance(v, int) or v < 2:
                raise ValueError("R1_MIN_CONSECUTIVE must be an integer >= 2")
        else:
            if not isinstance(v, (int, float)) or v <= 0:
                raise ValueError(f"{k} must be a positive number, got {v!r}")
        GROWTH_THRESHOLDS[k] = v
    _THRESHOLDS_FILE.parent.mkdir(exist_ok=True)
    _THRESHOLDS_FILE.write_text(json.dumps(GROWTH_THRESHOLDS, indent=2))

# ---------------------------------------------------------------------------
# Compat aliases — internal code still references the old module-level names.
# They are resolved at call-time via the live GROWTH_THRESHOLDS dict.
# ---------------------------------------------------------------------------
def _t(key):
    return GROWTH_THRESHOLDS[key]




def record_observation(db, candidate_id, scene_id, area_m2,
                       wse_m=None, volume_m3=None, observed_at=None):
    """Append or UPDATE (dedup by scene) - uses caller's session."""
    o = db.query(LakeObservation).filter(
        LakeObservation.candidate_id == candidate_id,
        LakeObservation.scene_id == scene_id).first()
    if o:
        o.area_m2 = float(area_m2)
        if wse_m:
            o.wse_m = float(wse_m)
        if volume_m3:
            o.volume_m3 = float(volume_m3)
        db.commit()
        return o.id
    from ..db import utcnow
    o = LakeObservation(candidate_id=candidate_id, scene_id=scene_id,
                        area_m2=float(area_m2),
                        wse_m=float(wse_m) if wse_m else None,
                        volume_m3=float(volume_m3) if volume_m3 else None,
                        observed_at=observed_at or utcnow())
    db.add(o)
    db.commit()
    return o.id


def analyze_growth(candidate_id, db=None):
    """Read-only analysis; accepts an open session (nested-safe)."""
    own = db is None
    db = db or SessionLocal()
    try:
        c = db.query(LakeCandidate).filter(
            LakeCandidate.id == candidate_id).first()
        if not c:
            return {"ok": False, "error": "candidate not found"}
        obs = db.query(LakeObservation).filter(
            LakeObservation.candidate_id == candidate_id
        ).order_by(LakeObservation.observed_at.asc()).all()
        if len(obs) < 2:
            return {"ok": True, "candidate_id": candidate_id,
                    "n_observations": len(obs),
                    "alert": {"level": "NONE", "rules_fired": []},
                    "note": "Need >= 2 observations for growth analysis."}
        series = [{"obs_id": o.id, "scene_id": o.scene_id,
                   "observed_at": o.observed_at.isoformat(),
                   "area_m2": o.area_m2, "wse_m": o.wse_m,
                   "volume_m3": o.volume_m3} for o in obs]
        t0 = obs[0].observed_at
        days = [(o.observed_at - t0).total_seconds() / 86400.0 for o in obs]
        areas = [o.area_m2 for o in obs]
        wse_series = [(o.wse_m, o.volume_m3) for o in obs if o.wse_m is not None]
        metrics, rules = _metrics_and_rules(days, areas, wse_series)
        level = _level(rules)
        c.growing = bool(rules.get("R1_CONSECUTIVE_GROWTH"))
        c.alert_level = "NONE" if level == "DRAINING" else level
        db.commit()
        return {"ok": True, "candidate_id": candidate_id,
                "n_observations": len(obs), "series": series,
                "metrics": metrics,
                "rules_fired": [r for r, on in rules.items() if on and
                                not r.startswith("_")],
                "alert": {"level": level,
                          "rules": {k: v for k, v in rules.items()
                                    if v and not k.startswith("_")}},
                "method": "Exponential fit (r, T2) + linear surge rate; "
                          "explicit rules R1-R5, thresholds in growth.py",
                "limitations": [
                    "Observation cadence is satellite-revisit-bound (5-12 d).",
                    "A single bad observation can fire R3 - check the series.",
                    "Snow/ice cover seasonally suppresses detected area and "
                    "can fake a DRAINING signal in winter."]}
    finally:
        if own:
            db.close()


def _metrics_and_rules(days, areas, wse_series):
    metrics, rules = {}, {}
    n = len(areas)
    span = days[-1] - days[0]
    peak = max(areas)
    metrics["peak_area_m2"] = round(peak, 0)
    if peak > 0 and areas[-1] <= peak * (1 - _t("R5_DRAIN_FRACTION")):
        rules["R5_DRAINING"] = True
    run = 0
    for i in range(1, n):
        run = run + 1 if areas[i] > areas[i - 1] else 0
    metrics["consecutive_growth_obs"] = run
    if run >= _t("R1_MIN_CONSECUTIVE"):
        rules["R1_CONSECUTIVE_GROWTH"] = True
    if span >= _t("MIN_SPAN_DAYS") and areas[0] > 0 and areas[-1] > 0:
        r = math.log(areas[-1] / areas[0]) / span
        T2 = math.log(2) / r if r > 0 else math.inf
        metrics["growth_rate_per_day"] = round(r, 4)
        metrics["doubling_time_days"] = (round(T2, 1)
                                         if math.isfinite(T2) else None)
        if 0 < T2 <= _t("R2_MAX_DOUBLING_DAYS"):
            rules["R2_RAPID_DOUBLING"] = {"doubling_time_days": round(T2, 1)}
            if T2 <= _t("R2_CRITICAL_DAYS"):
                rules["R2_RAPID_DOUBLING"]["critical"] = True
    if n >= 2 and days[-1] > days[-2]:
        g = (areas[-1] - areas[-2]) / (days[-1] - days[-2])
        metrics["latest_abs_growth_m2_day"] = round(g, 0)
        if (g >= _t("R3_ABS_SURGE_M2_DAY") and
                min(areas[-2], areas[-1]) >= _t("MIN_TRUST_AREA_M2")):
            rules["R3_ABSOLUTE_SURGE"] = {"m2_per_day": round(g, 0)}
    if len(wse_series) >= 2 and span >= _t("MIN_SPAN_DAYS"):
        w_rate = (wse_series[-1][0] - wse_series[0][0]) / span
        vol_latest = wse_series[-1][1]
        metrics["wse_rise_m_day"] = round(w_rate, 3)
        if w_rate > 0 and (vol_latest or 0) >= _t("R4_VOLUME_M3"):
            rules["R4_WSE_RISING_VOLUME"] = {
                "wse_rise_m_day": round(w_rate, 3),
                "latest_volume_m3": vol_latest}
    return metrics, rules


def _level(rules):
    fired = {k for k in rules if not k.startswith("_") and rules[k]}
    if "R5_DRAINING" in fired and len(fired) == 1:
        return "DRAINING"
    if "R2_RAPID_DOUBLING" in fired and isinstance(
            rules.get("R2_RAPID_DOUBLING"), dict) and             rules["R2_RAPID_DOUBLING"].get("critical"):
        return "CRITICAL"
    if "R3_ABSOLUTE_SURGE" in fired and "R1_CONSECUTIVE_GROWTH" in fired:
        return "CRITICAL"
    if fired & {"R2_RAPID_DOUBLING", "R3_ABSOLUTE_SURGE"}:
        return "WARNING"
    if "R1_CONSECUTIVE_GROWTH" in fired and "R4_WSE_RISING_VOLUME" in fired:
        return "WARNING"
    if fired & {"R1_CONSECUTIVE_GROWTH", "R4_WSE_RISING_VOLUME"}:
        return "WATCH"
    return "NONE"


def open_alerts(db):
    rows = db.query(LakeCandidate).filter(
        LakeCandidate.alert_level.in_(("WATCH", "WARNING", "CRITICAL")),
        LakeCandidate.status.in_(("DETECTED", "VERIFIED"))).all()
    order = {"CRITICAL": 0, "WARNING": 1, "WATCH": 2}
    rows = sorted(rows, key=lambda c: order.get(c.alert_level, 9))
    return [{"id": c.id, "zone_id": c.zone_id, "lat": c.lat, "lon": c.lon,
             "area_m2": c.area_m2, "volume_m3": c.volume_m3,
             "score": c.score, "status": c.status,
             "alert_level": c.alert_level, "growing": c.growing,
             "last_seen_at": c.last_seen_at.isoformat()} for c in rows]
