import urllib.request, json, time

base = 'http://127.0.0.1:8000'
req = urllib.request.Request(base + '/api/auth/token',
    data=json.dumps({'username': 'admin', 'password': 'admin123'}).encode(),
    headers={'Content-Type': 'application/json'})
token = json.loads(urllib.request.urlopen(req).read()).get('token', '')

sim_payload = {
    'scenario': 'major',
    'stored_volume_m3': 1996000000,
    'lake_area_m2': 60000000,
    'dam_height_m': 168.91,
    'dam_crest_len_m': 366,
    'breach_width_m': 100,
    'breach_depth_m': 80,
    'breach_time_hr': 1.5,
    'inflow_m3s': 1200,
    'dam_material': 'Concrete'
}

req2 = urllib.request.Request(
    base + '/api/simulations?incident_id=JR-20260929-22F604',
    data=json.dumps(sim_payload).encode(),
    headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token},
    method='POST'
)
d2 = json.loads(urllib.request.urlopen(req2).read())
sim_id = d2['simulation_id']
print('Created simulation:', sim_id)

for _ in range(40):
    time.sleep(2)
    req3 = urllib.request.Request(base + '/api/simulations/' + sim_id, headers={'Authorization': 'Bearer ' + token})
    s = json.loads(urllib.request.urlopen(req3).read())
    if s.get('status') == 'DONE':
        res = s.get('results', {})
        print('STATUS: DONE!')
        settlements = res.get('exposure', {}).get('settlements', [])
        print(f'Total settlements exposed: {len(settlements)}')
        for st in settlements:
            print(f"  {st['name']}: Pop={st['population']}, Arrival={st.get('arrival_min')} min, Depth={st.get('max_depth_m')} m")
        impacts = res.get('visual', {}).get('impact', [])
        print(f'\nTotal visual impacts: {len(impacts)}')
        for imp in impacts:
            print(f"  {imp['name']} ({imp['kind']}): Arr={imp.get('arrival_min')} min, Depth={imp.get('peak_depth_m')} m, Hazard={imp.get('people_hazard')}")
        break
