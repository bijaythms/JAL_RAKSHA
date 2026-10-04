import urllib.request
import urllib.parse
import json

q = """[out:json][timeout:15];
(
  way["waterway"~"river|stream"](9.80, 76.90, 9.98, 77.02);
);
out geom;"""

data = urllib.parse.urlencode({'data': q}).encode('utf-8')
req = urllib.request.Request('https://overpass-api.de/api/interpreter', data=data, headers={'User-Agent': 'JalRakshaRiver/1.0'})
try:
    resp = urllib.request.urlopen(req, timeout=12)
    res = json.loads(resp.read().decode('utf-8'))
    print(f"Total waterways found: {len(res.get('elements', []))}")
    for el in res.get('elements', [])[:10]:
        print(el.get('tags', {}).get('name'), el.get('tags', {}).get('waterway'), len(el.get('geometry', [])))
except Exception as e:
    print(f"Error: {e}")
