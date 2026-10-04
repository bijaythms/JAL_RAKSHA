import json
import shutil
import sys
from pathlib import Path
sys.path.insert(0, str(Path(".").resolve()))
from app.db import SessionLocal, Incident, Simulation

with open("data/river_networks/idukki_periyar.json", "r") as f:
    dense_pts = json.load(f)

print(f"Loaded {len(dense_pts)} valley centerline nodes.")
print(f"Start: {dense_pts[0]} -> End: {dense_pts[-1]}")

shutil.copy("data/river_networks/idukki_periyar.json", "data/river_networks/JR-20260929-22F604.json")
shutil.copy("data/river_networks/idukki_periyar.json", "data/river_networks/JR-20260929-5A298A.json")
shutil.copy("data/river_networks/idukki_periyar.json", "data/river_networks/JR-20260929-F0D4F3.json")

db = SessionLocal()
target_iids = ["JR-20260929-22F604", "JR-20260929-5A298A", "JR-20260929-F0D4F3"]

for iid in target_iids:
    inc = db.get(Incident, iid)
    if inc:
        inc.centerline = json.dumps(dense_pts)
        print(f"Updated DB Incident {iid} ({inc.name[:35]}): {len(dense_pts)} nodes")

# Clear old cached simulations for Idukki to ensure fresh run with new path
old_sims = db.query(Simulation).filter(Simulation.incident_id.in_(target_iids)).all()
print(f"Removing {len(old_sims)} old simulation records...")
for s in old_sims:
    db.delete(s)

db.commit()
db.close()
print("Database updated successfully with true valley centerline!")
