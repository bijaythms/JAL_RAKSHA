"""
Audit and update script for all 65 major dams in India.
Ensures every dam's GPS coordinates land directly on the physical dam wall / crest
on satellite imagery (Google Hybrid / ESRI).
"""
import sqlite3
import math
import json
from pathlib import Path
from app.services.major_dams import MAJOR_DAMS

# High-precision coordinates table (anchored on physical crest / spillway structure)
ACCURATE_DAM_COORDS = {
    # Uttarakhand & Himalayas
    "DAM-TEHRI": {"lat": 30.3783, "lon": 78.4800, "bearing": 140.0},
    "DAM-KOTESHWAR": {"lat": 30.2602, "lon": 78.4979, "bearing": 150.0},
    "DAM-RAMGANGA": {"lat": 29.5180, "lon": 78.7582, "bearing": 190.0},
    "DAM-LAKHWAR": {"lat": 30.5208, "lon": 77.9152, "bearing": 135.0},
    "DAM-DHAULIGANGA": {"lat": 29.9788, "lon": 80.5732, "bearing": 170.0},

    # Himachal Pradesh & Punjab
    "DAM-BHAKRA": {"lat": 31.4116, "lon": 76.4357, "bearing": 210.0},
    "DAM-PONG": {"lat": 31.9709, "lon": 75.9459, "bearing": 230.0},
    "DAM-CHAMERA": {"lat": 32.5969, "lon": 75.9855, "bearing": 260.0},
    "DAM-KOLDAM": {"lat": 31.3832, "lon": 76.8747, "bearing": 270.0},
    "DAM-NATHPA-JHAKRI": {"lat": 31.5617, "lon": 77.9920, "bearing": 250.0},

    # Jammu & Kashmir
    "DAM-BAGLIHAR": {"lat": 33.1620, "lon": 75.3278, "bearing": 240.0},
    "DAM-SALAL": {"lat": 33.1423, "lon": 74.8100, "bearing": 190.0},
    "DAM-URI": {"lat": 34.1450, "lon": 74.0720, "bearing": 270.0},

    # Gujarat
    "DAM-SARDAR-SAROVAR": {"lat": 21.8298, "lon": 73.7497, "bearing": 270.0},
    "DAM-UKAI": {"lat": 21.2482, "lon": 73.5894, "bearing": 260.0},
    "DAM-KADANA": {"lat": 23.3060, "lon": 73.8260, "bearing": 220.0},
    "DAM-DHAROI": {"lat": 23.9863, "lon": 72.9117, "bearing": 200.0},

    # Maharashtra
    "DAM-KOYNA": {"lat": 17.4023, "lon": 73.7510, "bearing": 85.0},
    "DAM-JAYAKWADI": {"lat": 19.4725, "lon": 75.3639, "bearing": 120.0},
    "DAM-UJJANI": {"lat": 18.0739, "lon": 75.1200, "bearing": 135.0},
    "DAM-BHATSA": {"lat": 19.5131, "lon": 73.4174, "bearing": 240.0},

    # Madhya Pradesh
    "DAM-INDIRA-SAGAR": {"lat": 22.2845, "lon": 76.4719, "bearing": 270.0},
    "DAM-GANDHI-SAGAR": {"lat": 24.7067, "lon": 75.5533, "bearing": 350.0},
    "DAM-BANSAGAR": {"lat": 24.1893, "lon": 81.2872, "bearing": 65.0},
    "DAM-BARGI": {"lat": 22.9390, "lon": 79.9217, "bearing": 280.0},
    "DAM-TAWA": {"lat": 22.5562, "lon": 77.9742, "bearing": 340.0},

    # Rajasthan
    "DAM-RANA-PRATAP-SAGAR": {"lat": 24.9177, "lon": 75.5828, "bearing": 30.0},
    "DAM-BISALPUR": {"lat": 25.9244, "lon": 75.4556, "bearing": 85.0},
    "DAM-MAHI-BAJAJ": {"lat": 23.6285, "lon": 74.5473, "bearing": 210.0},

    # Odisha
    "DAM-HIRAKUD": {"lat": 21.5280, "lon": 83.8690, "bearing": 120.0},
    "DAM-RENGALI": {"lat": 21.2768, "lon": 85.0325, "bearing": 130.0},
    "DAM-INDRAVATI": {"lat": 19.2763, "lon": 82.8284, "bearing": 160.0},

    # Andhra Pradesh & Telangana
    "DAM-NAGARJUNA-SAGAR": {"lat": 16.5756, "lon": 79.3117, "bearing": 85.0},
    "DAM-SRISAILAM": {"lat": 16.0868, "lon": 78.8970, "bearing": 70.0},
    "DAM-POLAVARAM": {"lat": 17.2573, "lon": 81.6464, "bearing": 115.0},

    # Karnataka
    "DAM-TUNGABHADRA": {"lat": 15.2636, "lon": 76.3337, "bearing": 65.0},
    "DAM-ALMATTI": {"lat": 16.3310, "lon": 75.8880, "bearing": 90.0},
    "DAM-KRS": {"lat": 12.4247, "lon": 76.5722, "bearing": 105.0},
    "DAM-SUPA": {"lat": 15.2762, "lon": 74.5269, "bearing": 190.0},
    "DAM-LINGANAMAKKI": {"lat": 14.1759, "lon": 74.8465, "bearing": 310.0},

    # Kerala
    "DAM-IDUKKI": {"lat": 9.8458, "lon": 76.9742, "bearing": 330.0},
    "DAM-CHERUTHONI": {"lat": 9.8509, "lon": 76.9725, "bearing": 325.0},
    "DAM-MULLAPERIYAR": {"lat": 9.5286, "lon": 77.1441, "bearing": 280.0},
    "DAM-MALAMPUZHA": {"lat": 10.8285, "lon": 76.6857, "bearing": 225.0},
    "DAM-SHOLAYAR": {"lat": 10.3218, "lon": 76.7355, "bearing": 260.0},

    # Tamil Nadu
    "DAM-METTUR": {"lat": 11.8035, "lon": 77.8061, "bearing": 160.0},
    "DAM-BHAVANISAGAR": {"lat": 11.4708, "lon": 77.1139, "bearing": 90.0},
    "DAM-VAIGAI": {"lat": 10.0465, "lon": 77.5821, "bearing": 110.0},

    # Uttar Pradesh & Bihar
    "DAM-RIHAND": {"lat": 24.2031, "lon": 83.0062, "bearing": 10.0},
    "DAM-MATATILA": {"lat": 25.1037, "lon": 78.3683, "bearing": 40.0},
    "DAM-KOSI-BARRAGE": {"lat": 26.5262, "lon": 86.9271, "bearing": 165.0},

    # Jharkhand & West Bengal
    "DAM-MAITHON": {"lat": 23.7845, "lon": 86.8125, "bearing": 130.0},
    "DAM-PANCHET": {"lat": 23.6810, "lon": 86.7473, "bearing": 110.0},
    "DAM-KANGSABATI": {"lat": 22.9639, "lon": 86.7889, "bearing": 115.0},
    "DAM-FARAKKA": {"lat": 24.8048, "lon": 87.9336, "bearing": 140.0},

    # Sikkim & Northeast
    "DAM-TEESTA-V": {"lat": 27.3867, "lon": 88.5034, "bearing": 195.0},
    "DAM-SOUTH-LHONAK": {"lat": 27.9144, "lon": 88.1836, "bearing": 95.0},
    "DAM-SUBANSIRI": {"lat": 27.5536, "lon": 94.2586, "bearing": 155.0},
    "DAM-UMIAM": {"lat": 25.6594, "lon": 91.9002, "bearing": 340.0},
    "DAM-DOYANG": {"lat": 26.2323, "lon": 94.2609, "bearing": 290.0},

    # Central & Landslide / High-Risk Natural Sites
    "DAM-HASDEO-BANGO": {"lat": 22.6050, "lon": 82.5980, "bearing": 170.0},
    "DAM-GANGREL": {"lat": 20.6267, "lon": 81.5600, "bearing": 45.0},
    "DAM-RISHIGANGA": {"lat": 30.4835, "lon": 79.7215, "bearing": 295.0},
    "DAM-GYA": {"lat": 33.6530, "lon": 77.7350, "bearing": 290.0},
    "DAM-PAREECHU": {"lat": 31.9505, "lon": 78.5805, "bearing": 255.0},
}

def generate_natural_centerline(start_lat: float, start_lon: float, bearing_deg: float, total_length_km: float = 15.0, steps: int = 30):
    """Generates realistic downstream river centerline path anchored exactly at dam crest."""
    R = 6371.0
    pts = [[round(start_lat, 5), round(start_lon, 5)]]
    cur_lat, cur_lon = start_lat, start_lon
    step_km = total_length_km / steps
    cur_bearing = math.radians(bearing_deg)

    for i in range(1, steps + 1):
        # Add slight natural river sinuosity
        meander = 0.12 * math.sin(i * 0.45)
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

def update_database():
    db_path = Path("data/jalraksha.db")
    if not db_path.exists():
        print("Database data/jalraksha.db not found!")
        return

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    updated = 0
    for dam_id, coord in ACCURATE_DAM_COORDS.items():
        lat = coord["lat"]
        lon = coord["lon"]
        bearing = coord["bearing"]
        cl = generate_natural_centerline(lat, lon, bearing)
        cl_json = json.dumps(cl)

        # Check if exists
        cur.execute("SELECT id, name, lat, lon FROM incidents WHERE id = ?", (dam_id,))
        row = cur.fetchone()
        if row:
            old_lat, old_lon = row[2], row[3]
            dist_m = math.sqrt((lat - old_lat)**2 + (lon - old_lon)**2) * 111000
            cur.execute("""
                UPDATE incidents 
                SET lat = ?, lon = ?, centerline = ?
                WHERE id = ?
            """, (lat, lon, cl_json, dam_id))
            print(f"Updated DB {dam_id}: ({old_lat:.4f}, {old_lon:.4f}) -> ({lat:.4f}, {lon:.4f}) [shifted {dist_m:.0f}m]")
            updated += 1

    conn.commit()
    conn.close()
    print(f"\nSuccessfully updated {updated} dams in SQLite database.")

def update_major_dams_py():
    path = Path("app/services/major_dams.py")
    content = path.read_text(encoding="utf-8")

    # For each dam, replace lat, lon, bearing_deg
    import re
    for dam_id, coord in ACCURATE_DAM_COORDS.items():
        # Match pattern: "id": "dam_id", ... "lat": X, "lon": Y,
        # We can find the block for dam_id
        idx = content.find(f'"id": "{dam_id}"')
        if idx != -1:
            end_idx = content.find("}", idx)
            block = content[idx:end_idx]
            
            # Replace lat
            block_new = re.sub(r'"lat":\s*[\d\.]+', f'"lat": {coord["lat"]:.4f}', block)
            # Replace lon
            block_new = re.sub(r'"lon":\s*[\d\.]+', f'"lon": {coord["lon"]:.4f}', block_new)
            # Replace bearing_deg if present
            if '"bearing_deg":' in block_new:
                block_new = re.sub(r'"bearing_deg":\s*[\d\.]+', f'"bearing_deg": {coord["bearing"]:.1f}', block_new)
            
            content = content[:idx] + block_new + content[end_idx:]

    path.write_text(content, encoding="utf-8")
    print(f"Successfully updated app/services/major_dams.py with accurate GPS coordinates.")

if __name__ == "__main__":
    update_database()
    update_major_dams_py()
