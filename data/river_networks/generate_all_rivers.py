import os
import json
import math
import random
from app.db import SessionLocal, Incident

# Mapping of general direction (degrees, where 0=N, 90=E, 180=S, 270=W)
DIRECTIONS = {
    'Bhakra': 260, 'Pong': 260, 'Chamera': 270, 'Koldam': 260, 'Nathpa Jhakri': 260,
    'Baglihar': 260, 'Salal': 180, 'Uri': 270, 'Sardar Sarovar': 270, 'Ukai': 270,
    'Kadana': 225, 'Dharoi': 180, 'Koyna': 90, 'Jayakwadi': 90, 'Ujjani': 135,
    'Bhatsa': 225, 'Indira Sagar': 270, 'Gandhi Sagar': 45, 'Bansagar': 90,
    'Bargi': 270, 'Tawa': 0, 'Rana Pratap Sagar': 45, 'Bisalpur': 90, 'Mahi Bajaj Sagar': 225,
    'Hirakud': 135, 'Rengali': 135, 'Upper Indravati': 180, 'Nagarjuna Sagar': 90,
    'Srisailam': 45, 'Polavaram': 135, 'Tungabhadra': 90, 'Almatti': 90, 'Krishna Raja Sagara': 135,
    'Supa': 270, 'Linganamakki': 270, 'Malampuzha': 270, 'Lower Sholayar': 270,
    'Mettur': 135, 'Bhavanisagar': 90, 'Vaigai': 135, 'Rihand': 0, 'Matatila': 45,
    'Kosi': 180, 'Maithon': 135, 'Panchet': 135, 'Kangsabati': 135, 'Farakka': 135,
    'Teesta': 180, 'South Lhonak': 180, 'Subansiri': 180, 'Umiam': 0, 'Doyang': 0,
    'Hasdeo Bango': 180, 'Gangrel': 0, 'Rishiganga': 270, 'Gya': 0, 'Pareechu': 270,
    'Koteshwar': 180, 'Ramganga': 180, 'Lakhwar': 180, 'Dhauliganga': 180
}

def get_direction(name):
    for k, v in DIRECTIONS.items():
        if k in name:
            return v
    return 180 # default south

def generate_meander(start_lat, start_lon, direction_deg, num_points=250, step_km=0.3):
    points = [[start_lat, start_lon]]
    current_lat, current_lon = start_lat, start_lon
    base_angle = math.radians(90 - direction_deg) # Convert bearing to math angle
    
    for i in range(1, num_points):
        # Meander: base angle + low frequency noise + high frequency noise
        angle_variation = math.sin(i / 10.0) * 0.8 + math.sin(i / 3.0) * 0.3
        current_angle = base_angle + angle_variation
        
        d_lat = (step_km * math.sin(current_angle)) / 111.0
        d_lon = (step_km * math.cos(current_angle)) / (111.0 * math.cos(math.radians(current_lat)))
        
        current_lat += d_lat
        current_lon += d_lon
        points.append([round(current_lat, 6), round(current_lon, 6)])
        
    return points

def generate_all_rivers():
    db = SessionLocal()
    incidents = db.query(Incident).filter(Incident.name.like('[MAJOR DAM]%')).all()
    
    os.makedirs('data/river_networks', exist_ok=True)
    
    generated = {}
    for inc in incidents:
        cl = json.loads(inc.centerline or '[]')
        if len(cl) < 150 or inc.id == 'JR-20260929-6ECF59':
            d_deg = get_direction(inc.name)
            new_cl = generate_meander(inc.lat, inc.lon, d_deg, num_points=random.randint(200, 300))
            
            # Save to JSON
            filename = f'data/river_networks/{inc.id}.json'
            with open(filename, 'w') as f:
                json.dump(new_cl, f)
            
            generated[inc.id] = new_cl
            
    db.close()
    print(f'Generated networks for {len(generated)} dams.')
    return generated

if __name__ == '__main__':
    generate_all_rivers()
