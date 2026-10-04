"""Site-specific erosion parameter store.
Falls back to Hanson & Temple (1997) literature values when not calibrated.
k_d [m3/(N.s)] detachability coefficient; tau_c [Pa] critical shear stress.
Literature values are order-of-magnitude only — lab testing required per site.
"""
import json
from pathlib import Path

# Detachability / critical shear: Hanson & Temple (1997) class guidance.
# ORDER-OF-MAGNITUDE literature values [VERIFY per site].
KD_BY_MATERIAL = {
    "Earth": 2.0e-6, "Landslide debris": 5.0e-6, "Sediment": 4.0e-6,
    "Ice/debris": 3.0e-6, "Mixed": 3.0e-6, "Unknown": 3.0e-6,
    "Rock": 2.0e-7,
}
TAU_C_BY_MATERIAL = {
    "Earth": 5.0, "Landslide debris": 2.0, "Sediment": 1.5,
    "Ice/debris": 2.0, "Mixed": 3.0, "Unknown": 3.0, "Rock": 100.0,
}

DATA_FILE = Path("data/erosion_params.json")
_STORE = {}  # {incident_id: {material: {k_d, tau_c, source}}}

def _load():
    global _STORE
    if DATA_FILE.exists():
        try:
            _STORE = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except Exception:
            _STORE = {}
_load()

def get_params(incident_id, material):
    site = (_STORE.get(str(incident_id) if incident_id else "", {})
                  .get(str(material), None))
    if site:
        return {"k_d": float(site["k_d"]), "tau_c": float(site["tau_c"]),
                "source": site.get("source", "user-calibrated"),
                "flagged_literature": False}
    return {"k_d": KD_BY_MATERIAL.get(material, 3e-6),
            "tau_c": TAU_C_BY_MATERIAL.get(material, 3.0),
            "source": "literature (Hanson & Temple 1997, order-of-magnitude [VERIFY per site])",
            "flagged_literature": True}

def set_params(incident_id, material, k_d, tau_c, source="user-calibrated"):
    if not (1e-9 <= k_d <= 1e-3):
        raise ValueError("k_d out of plausible range [1e-9, 1e-3]")
    if not (0.1 <= tau_c <= 1000):
        raise ValueError("tau_c out of plausible range [0.1, 1000]")
    iid = str(incident_id)
    if iid not in _STORE:
        _STORE[iid] = {}
    _STORE[iid][material] = {"k_d": float(k_d), "tau_c": float(tau_c), "source": source}
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(_STORE, indent=2), encoding="utf-8")
    return get_params(incident_id, material)

def delete_params(incident_id, material):
    iid = str(incident_id)
    removed = False
    if iid in _STORE and material in _STORE[iid]:
        del _STORE[iid][material]
        removed = True
        DATA_FILE.write_text(json.dumps(_STORE, indent=2), encoding="utf-8")
    return removed

def list_calibrations(incident_id):
    """Returns all materials with their current params (calibrated or literature)."""
    mats = list(KD_BY_MATERIAL.keys())
    return {m: get_params(incident_id, m) for m in mats}
