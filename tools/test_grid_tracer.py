import numpy as np
import urllib.request
import json
import math

def fetch_elevation_grid(min_lat, min_lon, max_lat, max_lon, nx=35, ny=35):
    lats = np.linspace(min_lat, max_lat, ny)
    lons = np.linspace(min_lon, max_lon, nx)
    
    # Open-Meteo accepts up to 1000 points per call
    all_pts = [(lat, lon) for lat in lats for lon in lons]
    lat_str = ','.join(f"{p[0]:.4f}" for p in all_pts)
    lon_str = ','.join(f"{p[1]:.4f}" for p in all_pts)
    url = f"https://api.open-meteo.com/v1/elevation?latitude={lat_str}&longitude={lon_str}"
    req = urllib.request.Request(url, headers={'User-Agent': 'JalRakshaGrid/1.0'})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        elevs = np.array(data['elevation'], dtype=np.float32).reshape((ny, nx))
        return lats, lons, elevs

def trace_dambreak_valley(start_lat, start_lon, target_length_km=20.0):
    # For Idukki/Cheruthoni, flow goes towards Periyar gorge (north-northwest)
    # Bounding box covers 9.84 to 10.05 N, 76.75 to 76.99 E
    min_lat, max_lat = start_lat - 0.02, start_lat + 0.18
    min_lon, max_lon = start_lon - 0.20, start_lon + 0.04
    
    print(f"Fetching DEM grid for bbox ({min_lat:.3f}, {min_lon:.3f}) to ({max_lat:.3f}, {max_lon:.3f})...")
    lats, lons, elev = fetch_elevation_grid(min_lat, min_lon, max_lat, max_lon, nx=30, ny=30)
    print(f"Grid fetched: {elev.shape}, elevation range: {np.nanmin(elev):.1f}m to {np.nanmax(elev):.1f}m")

    # Trace steepest descent down the DEM grid from (start_lat, start_lon)
    # Find closest grid index
    cur_r = int(np.argmin(np.abs(lats - start_lat)))
    cur_c = int(np.argmin(np.abs(lons - start_lon)))
    
    path = [[round(float(lats[cur_r]), 5), round(float(lons[cur_c]), 5)]]
    visited = set([(cur_r, cur_c)])
    
    ny, nx = elev.shape
    for step in range(50):
        # Look at 8 neighbors
        best_r, best_c = None, None
        best_elev = float('inf')
        
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0: continue
                nr, nc = cur_r + dr, cur_c + dc
                if 0 <= nr < ny and 0 <= nc < nx:
                    if (nr, nc) not in visited:
                        z = elev[nr, nc]
                        if z < best_elev:
                            best_elev = z
                            best_r, best_c = nr, nc
        
        if best_r is None:
            break
            
        cur_r, cur_c = best_r, best_c
        visited.add((cur_r, cur_c))
        path.append([round(float(lats[cur_r]), 5), round(float(lons[cur_c]), 5)])
        
    print(f"Traced DEM path with {len(path)} points.")
    for p in path[:15]:
        print(" ", p)

if __name__ == "__main__":
    trace_dambreak_valley(9.8509, 76.9725)
