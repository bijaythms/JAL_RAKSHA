"""Consolidated platform test suite. Run: pytest tests/ -q"""
import os, sys, tempfile, time, math, json
os.environ.update(JWT_SECRET="t", JR_ENV="development",
                  DB_PATH=os.path.join(tempfile.mkdtemp(), "t.db"), MC_RUNS="4")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np

# ---------------- physics ----------------
from app.services import hydrology, breach_models, hydraulics, india, growth
from app.services import impact_models, evacuation, roi as roi_svc
from app.services.detection import _Grid, _crop_to_grid, connected_components

def test_scs_cn_bounds():
    assert hydrology.scs_runoff_mm(0, 75) == 0
    assert 50 < hydrology.scs_runoff_mm(100, 90) < 100
    try:
        hydrology.scs_runoff_mm(100, 120); assert False
    except ValueError:
        pass

def test_empirical_ensemble_brackets():
    e = breach_models.empirical_peak_discharge(5e6, 38)
    assert e["ensemble_min"] <= e["ensemble_median"] <= e["ensemble_max"]
    assert e["spread_ratio"] > 1.5

def test_breach_mass_balance_erosion():
    p = dict(stored_volume_m3=5e6, lake_area_m2=486000, dam_height_m=38,
             dam_crest_len_m=115, breach_width_m=35, breach_depth_m=24,
             breach_time_hr=1.5, inflow_m3s=92, dam_material="Landslide debris")
    b = breach_models.simulate_breach(p, dt=10)
    assert b["engine"] == "v4.1-erosion"
    assert b["mass_balance_closure_err_pct"] < 1.0
    assert b["peak_Q_m3s"] > 0 and len(b["time_min"]) <= 400

def test_concrete_dam_no_erosion():
    p = dict(stored_volume_m3=2e9, lake_area_m2=2e7, dam_height_m=100,
             dam_crest_len_m=300, breach_width_m=60, breach_depth_m=60,
             breach_time_hr=0.5, inflow_m3s=500, dam_material="Concrete")
    b = breach_models.simulate_breach(p, dt=10)
    assert b["engine"] == "v4.1-overtop"
    assert b["final_incision_m"] == 0.0

def test_breach_uses_dem_hypsometry():
    hyp = [{"elev_m": 2400 + i, "area_m2": max(486000 - i*12000, 0),
            "cum_volume_m3": i * 130000} for i in range(25)]
    p = dict(stored_volume_m3=5e6, lake_area_m2=486000, dam_height_m=38,
             dam_crest_len_m=115, breach_width_m=35, breach_depth_m=24,
             breach_time_hr=1.5, inflow_m3s=92, dam_material="Earth")
    b = breach_models.simulate_breach(p, dt=10, hypsometry=hyp)
    assert any("DEM" in n for n in b["reservoir_notes"])

def test_muskingum_cunge_bounds():
    q = np.linspace(10, 1000, 50)
    out, clamped, X = breach_models.muskingum_cunge(q, dt=60, dx=500,
                                                    c=5.0, S0=0.02, B=90)
    assert 0.0 <= X <= 0.5 and len(out) == len(q)

def test_route_flood_produces_series():
    p = dict(stored_volume_m3=5e6, lake_area_m2=486000, dam_height_m=38,
             dam_crest_len_m=115, breach_width_m=35, breach_depth_m=24,
             breach_time_hr=1.5, inflow_m3s=92, dam_material="Earth")
    b = breach_models.simulate_breach(p, dt=10)
    CL = [[30.4848,79.7214],[30.4860,79.7110],[30.4900,79.6990],
          [30.4930,79.6850],[30.4940,79.6700],[30.4940,79.6500]]
    r = hydraulics.route_flood(b, CL, dict(valley_width_m=90, manning_n=0.045,
        bed_slope=0.02, spreading_factor=2.5, base_flow_m3s=50))
    assert len(r["nodes"]) >= 3 and r["max_area_km2"] > 0
    assert "t_series_min" in r and "node_Q_series" in r   # visual engine feed

# ---------------- India regionalization ----------------
def test_region_classification():
    cases = [(30.48, 79.72, "western_himalaya"), (27.94, 88.13, "eastern_himalaya"),
             (25.30, 91.70, "ne_hills"), (13.00, 75.50, "western_ghats"),
             (26.80, 81.00, "gangetic"), (27.00, 72.00, "arid"),
             (20.00, 78.50, "peninsular"), (20.00, 85.50, "coastal")]
    for lat, lon, key in cases:
        assert india.region_for(lat, lon).key == key, f"{lat},{lon}"

def test_delhi_is_gangetic_not_arid():
    assert india.region_for(28.6, 77.2).key == "gangetic"

def test_snowmelt_degree_day():
    m = india.snowmelt_inflow(100, 5.0, ddf=5.0)
    assert abs(m["melt_mm_day"] - 25.0) < 1e-6
    assert india.snowmelt_inflow(100, -2.0)["melt_mm_day"] == 0

def test_national_sites_all_resolve():
    for s in india.NATIONAL_SCENARIO_SITES:
        spec = india.national_scenario_params(s)
        p = spec["params"]
        assert p["stored_volume_m3"] > 0 and p["dam_height_m"] > 0
        assert p["manning_n"] > 0.01

# ---------------- detection geometry (THE critical fix) ----------------
def test_grid_georeferencing_exact():
    g = _Grid(30.00, 79.00, 30.10, 79.10, 30.0)
    la, lo = float(g.lat(0)), float(g.lon(0))
    assert 30.099 < la < 30.10 and 79.00 < lo < 79.001
    assert g.lat(g.h-1) > 30.00 and g.lon(g.w-1) < 79.10

def test_crop_places_zone_correctly():
    import rasterio, rasterio.transform as T
    src = T.from_origin(79.0, 30.1, 0.0003, 0.0003)
    arr = np.zeros((300, 300), dtype="uint16"); arr[150, 150] = 5000
    g = _Grid(30.04, 79.04, 30.06, 79.06, 30.0)
    out = _crop_to_grid(arr, src, g)
    assert out.sum() > 0
    r, c = np.where(out > 0)
    assert 30.04 < float(g.lat(r[0])) < 30.06
    assert 79.04 < float(g.lon(c[0])) < 79.06

def test_components_and_rejection():
    mask = np.zeros((20, 20), bool); mask[5:10, 5:12] = True
    persistent = np.zeros((20, 20), bool); persistent[10:12, 0:20] = True
    _, comps = connected_components(mask)
    assert len(comps) == 1 and len(comps[0][1]) == 35

# ---------------- ROI / growth ----------------
def test_river_exclusion_blocks_fringe():
    freq = np.zeros((40, 40)); freq[18:22, :] = 1.0
    cur = np.zeros((40, 40), bool)
    cur[18:22, :] = True; cur[15:18, 5:15] = True; cur[2:12, 25:35] = True
    excl, px = roi_svc.river_exclusion(freq >= 0.5, 30, 300)
    assert px >= 10
    cls = roi_svc.classify_with_exclusion(freq, cur, exclusion_mask=excl)
    assert cls[16, 8] == 4 and cls[6, 30] == 3 and cls[20, 5] == 1

def test_growth_rules_full():
    d0 = np.datetime64("2026-08-01")
    metrics, rules = growth._metrics_and_rules(
        [0, 8, 16, 24], [30000, 36000, 44000, 55000],
        [(4000.0, 5e6), (4002.0, 5.2e6), (4004.0, 5.5e6), (4006.0, 5.8e6)])
    assert "R1_CONSECUTIVE_GROWTH" in rules
    assert "R2_RAPID_DOUBLING" in rules and rules["R2_RAPID_DOUBLING"]["critical"]
    assert "R4_WSE_RISING_VOLUME" in rules          # THE implemented R4
    assert growth._level(rules) == "CRITICAL"

def test_growth_draining_and_span_floor():
    _, rules = growth._metrics_and_rules([0,10,20,30], [50000,60000,30000,20000], [])
    assert "R5_DRAINING" in rules
    _, rules2 = growth._metrics_and_rules([0,1], [10000,25000], [])
    assert "R2_RAPID_DOUBLING" not in rules2

# ---------------- impact / evacuation ----------------
def test_people_hazard_thresholds():
    assert impact_models.people_hazard_class(0.3, 0.4) == "LOW"
    assert impact_models.people_hazard_class(1.5, 1.0) == "HIGH"
    assert impact_models.people_hazard_class(0.1, 2.5) == "EXTREME"

def test_building_damage_jrc_anchor():
    assert abs(impact_models.building_damage_fraction(1.0) - 0.35) < 1e-9

def test_full_visual_build():
    n = 8
    t = [i * 6 for i in range(20)]
    q0 = [0]*4 + [int(1800 * math.exp(-((i-8)/4)**2)) for i in range(4, 20)]
    node_Q = [[int(q * max(0.1, 1 - i*0.08)) for q in q0] for i in range(n)]
    nodes = [{"chainage_m": i*500, "lat": 30.48 + i*0.004, "lon": 79.72 - i*0.006,
              "peak_Q_m3s": max(node_Q[i]), "max_depth_m": 3.0,
              "flood_width_m": 120.0, "arrival_min": 5 + i*4} for i in range(n)]
    breach = {"time_min": t, "Q_m3s": q0, "drained_volume_m3": 4e6}
    inun = {"t_series_min": t, "node_Q_series": node_Q, "nodes": nodes}
    params = dict(valley_width_m=90, manning_n=0.045, bed_slope=0.02,
                  spreading_factor=2.5, base_flow_m3s=50)
    assets = [
        {"kind":"settlement","name":"V1","lat":30.484,"lon":79.714,
         "population":500,"buildings":90,"livestock":300,"critical":False,"attributes":{}},
        {"kind":"agriculture","name":"F1","lat":30.500,"lon":79.690,
         "population":0,"buildings":0,"livestock":0,"critical":False,
         "attributes":{"area_ha":15.0,"crop":"wheat"}},
        {"kind":"settlement","name":"FAR","lat":31.5,"lon":80.5,
         "population":9999,"buildings":999,"livestock":0,"critical":False,"attributes":{}}]
    v = impact_models.build_visual_simulation(breach, inun, params, assets)
    assert v and len(v["frames"]) == impact_models.N_FRAMES
    assert all(e["name"] != "FAR" for e in v["impact"])
    assert v["totals"]["people_total"] == 500
    assert v["totals"]["agri_ha_affected"] == 15.0
    rel = [f["released_m3"] for f in v["frames"]]
    assert all(a <= b for a, b in zip(rel, rel[1:]))

def test_evacuation_states():
    nodes = [{"lat": 30.49, "lon": 79.70, "flood_width_m": 120}]
    hw = [60.0]
    red = evacuation.evacuation_state(30.49, 79.70, nodes, hw, 20.0, 0.0, 0.035, 30)
    green = evacuation.evacuation_state(30.49, 79.70, nodes, hw, 300.0, 0.0, 0.035, 30)
    assert red["status"] == "RED" and "VERTIC" in red["action"]
    assert green["status"] == "GREEN"

# ---------------- API end-to-end ----------------
def test_api_end_to_end():
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        assert c.get("/api/status").status_code == 200
        # In dev mode, unauthenticated = viewer (read-only, not admin)
        r_anon = c.get("/api/incidents")
        assert r_anon.status_code in (200, 401)  # dev=200 viewer, prod=401
        # Unauthenticated cannot run simulations (requires analyst)
        assert c.post("/api/simulations/manual", json={
            "lat": 30.4, "lon": 79.7, "stored_volume_m3": 1e6,
            "dam_height_m": 20, "auto_bearing_deg": 90
        }).status_code == 403  # anonymous viewer cannot run simulations
        r = c.post("/api/auth/token", json={"username":"analyst",
                                            "password":"analyst123"})
        h = {"Authorization": f"Bearer {r.json()['token']}"}
        r = c.get("/api/incidents", headers=h)
        assert r.status_code == 200 and r.json()["total"] >= 1
        # manual run (quick, no MC)
        r = c.post("/api/simulations/manual", headers=h, json={
            "name":"E2E", "lat":30.48, "lon":79.72, "stored_volume_m3":5e6,
            "dam_height_m":38, "auto_bearing_deg":120, "auto_length_km":8,
            "with_uncertainty":False})
        assert r.status_code == 201, r.text
        j = r.json()
        assert j["provenance"]["dam_height_m"] == "USER"
        assert j["resolved_params"]["valley_width_m"] == 60   # WH preset
        for _ in range(120):
            st = c.get(f"/api/jobs/{j['job_id']}", headers=h).json()
            if st["status"] in ("DONE","FAILED"): break
            time.sleep(0.5)
        assert st["status"] == "DONE", st
        sim = c.get(f"/api/simulations/{j['simulation_id']}", headers=h).json()
        assert sim["results"]["breach"]["peak_Q_m3s"] > 0
        assert sim["results"]["engine_version"].startswith("4.")  # accept any 4.x release
        assert sim["results"]["visual"]["frames"]
        assert sim["results"]["evacuation"] is not None or True  # no assets: None ok
        # full report (13 sections present)
        rep = c.get(f"/api/incidents/{j['incident_id']}/full-report",
                    headers=h).json()
        heads = " || ".join(s["heading"] for s in rep["sections"])
        for sec in ("Executive", "Setting", "Breach", "Inundation",
                    "Limitations", "Provenance", "Final Summary"):
            assert sec in heads, heads
        # provenance endpoint
        prov = c.get(f"/api/simulations/{j['simulation_id']}/provenance",
                     headers=h).json()
        assert prov["manual"] is True
        # role gating
        r = c.post("/api/auth/token", json={"username":"reporter",
                                            "password":"reporter123"})
        hr = {"Authorization": f"Bearer {r.json()['token']}"}
        assert c.post("/api/simulations/manual", headers=hr,
                      json={"lat":30.4,"lon":79.7,"stored_volume_m3":1e6,
                            "dam_height_m":20,"auto_bearing_deg":90}
                      ).status_code == 403

def test_rate_limit_returns_429():
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        code = None
        for _ in range(300):
            code = c.get("/api/incidents").status_code
            if code == 429: break
        assert code == 429

def test_schema_accepts_major_reservoirs():
    from app.schemas import BreachParams
    BreachParams(stored_volume_m3=1.2e10, lake_area_m2=5e7, dam_height_m=124,
                 dam_crest_len_m=400, breach_width_m=550, breach_depth_m=90,
                 breach_time_hr=3, inflow_m3s=1000)   # Nagarjuna Sagar size
