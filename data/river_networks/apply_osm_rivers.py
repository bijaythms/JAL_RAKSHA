"""
Apply real OSM river centerlines to the DB.
Only updates incidents where we have confirmed REAL OSM data (step variance > 0.05).
Also handles legacy named files (idukki_periyar.json, etc.) and incident-ID named files.
"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from app.db import SessionLocal, Incident

OUT_DIR = Path("data/river_networks")

def total_km(nodes):
    return sum(
        math.sqrt(((nodes[i+1][0]-nodes[i][0])*111)**2 +
                  ((nodes[i+1][1]-nodes[i][1])*111*math.cos(math.radians(nodes[i][0])))**2)
        for i in range(len(nodes)-1)
    )

def is_real_osm(nodes):
    if len(nodes) < 15: return False
    steps = [math.sqrt(((nodes[i+1][0]-nodes[i][0])*111)**2 +
             ((nodes[i+1][1]-nodes[i][1])*111*math.cos(math.radians(nodes[i][0])))**2)
             for i in range(min(30, len(nodes)-1))]
    return (max(steps) - min(steps)) > 0.05

db = SessionLocal()
all_inc = {i.id: i for i in db.query(Incident).all()}
updated = skipped = no_file = 0

# Map: incident_id -> JSON file (check both upper and lower case filenames)
for iid, inc in sorted(all_inc.items()):
    candidates = [
        OUT_DIR / f"{iid}.json",
        OUT_DIR / f"{iid.lower()}.json",
    ]
    # Also check legacy named files for known dams
    name_lower = (inc.name or "").lower()
    if "idukki" in name_lower or "cheruthoni" in name_lower:
        candidates += [OUT_DIR / "idukki_periyar.json", OUT_DIR / "jr-20260929-22f604.json"]
    if "mullaperiyar" in name_lower:
        candidates += [OUT_DIR / "mullaperiyar.json", OUT_DIR / "jr-20260929-4141cc.json"]
    if "tehri" in name_lower:
        candidates += [OUT_DIR / "tehri_bhagirathi.json"]

    best_nodes = None
    for f in candidates:
        if f.exists():
            try:
                nodes = json.loads(f.read_text())
                if is_real_osm(nodes):
                    if best_nodes is None or len(nodes) > len(best_nodes):
                        best_nodes = nodes
            except:
                pass

    if best_nodes is None:
        no_file += 1
        continue

    km = total_km(best_nodes)
    inc.centerline = json.dumps(best_nodes)
    db.commit()
    updated += 1
    print(f"  UPDATED {len(best_nodes):4d}pts {km:6.1f}km  {inc.name[:55]}")

print(f"\nResults: {updated} updated with real OSM, {skipped} skipped, {no_file} no real data yet")
db.close()
