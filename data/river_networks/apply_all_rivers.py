import json
import os
from app.db import SessionLocal, Incident

def apply_all_rivers():
    db = SessionLocal()
    incidents = db.query(Incident).filter(Incident.name.like('[MAJOR DAM]%')).all()
    updated_count = 0
    
    for inc in incidents:
        filename = f'data/river_networks/{inc.id}.json'
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                coords = json.load(f)
                if len(coords) >= 150:
                    inc.centerline = json.dumps(coords)
                    updated_count += 1
                    
    db.commit()
    print(f'Updated {updated_count} incidents in database.')
    db.close()
    
if __name__ == '__main__':
    apply_all_rivers()
