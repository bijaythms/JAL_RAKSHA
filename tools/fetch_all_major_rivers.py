import urllib.request
import urllib.parse
import json

rivers = {
    "Bhagirathi River": "Bhagirathi River, Uttarakhand",
    "Sutlej River": "Sutlej River, Himachal Pradesh",
    "Mahanadi River": "Mahanadi River, Odisha",
    "Narmada River": "Narmada River, Gujarat",
    "Krishna River": "Krishna River, Andhra Pradesh",
    "Kaveri River": "Kaveri River, Tamil Nadu",
    "Tungabhadra River": "Tungabhadra River, Karnataka",
    "Godavari River": "Godavari River, Maharashtra"
}

headers = {'User-Agent': 'JalRakshaRiverHydro/3.0 (hydrology@jalraksha.gov.in)'}
out = {}

for key, q in rivers.items():
    url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(q)}&format=json&polygon_geojson=1&limit=1"
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            if data:
                geo = data[0].get('geojson', {})
                out[key] = {
                    "type": geo.get("type"),
                    "coordinates": geo.get("coordinates")
                }
                print(f"Found {key}: {geo.get('type')}")
    except Exception as e:
        print(f"Error {key}: {e}")

with open("tools/major_rivers_osm.json", "w") as f:
    json.dump(out, f)
print("Finished fetching major rivers.")
