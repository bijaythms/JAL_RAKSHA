"""
Fetch real river centerlines from OpenStreetMap Overpass API for all major Indian dams.
Forced re-fetch — no cache skip. Uses multiple name fallbacks per river.
"""
import urllib.request
import urllib.parse
import json
import math
import time
import sys
from pathlib import Path

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OUT_DIR = Path("data/river_networks")
OUT_DIR.mkdir(exist_ok=True)

def overpass_query(query: str, retries=4) -> dict:
    data = urllib.parse.urlencode({"data": query}).encode()
    for attempt in range(retries):
        wait = 4 * (attempt + 1)
        try:
            req = urllib.request.Request(OVERPASS_URL, data=data,
                headers={"User-Agent": "JalRaksha-RiverSurvey/1.0",
                         "Content-Type": "application/x-www-form-urlencoded"})
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            print(f"    Attempt {attempt+1} failed ({e}), wait {wait}s...")
            time.sleep(wait)
    return {"elements": []}

def extract_river_nodes(elements, start_lat, start_lon, max_km=70.0):
    node_map = {}
    for el in elements:
        if el["type"] == "node":
            node_map[el["id"]] = (el["lat"], el["lon"])

    ways = []
    for el in elements:
        if el["type"] == "way" and "nodes" in el:
            pts = [node_map[nid] for nid in el["nodes"] if nid in node_map]
            if len(pts) >= 2:
                ways.append(pts)

    if not ways:
        return []

    def dist_m(a, b):
        dlat = (a[0] - b[0]) * 111000
        dlon = (a[1] - b[1]) * 111000 * math.cos(math.radians((a[0]+b[0])/2))
        return math.sqrt(dlat**2 + dlon**2)

    # Find the way closest to the dam (start point)
    best_idx, best_d, best_rev = 0, float("inf"), False
    for i, w in enumerate(ways):
        d1 = dist_m((start_lat, start_lon), w[0])
        d2 = dist_m((start_lat, start_lon), w[-1])
        if d1 < best_d: best_d = d1; best_idx = i; best_rev = False
        if d2 < best_d: best_d = d2; best_idx = i; best_rev = True

    chain = list(ways[best_idx])
    if best_rev:
        chain = chain[::-1]

    used = {best_idx}
    for _ in range(len(ways)):
        tail = chain[-1]
        bj, bd, br = None, 1500, False  # max 1.5km gap to stitch
        for i, w in enumerate(ways):
            if i in used: continue
            d1 = dist_m(tail, w[0])
            d2 = dist_m(tail, w[-1])
            if d1 < bd: bd = d1; bj = i; br = False
            if d2 < bd: bd = d2; bj = i; br = True
        if bj is None: break
        seg = ways[bj]; 
        if br: seg = seg[::-1]
        chain.extend(seg[1:]); used.add(bj)

    result = [[round(p[0], 5), round(p[1], 5)] for p in chain]

    # Trim to max_km
    cum = 0.0; trimmed = [result[0]]
    for i in range(1, len(result)):
        cum += dist_m(result[i-1], result[i]) / 1000.0
        trimmed.append(result[i])
        if cum >= max_km: break

    return trimmed if len(trimmed) >= 15 else []


def fetch_river(dam_name, lat, lon, river_names, bbox=1.2, max_km=70):
    """Try multiple river name alternatives until we get data."""
    south, north = lat - bbox, lat + bbox
    west, east   = lon - bbox, lon + bbox

    for rname in river_names:
        print(f"    Trying '{rname}'...")
        # Build query with multiple name tags
        query = f"""
[out:json][timeout:90];
(
  way[waterway=river][name="{rname}"]({south},{west},{north},{east});
  way[waterway=river]["name:en"="{rname}"]({south},{west},{north},{east});
  way[waterway=canal][name="{rname}"]({south},{west},{north},{east});
);
out body;
>;
out skel qt;
"""
        data = overpass_query(query)
        nodes = extract_river_nodes(data["elements"], lat, lon, max_km=max_km)
        time.sleep(2)
        if nodes and len(nodes) >= 20:
            print(f"    -> {len(nodes)} nodes with name '{rname}'")
            return nodes

    # Final fallback: any waterway=river within bbox
    print(f"    Trying generic waterway=river fallback in bbox...")
    query = f"""
[out:json][timeout:90];
(
  way[waterway=river]({south},{west},{north},{east});
);
out body;
>;
out skel qt;
"""
    data = overpass_query(query)
    nodes = extract_river_nodes(data["elements"], lat, lon, max_km=max_km)
    time.sleep(2)
    if nodes:
        print(f"    -> {len(nodes)} nodes (generic fallback)")
    return nodes


# ─── DAM LIST ──────────────────────────────────────────────────────────────
# (incident_id, dam_label, lat, lon, [river name alternatives], bbox, max_km)
DAMS = [
    # UTTARAKHAND
    ("JR-20260929-4DF716", "Koteshwar",       30.2070, 78.4775, ["Bhagirathi River","Bhagirathi","Ganga","Ganges"], 0.8, 50),
    ("JR-20260929-B3F09A", "Ramganga Kalagarh",29.4937,78.8819, ["Ramganga","Ram Ganga"], 1.2, 70),
    ("JR-20260929-192A20", "Lakhwar",          30.6500, 77.8167, ["Yamuna","Yamunotri"], 1.0, 60),
    ("JR-20260929-B472A4", "Dhauliganga",      29.9667, 80.3333, ["Dhauliganga","Dhauli Ganga","Gori"], 1.0, 60),
    ("JR-20260929-E1868E", "Rishiganga",       30.4835, 79.7215, ["Dhauliganga","Rishiganga","Rishi Ganga"], 0.8, 50),

    # HIMACHAL PRADESH
    ("JR-20260929-69A72B", "Bhakra",           31.4111, 76.4338, ["Sutlej","Satluj"], 1.0, 70),
    ("JR-20260929-CE8881", "Pong Dam",         32.0089, 75.9378, ["Beas","Vipasha"], 1.2, 70),
    ("JR-20260929-6E7C8C", "Chamera",          32.4571, 76.1303, ["Ravi","Iravati"], 1.2, 70),
    ("JR-20260929-E710BD", "Koldam",           31.6433, 76.6667, ["Sutlej","Satluj"], 0.8, 60),
    ("JR-20260929-255CCE", "Nathpa Jhakri",    31.5500, 77.8500, ["Sutlej","Satluj"], 1.0, 60),
    ("JR-20260929-1069C1", "Pareechu",         31.9505, 78.5805, ["Sutlej","Satluj","Spiti River","Spiti"], 1.2, 70),

    # JAMMU & KASHMIR
    ("JR-20260929-0FD860", "Baglihar",         33.0958, 75.5000, ["Chenab","Chandrabhaga"], 1.2, 70),
    ("JR-20260929-258818", "Salal",            33.0722, 74.8236, ["Chenab","Chandrabhaga"], 1.0, 60),
    ("JR-20260929-4CA1B4", "Uri",              34.0961, 74.0531, ["Jhelum","Jhelam","Vitasta"], 1.0, 60),

    # GUJARAT
    ("JR-20260929-6ECF59", "Sardar Sarovar",   21.8306, 73.7468, ["Narmada","Narmadā"], 1.0, 70),
    ("JR-20260929-2537AE", "Ukai",             21.2500, 73.6000, ["Tapi","Tapti"], 1.0, 60),
    ("JR-20260929-923269", "Kadana",           23.2667, 73.7333, ["Mahi","Mahi River"], 1.0, 60),
    ("JR-20260929-92599E", "Dharoi",           23.8333, 72.7833, ["Sabarmati","Sabarmatī"], 1.0, 60),

    # RAJASTHAN
    ("JR-20260929-F5D473", "Gandhi Sagar",     24.7178, 75.5703, ["Chambal River","Chambal","Charmanvati"], 1.2, 70),
    ("JR-20260929-46EF66", "Rana Pratap Sagar",24.9667, 75.5833, ["Chambal River","Chambal"], 1.0, 60),
    ("JR-20260929-398DD0", "Bisalpur",         26.0167, 75.3333, ["Banas","Banas River"], 1.2, 70),
    ("JR-20260929-8C75E2", "Mahi Bajaj Sagar", 23.9861, 74.0706, ["Mahi","Mahi River"], 1.0, 60),

    # MADHYA PRADESH
    ("JR-20260929-6321F9", "Indira Sagar",     22.3456, 76.4573, ["Narmada","Narmadā"], 1.0, 70),
    ("JR-20260929-E221E1", "Bansagar",         24.1981, 81.4422, ["Son","Son River","Sone"], 1.2, 70),
    ("JR-20260929-338E8E", "Bargi",            22.9764, 79.9347, ["Narmada","Narmadā"], 0.8, 60),
    ("JR-20260929-EC7E42", "Tawa",             22.6139, 78.0008, ["Tawa","Tawa River","Narmada"], 1.0, 60),

    # MAHARASHTRA
    ("JR-20260929-9ADA3B", "Koyna",            17.3951, 73.7518, ["Koyna","Koyna River"], 1.0, 60),
    ("JR-20260929-03807A", "Jayakwadi",        19.4333, 75.4333, ["Godavari","Gautami"], 1.2, 70),
    ("JR-20260929-711288", "Ujjani",           18.0167, 74.7167, ["Bhima","Bhima River"], 1.2, 70),
    ("JR-20260929-C6F11A", "Bhatsa",           19.4797, 73.4408, ["Bhatsa","Bhatsa River","Ulhas"], 1.0, 55),

    # ODISHA
    ("JR-20260929-E89E69", "Hirakud",          21.5373, 83.8667, ["Mahanadi","Mahānadi","Mahanandi"], 1.2, 80),
    ("JR-20260929-F1D819", "Rengali",          21.0000, 84.9000, ["Brahmani","Brahmani River","Vaitarani"], 1.0, 60),
    ("JR-20260929-FBE6AF", "Upper Indravati",  19.6167, 83.0167, ["Indravati","Indravati River"], 1.2, 70),

    # ANDHRA PRADESH / TELANGANA
    ("JR-20260929-C25704", "Nagarjuna Sagar",  16.5745, 79.3219, ["Krishna","Krishna River","Krishnaveni"], 1.2, 70),
    ("JR-20260929-88230C", "Srisailam",        16.0978, 78.8847, ["Krishna","Krishna River"], 1.0, 60),
    ("JR-20260929-1191C9", "Polavaram",        17.2508, 81.7017, ["Godavari","Gautami","Godāvari"], 1.0, 60),

    # KARNATAKA
    ("JR-20260929-EDF330", "Tungabhadra",      15.2667, 76.3333, ["Tungabhadra","Tungabhadrā"], 1.2, 70),
    ("JR-20260929-49B7B0", "Almatti",          16.3325, 76.0753, ["Krishna","Krishna River"], 1.2, 70),
    ("JR-20260929-F32A42", "KRS",              12.4237, 76.5686, ["Kaveri","Cauvery","Kāveri"], 1.2, 70),
    ("JR-20260929-26E57E", "Supa",             15.0500, 74.4000, ["Kali","Kali River","Kalinadi"], 0.8, 55),
    ("JR-20260929-5AE578", "Linganamakki",     14.0167, 74.9000, ["Sharavathi","Sharavati","Sharvati"], 0.8, 55),

    # KERALA
    ("JR-20260929-22F604", "Idukki",            9.8439, 76.9762, ["Periyar","Periyar River","Periār"], 0.6, 50),
    ("JR-20260929-5A298A", "Cheruthoni",        9.8439, 76.9762, ["Periyar","Cheruthoni","Cheruthoni River"], 0.6, 50),
    ("JR-20260929-4141CC", "Mullaperiyar",      9.5286, 77.1441, ["Periyar","Periyar River"], 0.8, 55),
    ("JR-20260929-94E84B", "Malampuzha",       10.8500, 76.6500, ["Bharathapuzha","Bharatapuzha","Nila"], 1.0, 60),
    ("JR-20260929-F0E423", "Lower Sholayar",   10.2833, 76.7000, ["Chalakudy River","Chalakudy","Periyar"], 0.8, 50),

    # TAMIL NADU
    ("JR-20260929-75CD79", "Mettur",           11.7861, 77.8006, ["Kaveri","Cauvery","Kāveri"], 1.2, 70),
    ("JR-20260929-862368", "Bhavanisagar",     11.4167, 77.1333, ["Bhavani","Bhavani River"], 1.0, 60),
    ("JR-20260929-643618", "Vaigai",           10.0500, 77.5500, ["Vaigai","Vaigai River"], 1.0, 60),

    # UTTAR PRADESH
    ("JR-20260929-0E5211", "Rihand",           24.1981, 82.9803, ["Rihand","Rihand River","Son"], 1.0, 60),
    ("JR-20260929-E652E3", "Matatila",         25.1037, 78.3683, ["Betwa","Betwa River","Vetravati"], 1.2, 70),

    # BIHAR
    ("JR-20260929-0BAE84", "Kosi Barrage",     26.5262, 86.9271, ["Kosi","Kosi River","Koshi"], 1.2, 70),

    # JHARKHAND / WB
    ("JR-20260929-8BF5A0", "Maithon",          23.7845, 86.8125, ["Barakar River","Barakar","Damodar"], 1.0, 60),
    ("JR-20260929-989BE8", "Panchet",          23.6810, 86.7473, ["Damodar","Damodar River"], 1.0, 60),
    ("JR-20260929-8682BA", "Kangsabati",       22.9639, 86.7889, ["Kangsabati","Kansabati","Kasai"], 1.0, 60),
    ("JR-20260929-02BA50", "Farakka",          24.8048, 87.9336, ["Ganges","Ganga","Bhagirathi"], 1.0, 60),

    # SIKKIM / NE
    ("JR-20260929-E255B1", "Teesta-V",         27.3867, 88.5034, ["Teesta","Tista","Teesta River"], 0.8, 55),
    ("JR-20260929-B3D64D", "South Lhonak",     27.9144, 88.1836, ["Teesta","Tista","Lhonak"], 1.2, 70),
    ("JR-20260929-0BA8E8", "Subansiri Lower",  27.5536, 94.2586, ["Subansiri","Subansiri River"], 1.2, 70),
    ("JR-20260929-749864", "Umiam",            25.6594, 91.9002, ["Umiam","Umiam River","Umtrew"], 0.8, 50),
    ("JR-20260929-E58284", "Doyang",           26.2323, 94.2609, ["Doyang","Doyang River","Dhansiri"], 1.0, 60),

    # CHHATTISGARH
    ("JR-20260929-25CEFE", "Hasdeo Bango",     22.6050, 82.5980, ["Hasdeo","Hasdeo River","Hasdeo Bango"], 1.0, 60),
    ("JR-20260929-B28772", "Gangrel",          20.6267, 81.5600, ["Mahanadi","Mahānadi"], 1.0, 60),

    # LADAKH
    ("JR-20260929-C520AA", "Gya Lake",         33.6530, 77.7350, ["Indus","Sindhu","Indus River"], 1.0, 60),
]


if __name__ == "__main__":
    print(f"Fetching real OSM river data for {len(DAMS)} dams (forced, no cache)...")
    ok = 0; failed = []

    for idx, (iid, name, lat, lon, river_names, bbox, max_km) in enumerate(DAMS):
        print(f"\n[{idx+1}/{len(DAMS)}] {name} -> {river_names[0]}")
        sys.stdout.flush()

        nodes = fetch_river(name, lat, lon, river_names, bbox=bbox, max_km=max_km)
        time.sleep(2)  # polite delay

        if nodes and len(nodes) >= 20:
            out_file = OUT_DIR / f"{iid}.json"
            out_file.write_text(json.dumps(nodes, indent=2))
            ok += 1
            print(f"  SAVED {len(nodes)} real OSM nodes -> {out_file.name}")
        else:
            failed.append((iid, name, river_names[0]))
            print(f"  FAILED: {name} -> will use existing best data")

    print(f"\n{'='*60}")
    print(f"Done: {ok} OK, {len(failed)} failed")
    if failed:
        print("Failed dams:")
        for iid, name, river in failed:
            print(f"  {iid}  {name}  ({river})")

    summary = {"ok": ok, "failed": {iid: f"{name}/{river}" for iid, name, river in failed}}
    (OUT_DIR / "osm_fetch_results.json").write_text(json.dumps(summary, indent=2))
