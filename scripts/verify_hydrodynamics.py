import urllib.request
import json
import time

params = {
    "stored_volume_m3": 1996000000.0,
    "lake_area_m2": 60000000.0,
    "dam_height_m": 168.9,
    "dam_crest_len_m": 365.8,
    "dam_material": "Concrete",
    "scenario": "major",
    "breach_width_m": 80.0,
    "breach_depth_m": 45.0,
    "breach_time_hr": 1.5,
    "inflow_m3s": 2500.0,
    "valley_width_m": 120.0,
    "bed_slope": 0.015,
    "manning_n": 0.04,
    "spreading_factor": 2.2,
    "base_flow_m3s": 100.0,
    "with_uncertainty": False,
    "debris_bulking_factor": 1.0
}

url = "http://127.0.0.1:8000/api/simulations?incident_id=JR-20260929-22F604"
req = urllib.request.Request(
    url,
    data=json.dumps(params).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)
res = urllib.request.urlopen(req)
sim = json.loads(res.read().decode("utf-8"))
sid = sim.get("simulation_id") or sim.get("id")
print("Created simulation:", sid)

for i in range(40):
    time.sleep(1)
    res = urllib.request.urlopen(f"http://127.0.0.1:8000/api/simulations/{sid}")
    sim_res = json.loads(res.read().decode("utf-8"))
    status = sim_res.get("status")
    if status == "DONE":
        print(f"Simulation COMPLETED in {i+1} seconds!")
        break
    elif status == "FAILED":
        print("FAILED:", sim_res.get("error"))
        break

# Fetch Hydrodynamic Comparison
res = urllib.request.urlopen(f"http://127.0.0.1:8000/api/simulations/{sid}/hydrodynamic-comparison")
comp = json.loads(res.read().decode("utf-8"))
print("\n=== HYDRODYNAMIC COMPARISON RESULTS ===")
print("Solvers validated:", list(comp.get("models", {}).keys()))
for m, info in comp.get("models", {}).items():
    print(f" * {info['name']}: peak Q={info.get('peak_discharge_m3s')} m3/s, wave speed={info.get('front_propagation_speed_kmh')} km/h")

print("\nDownstream settlements & infrastructure arrival times:")
for s in comp.get("settlement_impact_comparison", []):
    d_t = s["arrival_time_min"]["delft3d_swe"]
    s_t = s["arrival_time_min"]["sph_particles"]
    c_t = s["arrival_time_min"]["muskingum_cunge_1d"]
    dep = s["peak_depth_m"]["delft3d_swe"]
    urg = s["evacuation_urgency"]
    print(f" - {s['name']:35} ({s['distance_km']} km) | Delft3D: {d_t:4.1f}m | SPH: {s_t:4.1f}m | 1D: {c_t:4.1f}m | Depth: {dep:4.1f}m | {urg}")

# Also verify visual simulation frames
results = sim_res["results"] if isinstance(sim_res["results"], dict) else json.loads(sim_res["results"])
visual = results.get("visual")
if visual and "frames" in visual:
    print(f"\nVisual simulation frames generated: {len(visual['frames'])} frames")
    print(f"Total simulated time: {visual['frames'][-1]['t_min']} minutes")
    print(f"Max flood front reach: {visual['frames'][-1]['front_km']} km")
    print(f"Settlements in visual impact schedule: {len(visual.get('impact_schedule', []))}")
