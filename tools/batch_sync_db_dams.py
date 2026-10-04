"""
Re-sync and update all incidents in SQLite database with verified high-precision dam coordinates.
"""
import sqlite3
import json
import math
from app.services.major_dams import MAJOR_DAMS

def clean_name(n: str) -> str:
    n = n.replace("[MAJOR DAM]", "").replace("[NATIONAL]", "").strip()
    # Strip parentheses like (Uttarakhand), (worst-case breach), etc.
    if "(" in n:
        n = n.split("(")[0].strip()
    return n.lower()

def generate_natural_centerline(start_lat: float, start_lon: float, bearing_deg: float, total_length_km: float = 15.0, steps: int = 30):
    R = 6371.0
    pts = [[round(start_lat, 5), round(start_lon, 5)]]
    cur_lat, cur_lon = start_lat, start_lon
    step_km = total_length_km / steps
    cur_bearing = math.radians(bearing_deg)

    for i in range(1, steps + 1):
        meander = 0.10 * math.sin(i * 0.5)
        bearing = cur_bearing + meander

        d_rad = step_km / R
        lat_rad = math.radians(cur_lat)
        lon_rad = math.radians(cur_lon)

        new_lat_rad = math.asin(
            math.sin(lat_rad) * math.cos(d_rad) +
            math.cos(lat_rad) * math.sin(d_rad) * math.cos(bearing)
        )
        new_lon_rad = lon_rad + math.atan2(
            math.sin(bearing) * math.sin(d_rad) * math.cos(lat_rad),
            math.cos(d_rad) - math.sin(lat_rad) * math.sin(new_lat_rad)
        )

        cur_lat = math.degrees(new_lat_rad)
        cur_lon = math.degrees(new_lon_rad)
        pts.append([round(cur_lat, 5), round(cur_lon, 5)])

    return pts

conn = sqlite3.connect("data/jalraksha.db")
cur = conn.cursor()

cur.execute("SELECT id, name, lat, lon FROM incidents")
rows = cur.fetchall()

updated = 0
for inc_id, inc_name, cur_lat, cur_lon in rows:
    c_name = clean_name(inc_name)
    # Find matching dam in MAJOR_DAMS
    match = None
    for d in MAJOR_DAMS:
        d_clean = clean_name(d["name"])
        if d_clean == c_name or d_clean in c_name or c_name in d_clean:
            match = d
            break
        # Special alias checks
        if "tehri" in c_name and "tehri" in d_clean:
            match = d; break
        if "krs" in c_name or "krishna raja" in c_name and "krishna raja" in d_clean:
            match = d; break
        if "pong" in c_name and "pong" in d_clean:
            match = d; break
        if "bhakra" in c_name and "bhakra" in d_clean:
            match = d; break
        if "sardar sarovar" in c_name and "sardar sarovar" in d_clean:
            match = d; break
        if "hirakud" in c_name and "hirakud" in d_clean:
            match = d; break
        if "idukki" in c_name and "idukki" in d_clean and "cheruthoni" not in c_name:
            match = d; break
        if "cheruthoni" in c_name and "cheruthoni" in d_clean:
            match = d; break
        if "mullaperiyar" in c_name and "mullaperiyar" in d_clean:
            match = d; break
        if "mettur" in c_name and "mettur" in d_clean:
            match = d; break
        if "nagarjuna" in c_name and "nagarjuna" in d_clean:
            match = d; break
        if "tungabhadra" in c_name and "tungabhadra" in d_clean:
            match = d; break

    if match:
        new_lat = match["lat"]
        new_lon = match["lon"]
        bearing = match.get("bearing_deg", 130.0)
        dist_m = math.sqrt((new_lat - cur_lat)**2 + (new_lon - cur_lon)**2) * 111000
        cl = generate_natural_centerline(new_lat, new_lon, bearing)
        cl_json = json.dumps(cl)
        cur.execute("""
            UPDATE incidents
            SET lat = ?, lon = ?, centerline = ?
            WHERE id = ?
        """, (new_lat, new_lon, cl_json, inc_id))
        print(f"[{inc_id}] {inc_name:<45} -> ({new_lat:.4f}, {new_lon:.4f})  [shift: {dist_m:6.0f}m]")
        updated += 1
    else:
        print(f"[{inc_id}] {inc_name} -> No match in MAJOR_DAMS (kept original)")

conn.commit()
conn.close()
print(f"\nTotal incidents updated in SQLite: {updated} / {len(rows)}")
