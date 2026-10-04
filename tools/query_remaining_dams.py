import json
import urllib.request
import urllib.parse

# Specific queries for the remaining dams
remaining_queries = {
    "DAM-UKAI": "Ukai Dam",
    "DAM-UJJANI": "Ujjani Dam, Maharashtra",
    "DAM-TAWA": "Tawa Dam, Hoshangabad",
    "DAM-BISALPUR": "Bisalpur Dam, Tonk",
    "DAM-INDRAVATI": "Indravati Dam, Odisha",
    "DAM-NAGARJUNA-SAGAR": "Nagarjuna Sagar Dam",
    "DAM-ALMATTI": "Almatti Dam",
    "DAM-KRS": "Krishna Raja Sagara Dam",
    "DAM-BHAVANISAGAR": "Bhavanisagar Dam",
    "DAM-MAITHON": "Maithon Dam",
    "DAM-SOUTH-LHONAK": "South Lhonak, Sikkim",
    "DAM-SUBANSIRI": "Lower Subansiri Dam",
    "DAM-HASDEO-BANGO": "Hasdeo Bango Dam",
    "DAM-GANGREL": "Gangrel Dam",
    "DAM-PAREECHU": "Parechu River",
    "DAM-TEESTA-V": "Teesta V Dam",
    "DAM-GANDHI-SAGAR": "Gandhi Sagar Dam, Bhanpura"
}

headers = {'User-Agent': 'JalRakshaDamAuditor2/1.0'}
res = {}

for did, q in remaining_queries.items():
    url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(q)}&format=json&limit=1"
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read().decode('utf-8'))
            if data:
                res[did] = {
                    "lat": round(float(data[0]['lat']), 5),
                    "lon": round(float(data[0]['lon']), 5),
                    "name": data[0].get('display_name', '')[:70]
                }
            else:
                res[did] = "Not found"
    except Exception as e:
        res[did] = str(e)

with open("tools/remaining_dams.json", "w") as f:
    json.dump(res, f, indent=2)
print("Finished remaining dams query.")
