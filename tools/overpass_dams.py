import json
import urllib.request
import urllib.parse
import time

dams_to_find = {
    "DAM-NAGARJUNA-SAGAR": (16.55, 79.28, 16.60, 79.35),
    "DAM-UKAI": (21.20, 73.55, 21.30, 73.65),
    "DAM-UJJANI": (18.00, 75.05, 18.15, 75.18),
    "DAM-TAWA": (22.50, 77.92, 22.60, 78.02),
    "DAM-BISALPUR": (25.95, 75.40, 26.05, 75.52),
    "DAM-ALMATTI": (16.30, 75.85, 16.36, 75.92),
    "DAM-KRS": (12.40, 76.55, 12.45, 76.60),
    "DAM-BHAVANISAGAR": (11.43, 77.10, 11.50, 77.18),
    "DAM-MAITHON": (23.75, 86.78, 23.82, 86.85),
    "DAM-HASDEO-BANGO": (22.58, 82.55, 22.65, 82.65),
    "DAM-GANGREL": (20.60, 81.52, 20.66, 81.60),
    "DAM-GANDHI-SAGAR": (24.68, 75.52, 24.75, 75.60)
}

overpass_url = "https://overpass-api.de/api/interpreter"
found = {}

for did, (s, w, n, e) in dams_to_find.items():
    query = f"""[out:json][timeout:20];
    (
      node["waterway"="dam"]({s},{w},{n},{e});
      way["waterway"="dam"]({s},{w},{n},{e});
      node["barrier"="dam"]({s},{w},{n},{e});
      way["barrier"="dam"]({s},{w},{n},{e});
    );
    out center;"""
    try:
        post_data = urllib.parse.urlencode({"data": query}).encode("utf-8")
        req = urllib.request.Request(
            overpass_url,
            data=post_data,
            headers={"User-Agent": "JalRakshaDamAuditor2/2.0 (research@jalraksha.gov.in)"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            elems = data.get("elements", [])
            if elems:
                first = elems[0]
                pt = first.get("center", first)
                name = first.get("tags", {}).get("name", first.get("tags", {}).get("name:en", ""))
                found[did] = {
                    "lat": round(pt["lat"], 5),
                    "lon": round(pt["lon"], 5),
                    "name": name,
                    "tags": first.get("tags", {})
                }
                print(f"Found {did}: {name} at ({pt['lat']}, {pt['lon']})")
            else:
                found[did] = "No dam element in bbox"
                print(f"Not found in bbox {did}")
    except Exception as err:
        found[did] = f"Error: {err}"
        print(f"Error {did}: {err}")
    time.sleep(1.0)

with open("tools/overpass_found.json", "w") as f:
    json.dump(found, f, indent=2)
print("Finished Overpass queries.")
