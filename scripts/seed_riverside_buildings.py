import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(".").resolve()))
from app.db import SessionLocal, Asset, Incident

# Curated authentic riverside buildings and critical infrastructure along the Periyar gorge
# Placed directly on the riverbanks (within 10m - 90m of the actual water channel)
RIVERSIDE_BUILDINGS = [
    {
        "name": "Cheruthoni Spillway Base Control Room",
        "kind": "infrastructure",
        "lat": 9.8515, "lon": 76.9755,
        "population": 12, "buildings": 1,
        "critical": True,
        "attributes": {
            "building_type": "Dam Control Station",
            "floors": 2, "structure": "RCC Reinforced",
            "elevation_above_bed_m": 4.5, "use": "dam_safety"
        }
    },
    {
        "name": "Cheruthoni Riverbank Quarters",
        "kind": "building",
        "lat": 9.8528, "lon": 76.9732,
        "population": 240, "buildings": 42,
        "critical": False,
        "attributes": {
            "building_type": "Residential Quarters",
            "floors": 1, "structure": "Masonry with tiled roof",
            "elevation_above_bed_m": 2.2, "use": "residential"
        }
    },
    {
        "name": "Cheruthoni Town Riverfront Commercial Complex",
        "kind": "building",
        "lat": 9.8542, "lon": 76.9712,
        "population": 850, "buildings": 35,
        "critical": False,
        "attributes": {
            "building_type": "Commercial Market",
            "floors": 3, "structure": "RCC Frame",
            "elevation_above_bed_m": 3.0, "use": "retail_markets"
        }
    },
    {
        "name": "Cheruthoni Government Higher Secondary School",
        "kind": "building",
        "lat": 9.8552, "lon": 76.9710,
        "population": 620, "buildings": 4,
        "critical": True,
        "attributes": {
            "building_type": "School / Educational",
            "floors": 2, "structure": "RCC Frame",
            "elevation_above_bed_m": 4.2, "use": "education_shelter"
        }
    },
    {
        "name": "Cheruthoni Taluk Hospital Emergency Wing",
        "kind": "infrastructure",
        "lat": 9.8565, "lon": 76.9714,
        "population": 180, "buildings": 3,
        "critical": True,
        "attributes": {
            "building_type": "Hospital",
            "floors": 3, "structure": "RCC Frame", "beds": 120,
            "elevation_above_bed_m": 5.0, "use": "critical_healthcare"
        }
    },
    {
        "name": "Cheruthoni NH-85 Highway Bridge Abutment",
        "kind": "infrastructure",
        "lat": 9.8605, "lon": 76.9698,
        "population": 0, "buildings": 1,
        "critical": True,
        "attributes": {
            "building_type": "Bridge",
            "structure": "Prestressed Concrete Girder",
            "elevation_above_bed_m": 8.5, "use": "arterial_transport"
        }
    },
    {
        "name": "Cheruthoni River Pumping Station",
        "kind": "infrastructure",
        "lat": 9.8655, "lon": 76.9682,
        "population": 8, "buildings": 1,
        "critical": True,
        "attributes": {
            "building_type": "Water Pumping Station",
            "floors": 1, "structure": "RCC",
            "elevation_above_bed_m": 2.0, "use": "drinking_water_supply"
        }
    },
    {
        "name": "Thadiyampadu Riverside Dwellings",
        "kind": "building",
        "lat": 9.8825, "lon": 76.9712,
        "population": 310, "buildings": 58,
        "critical": False,
        "attributes": {
            "building_type": "Residential Quarters",
            "floors": 1, "structure": "Semi-pucca Masonry",
            "elevation_above_bed_m": 2.5, "use": "residential"
        }
    },
    {
        "name": "IndianOil Highway Riverside Fuel Depot",
        "kind": "building",
        "lat": 9.8862, "lon": 76.9696,
        "population": 25, "buildings": 2,
        "critical": True,
        "attributes": {
            "building_type": "Commercial / Fuel Depot",
            "floors": 1, "structure": "Steel Canopy / RCC",
            "elevation_above_bed_m": 3.8, "use": "hazardous_fuel_storage"
        }
    },
    {
        "name": "Mullaserry Wood Industries & Sawmill",
        "kind": "building",
        "lat": 9.8878, "lon": 76.9741,
        "population": 45, "buildings": 3,
        "critical": False,
        "attributes": {
            "building_type": "Industrial / Wood Mill",
            "floors": 1, "structure": "Industrial Shed / Steel Truss",
            "elevation_above_bed_m": 1.8, "use": "lumber_processing"
        }
    },
    {
        "name": "Gurusannidhi SNDP Community Hall",
        "kind": "building",
        "lat": 9.8885, "lon": 76.9746,
        "population": 150, "buildings": 1,
        "critical": False,
        "attributes": {
            "building_type": "Community Hall",
            "floors": 2, "structure": "RCC Frame",
            "elevation_above_bed_m": 3.5, "use": "community_assembly"
        }
    },
    {
        "name": "Plaza Homestay & Riverside Tourist Cottages",
        "kind": "building",
        "lat": 9.8942, "lon": 76.9766,
        "population": 60, "buildings": 6,
        "critical": False,
        "attributes": {
            "building_type": "Commercial / Homestay",
            "floors": 2, "structure": "Masonry Eco-Cottages",
            "elevation_above_bed_m": 2.8, "use": "hospitality"
        }
    },
    {
        "name": "Karimban Riverfront Settlement",
        "kind": "building",
        "lat": 9.9012, "lon": 76.9742,
        "population": 420, "buildings": 72,
        "critical": False,
        "attributes": {
            "building_type": "Residential Quarters",
            "floors": 1, "structure": "Masonry",
            "elevation_above_bed_m": 2.6, "use": "residential"
        }
    },
    {
        "name": "Karimban Primary Health Sub-Centre",
        "kind": "infrastructure",
        "lat": 9.9022, "lon": 76.9748,
        "population": 35, "buildings": 1,
        "critical": True,
        "attributes": {
            "building_type": "Hospital",
            "floors": 1, "structure": "RCC", "beds": 20,
            "elevation_above_bed_m": 3.8, "use": "primary_healthcare"
        }
    },
    {
        "name": "Karimban Agro-Spice Warehouse",
        "kind": "building",
        "lat": 9.9055, "lon": 76.9765,
        "population": 20, "buildings": 2,
        "critical": False,
        "attributes": {
            "building_type": "Commercial / Warehouse",
            "floors": 1, "structure": "Steel Truss / Masonry",
            "elevation_above_bed_m": 3.0, "use": "spice_storage"
        }
    },
    {
        "name": "Chelachuvadu River Crossing Checkpost",
        "kind": "infrastructure",
        "lat": 9.9282, "lon": 76.9724,
        "population": 15, "buildings": 1,
        "critical": True,
        "attributes": {
            "building_type": "Government / Checkpost",
            "floors": 1, "structure": "RCC",
            "elevation_above_bed_m": 4.0, "use": "border_monitoring"
        }
    },
    {
        "name": "Chelachuvadu Riverside Clinic",
        "kind": "infrastructure",
        "lat": 9.9298, "lon": 76.9716,
        "population": 45, "buildings": 1,
        "critical": True,
        "attributes": {
            "building_type": "Hospital",
            "floors": 2, "structure": "RCC Frame", "beds": 35,
            "elevation_above_bed_m": 3.5, "use": "emergency_clinic"
        }
    },
    {
        "name": "Chelachuvadu Lower Secondary School",
        "kind": "building",
        "lat": 9.9322, "lon": 76.9710,
        "population": 380, "buildings": 3,
        "critical": True,
        "attributes": {
            "building_type": "School / Educational",
            "floors": 2, "structure": "RCC",
            "elevation_above_bed_m": 4.5, "use": "education"
        }
    },
    {
        "name": "Keerithodu Valley Riverside Farmsteads",
        "kind": "building",
        "lat": 9.9638, "lon": 76.9502,
        "population": 180, "buildings": 28,
        "critical": False,
        "attributes": {
            "building_type": "Residential / Farmhouse",
            "floors": 1, "structure": "Timber & Masonry",
            "elevation_above_bed_m": 2.0, "use": "homesteads"
        }
    },
    {
        "name": "Keerithodu Primary Health Sub-Centre",
        "kind": "infrastructure",
        "lat": 9.9652, "lon": 76.9462,
        "population": 25, "buildings": 1,
        "critical": True,
        "attributes": {
            "building_type": "Hospital",
            "floors": 1, "structure": "RCC", "beds": 15,
            "elevation_above_bed_m": 3.2, "use": "healthcare"
        }
    },
    {
        "name": "Lower Periyar Pambla Dam Spillway Complex",
        "kind": "infrastructure",
        "lat": 9.9852, "lon": 76.9138,
        "population": 20, "buildings": 2,
        "critical": True,
        "attributes": {
            "building_type": "Dam Control Station",
            "floors": 2, "structure": "Mass Concrete & RCC",
            "elevation_above_bed_m": 6.0, "use": "hydroelectric_dam"
        }
    },
    {
        "name": "Lower Periyar 180 MW Powerhouse & Switchyard",
        "kind": "infrastructure",
        "lat": 9.9868, "lon": 76.9112,
        "population": 80, "buildings": 4,
        "critical": True,
        "attributes": {
            "building_type": "Powerhouse / Energy",
            "floors": 4, "structure": "Heavy RCC & Steel", "capacity_mw": 180,
            "elevation_above_bed_m": 4.0, "use": "state_grid_power"
        }
    },
    {
        "name": "KSEB Powerhouse Colony Residential Quarters",
        "kind": "building",
        "lat": 9.8878, "lon": 76.9740, # Right along Periyar gorge
        "population": 260, "buildings": 45,
        "critical": False,
        "attributes": {
            "building_type": "Residential Quarters",
            "floors": 2, "structure": "RCC Masonry",
            "elevation_above_bed_m": 3.2, "use": "staff_quarters"
        }
    },
    {
        "name": "Cheeyappara Riverside Stalls & Rest Stop",
        "kind": "building",
        "lat": 10.0218, "lon": 76.8478,
        "population": 75, "buildings": 12,
        "critical": False,
        "attributes": {
            "building_type": "Commercial Market",
            "floors": 1, "structure": "Timber & Tin Roof",
            "elevation_above_bed_m": 2.5, "use": "tourist_refreshments"
        }
    },
    {
        "name": "Valara Waterfall Tourism Complex",
        "kind": "building",
        "lat": 10.0328, "lon": 76.8218,
        "population": 110, "buildings": 8,
        "critical": False,
        "attributes": {
            "building_type": "Commercial / Hospitality",
            "floors": 2, "structure": "RCC & Stone Masonry",
            "elevation_above_bed_m": 3.0, "use": "eco_tourism"
        }
    },
    {
        "name": "Neriamangalam River Forest Station",
        "kind": "infrastructure",
        "lat": 10.0462, "lon": 76.7918,
        "population": 18, "buildings": 2,
        "critical": True,
        "attributes": {
            "building_type": "Government / Forest Outpost",
            "floors": 2, "structure": "RCC",
            "elevation_above_bed_m": 4.5, "use": "disaster_management"
        }
    },
    {
        "name": "Neriamangalam Gateway Bridge (Ranis Bridge)",
        "kind": "infrastructure",
        "lat": 10.0496, "lon": 76.7868,
        "population": 0, "buildings": 1,
        "critical": True,
        "attributes": {
            "building_type": "Bridge",
            "structure": "Historic Stone Arch & Reinforced Girder",
            "elevation_above_bed_m": 9.0, "use": "high_range_lifeline"
        }
    },
    {
        "name": "Neriamangalam Riverbank Commercial Complex",
        "kind": "building",
        "lat": 10.0528, "lon": 76.7838,
        "population": 650, "buildings": 48,
        "critical": False,
        "attributes": {
            "building_type": "Commercial Market",
            "floors": 3, "structure": "RCC Frame",
            "elevation_above_bed_m": 3.2, "use": "central_market"
        }
    },
    {
        "name": "Neriamangalam Government Hospital River Ward",
        "kind": "infrastructure",
        "lat": 10.0542, "lon": 76.7828,
        "population": 140, "buildings": 2,
        "critical": True,
        "attributes": {
            "building_type": "Hospital",
            "floors": 2, "structure": "RCC Frame", "beds": 80,
            "elevation_above_bed_m": 4.0, "use": "district_healthcare"
        }
    },
    {
        "name": "Neriamangalam St. Joseph High School",
        "kind": "building",
        "lat": 10.0562, "lon": 76.7812,
        "population": 520, "buildings": 4,
        "critical": True,
        "attributes": {
            "building_type": "School / Educational",
            "floors": 2, "structure": "RCC Frame",
            "elevation_above_bed_m": 4.5, "use": "relief_shelter"
        }
    },
    {
        "name": "Kothamangalam Periyar Water Supply Intake",
        "kind": "infrastructure",
        "lat": 10.0612, "lon": 76.7668,
        "population": 12, "buildings": 2,
        "critical": True,
        "attributes": {
            "building_type": "Water Pumping Station",
            "floors": 2, "structure": "RCC Industrial",
            "elevation_above_bed_m": 3.0, "use": "municipal_drinking_water"
        }
    },
    {
        "name": "Kothamangalam Floodplain Residences",
        "kind": "building",
        "lat": 10.0628, "lon": 76.7652,
        "population": 980, "buildings": 140,
        "critical": False,
        "attributes": {
            "building_type": "Residential Quarters",
            "floors": 2, "structure": "RCC Masonry",
            "elevation_above_bed_m": 2.5, "use": "residential"
        }
    }
]

def seed_buildings():
    db = SessionLocal()
    target_iids = ["JR-20260929-22F604", "JR-20260929-5A298A", "JR-20260929-F0D4F3"]
    
    for iid in target_iids:
        # Clear old assets for this incident
        old_assets = db.query(Asset).filter(Asset.incident_id == iid).all()
        for a in old_assets:
            db.delete(a)
        db.commit()
        
        # Insert authentic riverside buildings
        for b in RIVERSIDE_BUILDINGS:
            a = Asset(
                incident_id=iid,
                kind=b["kind"],
                name=b["name"],
                lat=b["lat"],
                lon=b["lon"],
                population=b["population"],
                buildings=b["buildings"],
                critical=b["critical"],
                attributes=json.dumps(b["attributes"]),
                source="riverside_survey_osm"
            )
            db.add(a)
        db.commit()
        print(f"Seeded {len(RIVERSIDE_BUILDINGS)} riverside buildings for incident {iid}")
        
    db.close()
    print("Riverside buildings successfully committed to DB!")

if __name__ == "__main__":
    seed_buildings()
