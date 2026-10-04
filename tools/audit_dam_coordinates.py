import json
from app.services.major_dams import MAJOR_DAMS

print(f"Total dams in catalog: {len(MAJOR_DAMS)}")
for i, d in enumerate(MAJOR_DAMS):
    print(f"{i+1:2d}. {d['id']:<24} {d['name']:<35} ({d['lat']:.4f}, {d['lon']:.4f})  river={d['river']} state={d['state']}")
