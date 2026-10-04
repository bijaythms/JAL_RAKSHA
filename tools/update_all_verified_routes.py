import sqlite3
import json
from app.services.dem_flow_router import trace_dambreak_valley_dem, identify_verified_corridor
from app.services.geo import haversine

conn = sqlite3.connect('data/jalraksha.db', timeout=15.0)
cur = conn.cursor()

cur.execute("SELECT id, name, lat, lon FROM incidents")
rows = cur.fetchall()

updated = 0
for inc_id, inc_name, lat, lon in rows:
    v_corridor = identify_verified_corridor(lat, lon, inc_name)
    if v_corridor:
        pts = trace_dambreak_valley_dem(lat, lon, dam_name=inc_name)
        length_km = sum(haversine(*pts[i-1], *pts[i]) / 1000.0 for i in range(1, len(pts)))
        cur.execute('UPDATE incidents SET centerline = ? WHERE id = ?', (json.dumps(pts), inc_id))
        print(f"Updated verified corridor: [{inc_id}] {inc_name} -> {len(pts)} pts ({length_km:.1f} km)")
        updated += 1

conn.commit()
conn.close()
print(f"\nFinished updating {updated} verified major dam river corridors.")
