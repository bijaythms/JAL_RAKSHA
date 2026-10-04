import urllib.request
import json

req = urllib.request.Request('http://127.0.0.1:8000/api/incidents?limit=100')
res = json.loads(urllib.request.urlopen(req).read().decode('utf-8'))
print(f"Total incidents returned: {len(res['items'])}")

sample_keys = ['Cheruthoni', 'Idukki', 'Mullaperiyar', 'Mettur', 'Tehri', 'Bhakra', 'Hirakud', 'Lakhwar', 'Bisalpur', 'Sardar Sarovar', 'Nagarjuna']
for item in res['items']:
    name = item['name']
    if any(k.lower() in name.lower() for k in sample_keys):
        print(f"  {item['id']} {name:<50} ({item['lat']:.4f}, {item['lon']:.4f})")
