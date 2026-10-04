import urllib.request
import urllib.parse
import json

q = """[out:json][timeout:20];
(
  way["waterway"="river"](9.84, 76.75, 10.05, 77.00);
);
out geom;"""

data = urllib.parse.urlencode({'data': q}).encode('utf-8')
req = urllib.request.Request(
    'https://overpass-api.de/api/interpreter',
    data=data,
    headers={'User-Agent': 'JalRakshaRiver/2.0 (research@jalraksha.gov.in)'}
)

try:
    resp = urllib.request.urlopen(req, timeout=18)
    res = json.loads(resp.read().decode('utf-8'))
    ways = res.get('elements', [])
    print(f"Found {len(ways)} river ways")
    for w in ways:
        name = w.get('tags', {}).get('name', 'unnamed')
        geom = w.get('geometry', [])
        print(f"Way ID {w['id']}: {name} ({len(geom)} pts), start=({geom[0]['lat']}, {geom[0]['lon']}), end=({geom[-1]['lat']}, {geom[-1]['lon']})")
    with open("tools/river_ways.json", "w") as f:
        json.dump(ways, f, indent=2)
except Exception as e:
    print(f"Error: {e}")
