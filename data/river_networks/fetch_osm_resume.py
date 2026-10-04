"""
Resume OSM fetch - only fetch dams that don't yet have real OSM data.
Runs in small batches of 5, with 30s pauses between batches.
"""
import urllib.request, urllib.parse, json, math, time, sys
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

OVERPASS_MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]
OUT_DIR = Path("data/river_networks")

def is_real_osm(nodes):
    """True if node step variance > 0.05 (not simulated uniform steps)."""
    if len(nodes) < 10: return False
    steps = [math.sqrt(((nodes[i+1][0]-nodes[i][0])*111)**2 +
             ((nodes[i+1][1]-nodes[i][1])*111*math.cos(math.radians(nodes[i][0])))**2)
             for i in range(min(30, len(nodes)-1))]
    return (max(steps)-min(steps)) > 0.05

def overpass_query(query, timeout=60):
    data = urllib.parse.urlencode({"data": query}).encode()
    for mirror in OVERPASS_MIRRORS:
        for attempt in range(3):
            wait = 5 * (attempt + 1)
            try:
                req = urllib.request.Request(mirror, data=data,
                    headers={"User-Agent": "JalRaksha/2.0 (dam-safety research)",
                             "Content-Type": "application/x-www-form-urlencoded"})
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    return json.loads(r.read().decode())
            except Exception as e:
                print(f"    [{mirror[:30]}] attempt {attempt+1}: {type(e).__name__}: {str(e)[:60]}")
                time.sleep(wait)
    return {"elements": []}

def extract_nodes(elements, start_lat, start_lon, max_km=70):
    node_map = {el["id"]: (el["lat"], el["lon"]) for el in elements if el["type"] == "node"}
    ways = []
    for el in elements:
        if el["type"] == "way" and "nodes" in el:
            pts = [node_map[n] for n in el["nodes"] if n in node_map]
            if len(pts) >= 2: ways.append(pts)
    if not ways: return []

    def dm(a, b):
        return math.sqrt(((a[0]-b[0])*111000)**2 + ((a[1]-b[1])*111000*math.cos(math.radians((a[0]+b[0])/2)))**2)

    bi, bd, br = 0, float("inf"), False
    for i, w in enumerate(ways):
        d1 = dm((start_lat, start_lon), w[0]); d2 = dm((start_lat, start_lon), w[-1])
        if d1 < bd: bd=d1; bi=i; br=False
        if d2 < bd: bd=d2; bi=i; br=True

    chain = ways[bi][::-1] if br else list(ways[bi])
    used = {bi}
    for _ in range(len(ways)):
        tail = chain[-1]; bj, bd2, br2 = None, 1500, False
        for i, w in enumerate(ways):
            if i in used: continue
            d1=dm(tail,w[0]); d2=dm(tail,w[-1])
            if d1<bd2: bd2=d1; bj=i; br2=False
            if d2<bd2: bd2=d2; bj=i; br2=True
        if bj is None: break
        seg = ways[bj][::-1] if br2 else ways[bj]
        chain.extend(seg[1:]); used.add(bj)

    result = [[round(p[0],5), round(p[1],5)] for p in chain]
    cum = 0.0; out = [result[0]]
    for i in range(1, len(result)):
        cum += dm(result[i-1], result[i])/1000
        out.append(result[i])
        if cum >= max_km: break
    return out if len(out) >= 15 else []

def fetch_dam(iid, name, lat, lon, river_names, bbox, max_km):
    south, north = lat-bbox, lat+bbox
    west, east = lon-bbox, lon+bbox
    for rname in river_names:
        print(f"    trying '{rname}'...")
        q = f"""[out:json][timeout:60];(
  way[waterway=river][name="{rname}"]({south},{west},{north},{east});
  way[waterway=river]["name:en"="{rname}"]({south},{west},{north},{east});
);out body;>;out skel qt;"""
        d = overpass_query(q)
        nodes = extract_nodes(d["elements"], lat, lon, max_km)
        time.sleep(3)
        if nodes and len(nodes) >= 20:
            print(f"    -> {len(nodes)} nodes ('{rname}')")
            return nodes
    # generic fallback
    print(f"    trying generic waterway=river bbox...")
    q = f"""[out:json][timeout:60];(way[waterway=river]({south},{west},{north},{east}););out body;>;out skel qt;"""
    d = overpass_query(q)
    nodes = extract_nodes(d["elements"], lat, lon, max_km)
    time.sleep(3)
    if nodes: print(f"    -> {len(nodes)} nodes (generic)")
    return nodes

DAMS = [
    ("JR-20260929-B472A4","Dhauliganga",29.9667,80.3333,["Dhauliganga","Dhauli Ganga","Gori Ganga"],1.0,60),
    ("JR-20260929-E1868E","Rishiganga",30.4835,79.7215,["Dhauliganga","Rishiganga","Pindar"],0.8,50),
    ("JR-20260929-69A72B","Bhakra",31.4111,76.4338,["Sutlej","Satluj"],1.0,70),
    ("JR-20260929-CE8881","Pong Dam",32.0089,75.9378,["Beas","Vipasha"],1.2,70),
    ("JR-20260929-6E7C8C","Chamera",32.4571,76.1303,["Ravi","Iravati"],1.2,70),
    ("JR-20260929-E710BD","Koldam",31.6433,76.6667,["Sutlej","Satluj"],0.8,60),
    ("JR-20260929-255CCE","Nathpa Jhakri",31.5500,77.8500,["Sutlej","Satluj"],1.0,60),
    ("JR-20260929-1069C1","Pareechu",31.9505,78.5805,["Sutlej","Spiti River","Spiti"],1.2,70),
    ("JR-20260929-0FD860","Baglihar",33.0958,75.5000,["Chenab","Chandrabhaga"],1.2,70),
    ("JR-20260929-258818","Salal",33.0722,74.8236,["Chenab","Chandrabhaga"],1.0,60),
    ("JR-20260929-4CA1B4","Uri",34.0961,74.0531,["Jhelum","Vitasta"],1.0,60),
    ("JR-20260929-6ECF59","Sardar Sarovar",21.8306,73.7468,["Narmada"],1.0,70),
    ("JR-20260929-2537AE","Ukai",21.2500,73.6000,["Tapi","Tapti"],1.0,60),
    ("JR-20260929-923269","Kadana",23.2667,73.7333,["Mahi","Mahi River"],1.0,60),
    ("JR-20260929-92599E","Dharoi",23.8333,72.7833,["Sabarmati","Sabarmatī"],1.0,60),
    ("JR-20260929-F5D473","Gandhi Sagar",24.7178,75.5703,["Chambal River","Chambal"],1.2,70),
    ("JR-20260929-46EF66","Rana Pratap Sagar",24.9667,75.5833,["Chambal River","Chambal"],1.0,60),
    ("JR-20260929-398DD0","Bisalpur",26.0167,75.3333,["Banas","Banas River"],1.2,70),
    ("JR-20260929-8C75E2","Mahi Bajaj Sagar",23.9861,74.0706,["Mahi","Mahi River"],1.0,60),
    ("JR-20260929-6321F9","Indira Sagar",22.3456,76.4573,["Narmada"],1.0,70),
    ("JR-20260929-E221E1","Bansagar",24.1981,81.4422,["Son","Son River","Sone"],1.2,70),
    ("JR-20260929-338E8E","Bargi",22.9764,79.9347,["Narmada"],0.8,60),
    ("JR-20260929-EC7E42","Tawa",22.6139,78.0008,["Tawa","Tawa River","Narmada"],1.0,60),
    ("JR-20260929-9ADA3B","Koyna",17.3951,73.7518,["Koyna","Koyna River"],1.0,60),
    ("JR-20260929-03807A","Jayakwadi",19.4333,75.4333,["Godavari","Gautami"],1.2,70),
    ("JR-20260929-711288","Ujjani",18.0167,74.7167,["Bhima","Bhima River"],1.2,70),
    ("JR-20260929-C6F11A","Bhatsa",19.4797,73.4408,["Bhatsa","Ulhas","Bhatsa River"],1.0,55),
    ("JR-20260929-E89E69","Hirakud",21.5373,83.8667,["Mahanadi","Mahanadi River"],1.2,80),
    ("JR-20260929-F1D819","Rengali",21.0000,84.9000,["Brahmani","Brahmani River"],1.0,60),
    ("JR-20260929-FBE6AF","Upper Indravati",19.6167,83.0167,["Indravati","Indravati River"],1.2,70),
    ("JR-20260929-C25704","Nagarjuna Sagar",16.5745,79.3219,["Krishna","Krishna River"],1.2,70),
    ("JR-20260929-88230C","Srisailam",16.0978,78.8847,["Krishna","Krishna River"],1.0,60),
    ("JR-20260929-1191C9","Polavaram",17.2508,81.7017,["Godavari","Gautami"],1.0,60),
    ("JR-20260929-EDF330","Tungabhadra",15.2667,76.3333,["Tungabhadra","Tungabhadra River"],1.2,70),
    ("JR-20260929-49B7B0","Almatti",16.3325,76.0753,["Krishna","Krishna River"],1.2,70),
    ("JR-20260929-F32A42","KRS",12.4237,76.5686,["Kaveri","Cauvery"],1.2,70),
    ("JR-20260929-26E57E","Supa",15.0500,74.4000,["Kali","Kali River","Kalinadi"],0.8,55),
    ("JR-20260929-5AE578","Linganamakki",14.0167,74.9000,["Sharavathi","Sharavati"],0.8,55),
    ("JR-20260929-22F604","Idukki",9.8439,76.9762,["Periyar","Periyar River"],0.6,50),
    ("JR-20260929-5A298A","Cheruthoni",9.8439,76.9762,["Periyar","Cheruthoni River"],0.6,50),
    ("JR-20260929-4141CC","Mullaperiyar",9.5286,77.1441,["Periyar","Periyar River"],0.8,55),
    ("JR-20260929-94E84B","Malampuzha",10.8500,76.6500,["Bharathapuzha","Nila","Bharatapuzha"],1.0,60),
    ("JR-20260929-F0E423","Lower Sholayar",10.2833,76.7000,["Chalakudy River","Chalakudy","Periyar"],0.8,50),
    ("JR-20260929-75CD79","Mettur",11.7861,77.8006,["Kaveri","Cauvery"],1.2,70),
    ("JR-20260929-862368","Bhavanisagar",11.4167,77.1333,["Bhavani","Bhavani River"],1.0,60),
    ("JR-20260929-643618","Vaigai",10.0500,77.5500,["Vaigai","Vaigai River"],1.0,60),
    ("JR-20260929-0E5211","Rihand",24.1981,82.9803,["Rihand","Rihand River","Son"],1.0,60),
    ("JR-20260929-E652E3","Matatila",25.1037,78.3683,["Betwa","Betwa River"],1.2,70),
    ("JR-20260929-0BAE84","Kosi Barrage",26.5262,86.9271,["Kosi","Koshi","Kosi River"],1.2,70),
    ("JR-20260929-8BF5A0","Maithon",23.7845,86.8125,["Barakar River","Barakar","Damodar"],1.0,60),
    ("JR-20260929-989BE8","Panchet",23.6810,86.7473,["Damodar","Damodar River"],1.0,60),
    ("JR-20260929-8682BA","Kangsabati",22.9639,86.7889,["Kangsabati","Kansabati","Kasai"],1.0,60),
    ("JR-20260929-02BA50","Farakka",24.8048,87.9336,["Ganges","Ganga","Bhagirathi"],1.0,60),
    ("JR-20260929-E255B1","Teesta-V",27.3867,88.5034,["Teesta","Tista"],0.8,55),
    ("JR-20260929-B3D64D","South Lhonak",27.9144,88.1836,["Teesta","Tista","Lhonak Chu"],1.2,70),
    ("JR-20260929-0BA8E8","Subansiri Lower",27.5536,94.2586,["Subansiri","Subansiri River"],1.2,70),
    ("JR-20260929-749864","Umiam",25.6594,91.9002,["Umiam","Umiam River","Umtrew"],0.8,50),
    ("JR-20260929-E58284","Doyang",26.2323,94.2609,["Doyang","Doyang River","Dhansiri"],1.0,60),
    ("JR-20260929-25CEFE","Hasdeo Bango",22.6050,82.5980,["Hasdeo","Hasdeo River"],1.0,60),
    ("JR-20260929-B28772","Gangrel",20.6267,81.5600,["Mahanadi","Mahanadi River"],1.0,60),
    ("JR-20260929-C520AA","Gya Lake",33.6530,77.7350,["Indus","Sindhu"],1.0,60),
]

BATCH = 5
BATCH_PAUSE = 20

if __name__ == "__main__":
    ok = []; failed = []
    # Filter: only fetch dams that don't already have real OSM data
    todo = []
    for row in DAMS:
        iid = row[0]
        f = OUT_DIR / f"{iid}.json"
        if f.exists():
            d = json.loads(f.read_text())
            if is_real_osm(d):
                print(f"  SKIP (real OSM {len(d)}pts): {row[1]}")
                ok.append(iid)
                continue
        todo.append(row)

    print(f"\n{len(todo)} dams need fetching, {len(ok)} already have real OSM data\n")

    for bi in range(0, len(todo), BATCH):
        batch = todo[bi:bi+BATCH]
        print(f"\n=== Batch {bi//BATCH+1}/{(len(todo)+BATCH-1)//BATCH} ===")
        for iid, name, lat, lon, rivers, bbox, max_km in batch:
            print(f"\n  {name} ({iid})")
            nodes = fetch_dam(iid, name, lat, lon, rivers, bbox, max_km)
            if nodes and len(nodes) >= 20 and is_real_osm(nodes):
                (OUT_DIR / f"{iid}.json").write_text(json.dumps(nodes, indent=2))
                ok.append(iid)
                print(f"  -> SAVED {len(nodes)} real nodes")
            else:
                failed.append((iid, name))
                print(f"  -> FAILED (got {len(nodes) if nodes else 0} nodes)")

        if bi + BATCH < len(todo):
            print(f"\nBatch done. Pausing {BATCH_PAUSE}s before next batch...")
            sys.stdout.flush()
            time.sleep(BATCH_PAUSE)

    print(f"\n{'='*50}")
    print(f"DONE: {len(ok)} real OSM, {len(failed)} failed")
    if failed:
        for iid, name in failed:
            print(f"  FAILED: {iid}  {name}")
