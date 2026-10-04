import json
import time
import urllib.request
import urllib.parse
from app.services.major_dams import MAJOR_DAMS

# We can query OSM for each dam and compare with current catalog
results = []
headers = {'User-Agent': 'JalRakshaDamAuditor/1.0 (dam-safety-research@jalraksha.gov.in)'}

queries = {
    "DAM-TEHRI": "Tehri Dam, Uttarakhand",
    "DAM-KOTESHWAR": "Koteshwar Dam, Uttarakhand",
    "DAM-RAMGANGA": "Ramganga Dam, Uttarakhand",
    "DAM-LAKHWAR": "Lakhwar Dam, Uttarakhand",
    "DAM-DHAULIGANGA": "Dhauliganga Dam, Uttarakhand",
    "DAM-BHAKRA": "Bhakra Dam, Himachal Pradesh",
    "DAM-PONG": "Pong Dam, Himachal Pradesh",
    "DAM-CHAMERA": "Chamera Dam, Himachal Pradesh",
    "DAM-KOLDAM": "Koldam, Himachal Pradesh",
    "DAM-NATHPA-JHAKRI": "Nathpa Jhakri Dam, Himachal Pradesh",
    "DAM-BAGLIHAR": "Baglihar Dam, Jammu and Kashmir",
    "DAM-SALAL": "Salal Dam, Jammu and Kashmir",
    "DAM-URI": "Uri Dam, Jammu and Kashmir",
    "DAM-SARDAR-SAROVAR": "Sardar Sarovar Dam, Gujarat",
    "DAM-UKAI": "Ukai Dam, Gujarat",
    "DAM-KADANA": "Kadana Dam, Gujarat",
    "DAM-DHAROI": "Dharoi Dam, Gujarat",
    "DAM-KOYNA": "Koyna Dam, Maharashtra",
    "DAM-JAYAKWADI": "Jayakwadi Dam, Maharashtra",
    "DAM-UJJANI": "Ujjani Dam, Maharashtra",
    "DAM-BHATSA": "Bhatsa Dam, Maharashtra",
    "DAM-INDIRA-SAGAR": "Indira Sagar Dam, Madhya Pradesh",
    "DAM-GANDHI-SAGAR": "Gandhi Sagar Dam, Madhya Pradesh",
    "DAM-BANSAGAR": "Bansagar Dam, Madhya Pradesh",
    "DAM-BARGI": "Bargi Dam, Madhya Pradesh",
    "DAM-TAWA": "Tawa Dam, Madhya Pradesh",
    "DAM-RANA-PRATAP-SAGAR": "Rana Pratap Sagar Dam, Rajasthan",
    "DAM-BISALPUR": "Bisalpur Dam, Rajasthan",
    "DAM-MAHI-BAJAJ": "Mahi Bajaj Sagar Dam, Rajasthan",
    "DAM-HIRAKUD": "Hirakud Dam, Odisha",
    "DAM-RENGALI": "Rengali Dam, Odisha",
    "DAM-INDRAVATI": "Upper Indravati Dam, Odisha",
    "DAM-NAGARJUNA-SAGAR": "Nagarjuna Sagar Dam, Andhra Pradesh",
    "DAM-SRISAILAM": "Srisailam Dam, Andhra Pradesh",
    "DAM-POLAVARAM": "Polavaram Dam, Andhra Pradesh",
    "DAM-TUNGABHADRA": "Tungabhadra Dam, Karnataka",
    "DAM-ALMATTI": "Almatti Dam, Karnataka",
    "DAM-KRS": "Krishna Raja Sagara Dam, Karnataka",
    "DAM-SUPA": "Supa Dam, Karnataka",
    "DAM-LINGANAMAKKI": "Linganamakki Dam, Karnataka",
    "DAM-IDUKKI": "Idukki Dam, Kerala",
    "DAM-CHERUTHONI": "Cheruthoni Dam, Kerala",
    "DAM-MULLAPERIYAR": "Mullaperiyar Dam, Kerala",
    "DAM-MALAMPUZHA": "Malampuzha Dam, Kerala",
    "DAM-SHOLAYAR": "Sholayar Dam, Kerala",
    "DAM-METTUR": "Mettur Dam, Tamil Nadu",
    "DAM-BHAVANISAGAR": "Bhavanisagar Dam, Tamil Nadu",
    "DAM-VAIGAI": "Vaigai Dam, Tamil Nadu",
    "DAM-RIHAND": "Rihand Dam, Uttar Pradesh",
    "DAM-MATATILA": "Matatila Dam, Uttar Pradesh",
    "DAM-KOSI-BARRAGE": "Kosi Barrage, Nepal",
    "DAM-MAITHON": "Maithon Dam, Jharkhand",
    "DAM-PANCHET": "Panchet Dam, Jharkhand",
    "DAM-KANGSABATI": "Kangsabati Dam, West Bengal",
    "DAM-FARAKKA": "Farakka Barrage, West Bengal",
    "DAM-TEESTA-V": "Teesta V Dam, Sikkim",
    "DAM-SOUTH-LHONAK": "South Lhonak Lake, Sikkim",
    "DAM-SUBANSIRI": "Subansiri Lower Dam, Arunachal Pradesh",
    "DAM-UMIAM": "Umiam Dam, Meghalaya",
    "DAM-DOYANG": "Doyang Dam, Nagaland",
    "DAM-HASDEO-BANGO": "Hasdeo Bango Dam, Chhattisgarh",
    "DAM-GANGREL": "Gangrel Dam, Chhattisgarh",
    "DAM-RISHIGANGA": "Rishi Ganga, Chamoli, Uttarakhand",
    "DAM-GYA": "Gya, Ladakh",
    "DAM-PAREECHU": "Parechu River, Himachal Pradesh"
}

out = {}
for dam in MAJOR_DAMS:
    did = dam["id"]
    q = queries.get(did, f"{dam['name']}, India")
    url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(q)}&format=json&limit=1"
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            if data:
                lat = float(data[0]['lat'])
                lon = float(data[0]['lon'])
                name = data[0].get('display_name', '')
                out[did] = {
                    "catalog_lat": dam["lat"],
                    "catalog_lon": dam["lon"],
                    "osm_lat": round(lat, 5),
                    "osm_lon": round(lon, 5),
                    "osm_name": name[:60],
                    "dist_km": round(((lat - dam["lat"])**2 + (lon - dam["lon"])**2)**0.5 * 111, 2)
                }
            else:
                out[did] = {"error": "Not found"}
    except Exception as e:
        out[did] = {"error": str(e)}
    time.sleep(1.0) # Respect OSM Nominatim 1 req/sec rate limit

with open("tools/osm_dam_coords.json", "w") as f:
    json.dump(out, f, indent=2)
print("Finished checking OSM coordinates.")
