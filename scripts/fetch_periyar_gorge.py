import urllib.request
import urllib.parse
import json

query = """
[out:json][timeout:25];
(
  way["waterway"="river"](9.84,76.75,10.07,76.98);
);
out geom;
"""

endpoints = [
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass-api.de/api/interpreter"
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
        with urllib.request.urlopen(req, timeout=30) as res:
            data = json.loads(res.read().decode("utf-8"))
            print(f"Success from {ep}!")
            break
    except Exception as e:
        print(f"Failed {ep}: {e}")

if data:
    ways = data.get("elements", [])
    print(f"Total river ways found: {len(ways)}")
    with open("scripts/periyar_river_ways.json", "w", encoding="utf-8") as f:
        json.dump(ways, f, indent=2)
    for elem in ways:
        name = elem.get("tags", {}).get("name", "")
        geom = elem.get("geometry", [])
        if geom:
            print(f"Way {elem['id']}: name='{name}', pts={len(geom)}, start=({geom[0]['lat']:.4f},{geom[0]['lon']:.4f}), end=({geom[-1]['lat']:.4f},{geom[-1]['lon']:.4f})")
