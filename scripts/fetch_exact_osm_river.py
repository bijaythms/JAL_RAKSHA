import urllib.request
import urllib.parse
import json

# Tight bounding box covering Cheruthoni to Chelachuvadu: 9.84 to 9.94, 76.94 to 76.99
query = """[out:json][timeout:25];
(
  way["waterway"="river"](9.84,76.94,9.94,76.99);
);
out geom;
"""

endpoints = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter"
]

data = None
for ep in endpoints:
    print(f"Trying {ep}...")
    try:
        req = urllib.request.Request(
            ep,
            data=urllib.parse.urlencode({"data": query}).encode("utf-8"),
            headers={"User-Agent": "JalRaksha/1.0"}
        )
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode("utf-8"))
            print(f"Success from {ep}!")
            break
    except Exception as e:
        print(f"Failed {ep}: {e}")

if data:
    ways = data.get("elements", [])
    print(f"Found {len(ways)} river ways:")
    for w in ways:
        tags = w.get("tags", {})
        geom = w.get("geometry", [])
        if geom:
            print(f"Way {w['id']}: name='{tags.get('name', '')}', pts={len(geom)}, start=({geom[0]['lat']:.5f},{geom[0]['lon']:.5f}), end=({geom[-1]['lat']:.5f},{geom[-1]['lon']:.5f})")
    with open("scripts/cheruthoni_river_ways.json", "w", encoding="utf-8") as f:
        json.dump(ways, f, indent=2)
else:
    print("No data received.")
