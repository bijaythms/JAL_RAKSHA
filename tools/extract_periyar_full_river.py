import urllib.request
import urllib.parse
import json

# 1. Fetch official Periyar relation from OSM details
url = 'https://nominatim.openstreetmap.org/details?osmtype=R&osmid=11778217&polygon_geojson=1&format=json'
req = urllib.request.Request(url, headers={'User-Agent': 'JalRakshaRiverHydro/2.0'})
res = json.loads(urllib.request.urlopen(req, timeout=12).read().decode('utf-8'))
geo = res.get('geometry', {})
lines = geo.get('coordinates', [])
print(f"Periyar MultiLineString lines count: {len(lines)}")

# Save to tools/periyar_raw.json
with open("tools/periyar_raw.json", "w") as f:
    json.dump(lines, f)
print("Saved periyar_raw.json")
