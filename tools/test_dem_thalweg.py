import urllib.request
import json
import math

def destination(lat, lon, bearing_deg, distance_m):
    R = 6371000.0
    d_rad = distance_m / R
    b_rad = math.radians(bearing_deg)
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)

    lat2 = math.asin(
        math.sin(lat_rad) * math.cos(d_rad) +
        math.cos(lat_rad) * math.sin(d_rad) * math.cos(b_rad)
    )
    lon2 = lon_rad + math.atan2(
        math.sin(b_rad) * math.sin(d_rad) * math.cos(lat_rad),
        math.cos(d_rad) - math.sin(lat_rad) * math.sin(lat2)
    )
    return math.degrees(lat2), math.degrees(lon2)

def get_elevations(points):
    """Batch fetch elevations from Open-Meteo DEM API."""
    if not points:
        return []
    lat_str = ','.join(f"{p[0]:.5f}" for p in points)
    lon_str = ','.join(f"{p[1]:.5f}" for p in points)
    url = f"https://api.open-meteo.com/v1/elevation?latitude={lat_str}&longitude={lon_str}"
    req = urllib.request.Request(url, headers={'User-Agent': 'JalRakshaDEM/1.0'})
    with urllib.request.urlopen(req, timeout=8) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        return data.get('elevation', [])

def trace_dem_flow_path(start_lat, start_lon, initial_bearing=330.0, total_km=15.0, step_m=350.0):
    current_lat = start_lat
    current_lon = start_lon
    current_bearing = initial_bearing
    path = [[round(current_lat, 5), round(current_lon, 5)]]

    num_steps = int((total_km * 1000.0) / step_m)
    print(f"Tracing DEM flow path: start=({start_lat}, {start_lon}), {num_steps} steps of {step_m}m")

    # Arc of angles to sample at each step (-60, -40, -20, 0, +20, +40, +60)
    angle_offsets = [-65, -45, -30, -15, 0, 15, 30, 45, 65]

    for step in range(num_steps):
        candidates = []
        for offset in angle_offsets:
            b = (current_bearing + offset) % 360.0
            nlat, nlon = destination(current_lat, current_lon, b, step_m)
            candidates.append((nlat, nlon, b, offset))

        # Query elevations for all candidates in one batch
        elevs = get_elevations([(c[0], c[1]) for c in candidates])

        # Evaluate score: we want lowest elevation, with slight penalty for sharp direction turns
        best_cand = None
        best_score = float('inf')

        for (nlat, nlon, b, offset), elev in zip(candidates, elevs):
            if elev is None:
                continue
            # Score combines elevation (primary) + small angle penalty to keep flow moving downstream
            turn_penalty = abs(offset) * 0.4
            score = elev + turn_penalty
            if score < best_score:
                best_score = score
                best_cand = (nlat, nlon, b, elev)

        if not best_cand:
            # Fallback step forward
            nlat, nlon = destination(current_lat, current_lon, current_bearing, step_m)
            best_cand = (nlat, nlon, current_bearing, 0)

        current_lat, current_lon = best_cand[0], best_cand[1]
        # Smooth bearing adjustment (inertia)
        current_bearing = (0.6 * current_bearing + 0.4 * best_cand[2]) % 360.0
        path.append([round(current_lat, 5), round(current_lon, 5)])

    return path

# Test for Cheruthoni Dam
path = trace_dem_flow_path(9.8509, 76.9725, initial_bearing=335.0, total_km=15.0, step_m=400.0)
print(f"Generated DEM flow path with {len(path)} points.")
print("First 10 points:")
for p in path[:10]:
    print(f"  {p}")

# Also compare elevation profile
elevs = get_elevations(path)
print(f"Elevation drops from {elevs[0]}m to {elevs[-1]}m (min: {min(elevs)}m, max: {max(elevs)}m)")
