"""Historical water-frequency baselines per zone (cached npz with shape)."""
import json, time
from pathlib import Path
import numpy as np
from ..config import cfg

BASELINE_DIR = Path(cfg.DB_PATH).parent / "baselines"
BASELINE_DIR.mkdir(parents=True, exist_ok=True)

MIN_SCENES = 4
MAX_SCENES = 12


def baseline_path(zone_id):
    return BASELINE_DIR / f"{zone_id}.npz"


def save_baseline(zone_id, freq, valid, n_scenes, bbox, sources, shape):
    np.savez_compressed(
        baseline_path(zone_id), freq=freq.astype("float32"),
        valid=valid.astype("uint8"), n_scenes=n_scenes,
        bbox=np.array(bbox, dtype="float64"), shape=np.array(shape),
        built_at=time.time(), sources=np.array(json.dumps(sources)))


def load_baseline(zone_id):
    p = baseline_path(zone_id)
    if not p.exists():
        return None
    z = np.load(p, allow_pickle=True)
    return {"freq": z["freq"], "valid": z["valid"],
            "n_scenes": int(z["n_scenes"]),
            "bbox": z["bbox"].tolist(),
            "shape": tuple(int(x) for x in z["shape"]),
            "built_at": float(z["built_at"]),
            "sources": json.loads(str(z["sources"]))}


def is_stale(b, max_age_days=14):
    return (not b) or (time.time() - b["built_at"] > max_age_days * 86400)


def classify(baseline_freq, current_water, new_water_thresh=0.10,
             persistent_thresh=0.50):
    cls = np.zeros(baseline_freq.shape, dtype="uint8")
    cls[baseline_freq >= persistent_thresh] = 1
    cls[(baseline_freq >= new_water_thresh) &
        (baseline_freq < persistent_thresh)] = 2
    cls[current_water & (baseline_freq < new_water_thresh)] = 3
    return cls
