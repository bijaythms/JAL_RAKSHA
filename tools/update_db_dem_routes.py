"""
Update all dam incidents in SQLite with realistic DEM-derived river valley flow paths.
"""
import sqlite3
import json
import math
from app.services.dem_flow_router import trace_dambreak_valley_dem
from app.services.geo import haversine

conn = sqlite3.connect("data/jalraksha.db")
cur = conn.cursor()

cur.execute("SELECT id, name, lat, lon FROM incidents")
rows = cur.fetchall()

updated = 0
for inc_id, inc_name, lat, lon in rows:
    # Generate authentic DEM river valley route
    pts = trace_dambreak_valley_dem(lat, lon, initial_bearing=135.0, total_km=25.0, dam_name=inc_name)
    if pts and len(pts) >= 2:
        cl_json = json.dumps(pts)
        length_km = 0.0
        for i in range(1, len(pts)):
            length_km += haversine(*pts[i-1], *pts[i]) / 1000.0
        cur.execute("UPDATE incidents SET centerline = ? WHERE id = ?", (cl_json, inc_id))
        print(f"[{inc_id}] {inc_name:<50} -> {len(pts)} pts ({length_km:.1f} km)")
        updated += 1

conn.commit()
conn.close()
print(f"\nSuccessfully updated {updated} incidents with DEM-derived river valley flow paths.")
