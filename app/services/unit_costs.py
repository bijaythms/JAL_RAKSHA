"""Configurable unit costs for economic impact calculations.

Costs are looked up in priority order:
  1. Per-incident override  (keyed by incident_id)
  2. Per-region override    (keyed by region key, e.g. 'western_himalaya')
  3. DEFAULT_COSTS fallback

``flagged_placeholder`` is True only when falling back to DEFAULT_COSTS
unchanged — callers should surface this in report limitations.

Overrides persist to ``data/unit_costs.json`` across restarts.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Defaults (literature / Schedule-of-Rates order-of-magnitude placeholders)
# ---------------------------------------------------------------------------
DEFAULT_COSTS: dict = {
    "building": 600_000,
    "crop_per_ha": 120_000,
    "livestock_per_head": 40_000,
}

# ---------------------------------------------------------------------------
# In-memory stores
# ---------------------------------------------------------------------------
_region_overrides: dict[str, dict] = {}   # region_key  -> cost dict
_incident_overrides: dict[str, dict] = {} # incident_id -> cost dict

# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------
_DATA_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "unit_costs.json"


def _load() -> None:
    """Load persisted overrides from disk on module import."""
    global _region_overrides, _incident_overrides
    try:
        if _DATA_FILE.exists():
            data = json.loads(_DATA_FILE.read_text(encoding="utf-8"))
            _region_overrides   = data.get("regions", {})
            _incident_overrides = data.get("incidents", {})
            log.info("unit_costs: loaded from %s", _DATA_FILE)
    except Exception as exc:
        log.warning("unit_costs: failed to load %s (%s) — using defaults", _DATA_FILE, exc)


def _save() -> None:
    """Persist current overrides to disk."""
    try:
        _DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        _DATA_FILE.write_text(
            json.dumps({"regions": _region_overrides, "incidents": _incident_overrides},
                       indent=2),
            encoding="utf-8")
    except Exception as exc:
        log.error("unit_costs: failed to save %s (%s)", _DATA_FILE, exc)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_costs(incident_id: Optional[str] = None,
              region_key: Optional[str] = None) -> dict:
    """Return resolved unit costs with provenance metadata.

    Returns a dict with keys:
      ``costs``               – {"building": int, "crop_per_ha": int, "livestock_per_head": int}
      ``source``              – "incident" | "region" | "default"
      ``flagged_placeholder`` – True when DEFAULT_COSTS are used unchanged
    """
    if incident_id and incident_id in _incident_overrides:
        return {
            "costs": dict(_incident_overrides[incident_id]),
            "source": "incident",
            "flagged_placeholder": False,
        }
    if region_key and region_key in _region_overrides:
        return {
            "costs": dict(_region_overrides[region_key]),
            "source": "region",
            "flagged_placeholder": False,
        }
    return {
        "costs": dict(DEFAULT_COSTS),
        "source": "default",
        "flagged_placeholder": True,
    }


def set_costs(level: str, key: str,
              building: Optional[float] = None,
              crop_per_ha: Optional[float] = None,
              livestock_per_head: Optional[float] = None) -> dict:
    """Set unit cost overrides at ``level`` ('default'|'region'|'incident').

    Only the supplied fields are updated; omitted fields fall back to the
    current default for that level.  Returns the updated cost dict.

    Parameters
    ----------
    level : str
        ``'default'``  – update the module-level DEFAULT_COSTS in-process
                         (not persisted; use 'region'/'incident' for persistence)
        ``'region'``   – store under *key* (a region key string)
        ``'incident'`` – store under *key* (an incident_id string)
    key : str
        The region key or incident_id.  Unused when level is ``'default'``.
    building, crop_per_ha, livestock_per_head : float, optional
        New values.  Any ``None`` values are filled from DEFAULT_COSTS.
    """
    updated = {
        "building":          int(building)          if building          is not None else DEFAULT_COSTS["building"],
        "crop_per_ha":       int(crop_per_ha)       if crop_per_ha       is not None else DEFAULT_COSTS["crop_per_ha"],
        "livestock_per_head": int(livestock_per_head) if livestock_per_head is not None else DEFAULT_COSTS["livestock_per_head"],
    }

    if level == "default":
        DEFAULT_COSTS.update(updated)
    elif level == "region":
        _region_overrides[key] = updated
        _save()
    elif level == "incident":
        _incident_overrides[key] = updated
        _save()
    else:
        raise ValueError(f"Invalid level '{level}'; must be 'default', 'region', or 'incident'")

    return updated


def all_rates() -> dict:
    """Return all configured rates (for the /api/costs endpoint)."""
    return {
        "default": dict(DEFAULT_COSTS),
        "regions": {k: dict(v) for k, v in _region_overrides.items()},
        "incidents": {k: dict(v) for k, v in _incident_overrides.items()},
    }


# Load persisted data immediately on import
_load()
