import sqlite3
import json
from app.services.dem_flow_router import trace_dambreak_valley_dem
from app.services.geo import haversine

conn = sqlite3.connect('data/jalraksha.db', timeout=30.0)
cur = conn.cursor()

cur.execute("SELECT id, name, lat, lon FROM incidents WHERE name LIKE '%Idukki%' OR name LIKE '%Cheruthoni%'")
rows = cur.fetchall()
for inc_id, inc_name, lat, lon in rows:
    pts = trace_dambreak_valley_dem(lat, lon, dam_name=inc_name)
    length_km = sum(haversine(*pts[i-1], *pts[i]) / 1000.0 for i in range(1, len(pts)))
    cur.execute('UPDATE incidents SET centerline = ? WHERE id = ?', (json.dumps(pts), inc_id))
    print(f"Updated {inc_id} {inc_name}: {len(pts)} pts ({length_km:.1f} km)")

conn.commit()
conn.close()
print("Finished updating Idukki & Cheruthoni flow routes.")
