"""Comprehensive 13-section assessment report, assembled from STORED
artifacts only. Freshness manifest on every item; guards for legacy
results; stale items echoed in the final summary."""
import json
from datetime import datetime, timezone
from ..db import (SessionLocal, Incident, Simulation, Asset, DamageReport,
                  Upload, LakeCandidate, LakeObservation, MonitoringZone)
from . import india
from . import growth as _growth

FRESH_HOURS = 72.0


def _utcnow():
    return datetime.now(timezone.utc)


def _fresh(ts):
    if ts is None:
        return "MISSING"
    try:
        age = (_utcnow() - ts).total_seconds() / 3600.0
    except Exception:
        return "MISSING"
    return "FRESH" if age <= FRESH_HOURS else "STALE ({:.1f} d old)".format(age / 24.0)


def _kv(pairs):
    return {"type": "kv", "rows": [(k, v) for k, v in pairs if v is not None]}


def _text(s):
    return {"type": "text", "text": s}


def _table(headers, rows):
    return {"type": "table", "headers": headers, "rows": rows}


def _list(items):
    return {"type": "list", "items": items}


def _warning(s):
    return {"type": "warning", "text": s}


def _fmt_inr(v):
    if v is None:
        return "-"
    if v >= 1e7:
        return "Rs {:,.1f} crore".format(v / 1e7)
    if v >= 1e5:
        return "Rs {:,.0f} lakh".format(v / 1e5)
    return "Rs {:,.0f}".format(v)


def build_full_report(incident_id, run_id=None):
    db = SessionLocal()
    try:
        inc = db.get(Incident, incident_id)
        if not inc:
            return {"ok": False, "error": "incident not found"}
        sim = None
        if run_id:
            sim = db.get(Simulation, run_id)
            if not sim or sim.incident_id != incident_id or sim.status != "DONE":
                return {"ok": False,
                        "error": "specified simulation not found/complete"}
        else:
            sim = (db.query(Simulation)
                     .filter(Simulation.incident_id == incident_id,
                             Simulation.status == "DONE")
                     .order_by(Simulation.created_at.desc()).first())
        params = json.loads(sim.params) if sim else None
        res = json.loads(sim.results) if sim else {}
        region = india.region_for(inc.lat, inc.lon)
        assets = db.query(Asset).filter(
            Asset.incident_id == incident_id).all()
        damage = (db.query(DamageReport)
                    .filter(DamageReport.incident_id == incident_id,
                            DamageReport.status == "VERIFIED")
                    .order_by(DamageReport.created_at.desc()).all())
        dem_upload = None
        if inc.dem_upload_id:
            dem_upload = db.get(Upload, inc.dem_upload_id)
        candidate = (db.query(LakeCandidate)
                       .filter(LakeCandidate.incident_id == incident_id)
                       .first())
        observations = []
        if candidate:
            observations = (db.query(LakeObservation)
                              .filter(LakeObservation.candidate_id ==
                                      candidate.id)
                              .order_by(LakeObservation.observed_at.asc())
                              .all())
        zone = None
        if candidate:
            zone = db.get(MonitoringZone, candidate.zone_id)

        sections = []
        freshness = []

        def stamp(item, ts):
            freshness.append((item, _fresh(ts)))

        stamp("Incident created", inc.created_at)
        stamp("Downstream centerline", inc.created_at)
        if dem_upload:
            stamp("DEM hypsometry", dem_upload.created_at)
        if sim:
            stamp("Simulation run", sim.created_at)
        if candidate:
            stamp("Last satellite detection", candidate.last_seen_at)

        # ---- 1. Executive summary ----
        if sim:
            b = res.get("breach", {})
            inun = res.get("inundation", {})
            expo = res.get("exposure", {})
            vis = res.get("visual") or {}
            ev = res.get("evacuation") or {}
            totals = vis.get("totals", {})
            arr = inun.get("first_arrival_min")
            red = [c for c in ev.get("clocks", [])
                   if c.get("status_at_zero") == "RED"]
            amber = [c for c in ev.get("clocks", [])
                     if c.get("status_at_zero") == "AMBER"]
            ens = b.get("empirical_ensemble", {})
            eq_min = ens.get("ensemble_min", 0)
            eq_max = ens.get("ensemble_max", 0)
            fro = b.get("empirical_froehlich1995_Qp", 0)
            exec_lines = []
            exec_lines.append(
                "Scenario: '{}' breach of a {:.0f} m {} barrier impounding "
                "{:,.0f} m3 on the {} near ({:.4f}N, {:.4f}E), {}.".format(
                    params["scenario"], params["dam_height_m"],
                    params["dam_material"].lower(),
                    params["stored_volume_m3"],
                    inc.river_name or "unnamed channel",
                    inc.lat, inc.lon, inc.region or region.name))
            exec_lines.append(
                "Modelled peak breach discharge {:,.0f} m3/s (ensemble range "
                "{:,.0f}-{:,.0f} m3/s; Froehlich 1995 cross-check {:,.0f} "
                "m3/s).".format(b.get("peak_Q_m3s", 0), eq_min, eq_max, fro))
            line3 = ("Flood travels {} km downstream; maximum inundation {} "
                     "km2, depth {} m.".format(inun.get("corridor_km"),
                                               inun.get("max_area_km2"),
                                               inun.get("max_depth_m")))
            if arr is not None:
                line3 += " First arrival {:.0f} minutes.".format(arr)
            else:
                line3 += " No node exceeded 2x base flow."
            exec_lines.append(line3)
            exec_lines.append(
                "Exposure: {:,} people, {} buildings, {} critical "
                "facilities, {} ha agriculture, {} livestock.".format(
                    expo.get("total_population_exposed", 0),
                    expo.get("buildings_exposed", 0),
                    len(expo.get("critical_infra_affected", [])),
                    totals.get("agri_ha_affected", 0),
                    totals.get("livestock", 0)))
            if ev.get("clocks"):
                exec_lines.append(
                    "Evacuation: {} settlement(s) cannot self-evacuate on "
                    "foot (VERTICAL evacuation); {} require immediate "
                    "start.".format(len(red), len(amber)))
            else:
                exec_lines.append("No settlement evacuation assessment "
                                  "(no exposure layer).")
            risk = res.get("risk", {})
            if risk:
                exec_lines.append(
                    "TDRI {} [{}-{}], band {}. Recommended: {}.".format(
                        risk.get("tdri"), risk.get("range", [0, 0])[0],
                        risk.get("range", [0, 0])[1], risk.get("band"),
                        risk.get("recommended_action")))
        else:
            exec_lines = ["NO COMPLETED SIMULATION EXISTS for this incident. "
                          "Run a breach simulation to generate the impact "
                          "and evacuation sections."]
        sections.append({"heading": "1. Executive Summary",
                         "blocks": [_text(l) for l in exec_lines]})

        # ---- 2. Setting ----
        sections.append({
            "heading": "2. Geographic & Hydrological Setting",
            "blocks": [
                _kv([("Incident ID", inc.id), ("Name", inc.name),
                     ("Type", inc.incident_type), ("Status", inc.status),
                     ("River", inc.river_name or "-"),
                     ("Region", region.name),
                     ("Coordinates",
                      "{:.5f}N, {:.5f}E".format(inc.lat, inc.lon)),
                     ("Physiographic preset", region.key)]),
                _text(region.notes),
                _kv([("Regional valley width", "{} m".format(
                          region.valley_width_m)),
                     ("Regional bed slope", str(region.bed_slope)),
                     ("Regional Manning n", str(region.manning_n)),
                     ("Inflow regime", region.inflow_mode),
                     ("Design 24-h storm",
                      "{} mm".format(region.design_storm_24h_mm)),
                     ("Evacuation mobilization (typical)",
                      "{} min".format(region.mobilization_min))]),
                _warning("Regional values are physiographic presets - "
                         "order-of-magnitude figures, not site "
                         "calibrations."),
            ]})

        # ---- 3. Detection evidence ----
        if candidate:
            buffer_m = 300
            if zone and zone.river_buffer_m:
                buffer_m = zone.river_buffer_m
            obs_rows = []
            for o in observations:
                obs_rows.append([
                    o.observed_at.strftime("%Y-%m-%d"),
                    "{:.2f} ha".format(o.area_m2 / 1e4),
                    "{:.1f} m".format(o.wse_m) if o.wse_m else "-",
                    "{:.2f} M m3".format(o.volume_m3 / 1e6)
                    if o.volume_m3 else "-"])
            blocks3 = [
                _kv([("Candidate ID", candidate.id),
                     ("Status", candidate.status),
                     ("Detection score", candidate.score),
                     ("Growing flag",
                      "YES" if candidate.growing else "no"),
                     ("Alert level", candidate.alert_level)]),
                _text("Detected by the automated monitor as new water "
                      "against a historical water-frequency baseline, "
                      "separated from river widening by a {} m exclusion "
                      "buffer and morphology tests.".format(buffer_m))]
            if obs_rows:
                blocks3.append(_table(["Date", "Water area", "WSE",
                                       "Volume"], obs_rows))
            g = _growth.analyze_growth(candidate.id, db=db)
            if g.get("ok") and g.get("metrics"):
                blocks3.append(_kv([
                    ("Growth rules fired",
                     ", ".join(g.get("rules_fired", [])) or "none"),
                    ("Doubling time",
                     "{} d".format(g["metrics"]["doubling_time_days"])
                     if g["metrics"].get("doubling_time_days") else "-"),
                    ("Latest growth rate",
                     "{:,.0f} m2/day".format(
                         g["metrics"].get("latest_abs_growth_m2_day", 0)))]))
            sections.append({"heading": "3. Detection Evidence & Monitoring "
                                        "History", "blocks": blocks3})
        elif inc.is_manual:
            sections.append({
                "heading": "3. Detection Evidence & Monitoring History",
                "blocks": [_text("Manually-defined scenario entered by an "
                                 "official - no automated satellite "
                                 "detection exists. Parameter provenance in "
                                 "Section 12.")]})
        else:
            sections.append({
                "heading": "3. Detection Evidence & Monitoring History",
                "blocks": [_text("No automated detection linked to this "
                                 "incident. Add the area as a monitoring "
                                 "zone to begin satellite surveillance.")]})

        # ---- 4. Reservoir & dam ----
        dem_meta = json.loads(dem_upload.meta) if dem_upload else {}
        rows4 = []
        if params:
            rows4.append(("Stored volume",
                          "{:,.0f} m3".format(params["stored_volume_m3"])))
            rows4.append(("Lake surface area",
                          "{:,.0f} m2".format(params["lake_area_m2"])))
            rows4.append(("Dam height", "{} m".format(params["dam_height_m"])))
            rows4.append(("Crest length",
                          "{} m".format(params["dam_crest_len_m"])))
            rows4.append(("Dam material", params["dam_material"]))
        if dem_upload:
            rows4.append(("DEM source",
                          "Uploaded CSV point cloud ({} pts)".format(
                              dem_meta.get("points"))))
        else:
            rows4.append(("DEM source",
                          "None uploaded - parametric bathymetry"))
        blocks4 = [_kv(rows4)]
        if candidate and (candidate.wse_m or candidate.depth_m):
            blocks4.append(_kv([
                ("WSE (GLO-30 fit)", "{} m".format(candidate.wse_m)),
                ("Max depth (GLO-30)", "{} m".format(candidate.depth_m)),
                ("Volume (GLO-30)",
                 "{:,.0f} m3".format(candidate.volume_m3))]))
        sections.append({"heading": "4. Reservoir & Dam Characterization",
                         "blocks": blocks4})

        if not sim:
            sections.append({
                "heading": "5-10. Simulation sections",
                "blocks": [_warning("Sections 5-10 require a completed "
                                    "simulation. Run one from the BREACH "
                                    "SIMULATION tab, then regenerate.")]})
            sections = sections[:5]
        else:
            b = res.get("breach", {})
            inun = res.get("inundation", {})
            expo = res.get("exposure", {})
            unc = res.get("uncertainty")
            vis = res.get("visual")
            ev = res.get("evacuation")
            risk = res.get("risk", {})
            conf = res.get("confidence")

            # ---- 5. Breach ----
            ens = b.get("empirical_ensemble", {})
            eq_rows = []
            for k, v in ens.get("equations", {}).items():
                eq_rows.append([k, "{:,.0f}".format(v)])
            eq_rows.append(["Physical model (routed)",
                            "{:,.0f}".format(b.get("peak_Q_m3s", 0))])
            if ens.get("ensemble_median"):
                eq_rows.append(["Ensemble median",
                                "{:,.0f}".format(ens["ensemble_median"])])
            blocks5 = [
                _table(["Model", "Peak Q (m3/s)"], eq_rows),
                _kv([("Engine", b.get("engine", "unknown")),
                     ("Time to peak",
                      "{} min".format(b.get("time_to_peak_min"))),
                     ("Drained volume",
                      "{:,.0f} m3".format(b.get("drained_volume_m3", 0))),
                     ("Mass-balance closure",
                      "{} %".format(
                          b.get("mass_balance_closure_err_pct")))]),
                _text("Method: {}.".format(b.get("method", "-")))]
            caveat = ens.get("caveat",
                             "Empirical ensemble not stored for this run.")
            blocks5.append(_warning(caveat))
            sections.append({"heading": "5. Breach Analysis",
                             "blocks": blocks5})

            # ---- 6. Uncertainty ----
            blocks6 = []
            if unc:
                u_rows = []
                for k, v in unc.items():
                    u_rows.append([k.replace("_", " "), v["p10"], v["p50"],
                                   v["p90"]])
                blocks6.append(_table(["Quantity", "p10", "p50", "p90"],
                                      u_rows))
            else:
                blocks6.append(_text("Monte Carlo was disabled - point "
                                     "estimates only."))
            if risk:
                blocks6.append(_kv([
                    ("TDRI", "{} [{}-{}]".format(
                        risk["tdri"], risk["range"][0], risk["range"][1])),
                    ("Band", risk["band"])]))
            if conf:
                blocks6.append(_table(
                    ["Confidence item", ""],
                    [[p, ""] for p in conf["provenance"]]))
            sections.append({"heading": "6. Uncertainty Analysis",
                             "blocks": blocks6})

            # ---- 7. Inundation ----
            node_rows = []
            for n in inun.get("nodes", []):
                node_rows.append([
                    "{:.1f}".format(n["chainage_m"] / 1000.0),
                    "{:,.0f}".format(n["peak_Q_m3s"]),
                    str(n["max_depth_m"]),
                    "{:.0f}".format(n["flood_width_m"]),
                    str(n["arrival_min"]) if n["arrival_min"] is not None
                    else "-"])
            arr_txt = "no significant arrival"
            if inun.get("first_arrival_min") is not None:
                arr_txt = "{} min".format(inun["first_arrival_min"])
            sections.append({
                "heading": "7. Downstream Inundation",
                "blocks": [
                    _kv([("Corridor length",
                          "{} km".format(inun.get("corridor_km"))),
                         ("Max area", "{} km2 ({})".format(
                             inun.get("max_area_km2"),
                             inun.get("area_method", "-"))),
                         ("Max depth", "{} m".format(
                             inun.get("max_depth_m"))),
                         ("First arrival", arr_txt)]),
                    _table(["Chainage (km)", "Peak Q", "Depth (m)",
                            "Width (m)", "Arrival (min)"], node_rows)]})

            # ---- 8 & 9. Hazard & impact (guarded for legacy runs) ----
            if vis and vis.get("frames"):
                vf = max((f["max_force_kN_m"] for f in vis["frames"]),
                         default=0)
                vv = max((f["max_v_ms"] for f in vis["frames"]), default=0)
                dv = max((f["max_dv"] for f in vis["frames"]), default=0)
                t = vis.get("totals", {})
                ppl = t.get("people", {})
                sections.append({
                    "heading": "8. Hazard Intensity",
                    "blocks": [
                        _kv([("Max velocity", "{} m/s".format(vv)),
                             ("Max depth x velocity",
                              "{} m2/s".format(dv)),
                             ("Max drag force per metre",
                              "{} kN/m".format(vf))]),
                        _text("Section-averaged 1D hydraulics; local "
                              "values around obstructions can be 2-3x "
                              "higher; debris-laden fronts far more."),
                        _table(
                            ["People hazard class", "Population"],
                            [[k, "{:,}".format(ppl.get(k, 0))]
                             for k in ("LOW", "MODERATE", "HIGH",
                                       "EXTREME")])]})
                ec = t.get("economic_inr", {})
                blocks9 = [
                    _kv([("Population exposed",
                          "{:,}".format(t.get("people_total", 0))),
                         ("Buildings affected",
                          str(t.get("buildings_affected", 0))),
                         ("Buildings fully-damaged equivalent",
                          str(t.get("buildings_fully_damaged_eq", 0))),
                         ("Agriculture affected",
                          "{} ha".format(t.get("agri_ha_affected", 0))),
                         ("Agriculture lost",
                          "{} ha".format(t.get("agri_ha_lost", 0))),
                         ("Livestock", str(t.get("livestock", 0))),
                         ("Economic proxy - buildings",
                          _fmt_inr(ec.get("buildings", 0))),
                         ("Economic proxy - agriculture",
                          _fmt_inr(ec.get("agriculture", 0))),
                         ("TOTAL ({})".format("configured rates" if t.get("unit_costs_flagged") is False else "placeholder rates"),
                          _fmt_inr(t.get("economic_total_inr", 0)))]),
                ]
                if t.get("unit_costs_flagged") is False:
                    blocks9.append(_text("Economic figures use CONFIGURED unit rates (source: {}).".format(
                        t.get("unit_costs_source", "override"))))
                else:
                    blocks9.append(_warning("Economic figures use PLACEHOLDER unit rates - "
                                            "replace with district Schedule of Rates."))
                if damage:
                    blocks9.append(_table(
                        ["Verified field report", "Depth", "Date"],
                        [[d.incident_type,
                          "{} m".format(d.water_depth_m),
                          d.created_at.strftime("%Y-%m-%d")]
                         for d in damage]))
                sections.append({"heading": "9. Impact Assessment",
                                 "blocks": blocks9})
            else:
                sections.append({
                    "heading": "8-9. Hazard & Impact",
                    "blocks": [_warning(
                        "This simulation has no visual-impact payload "
                        "(engine_version: {}). Re-run to obtain "
                        "hazard-intensity and impact sections.".format(
                            res.get("engine_version", "unknown")))]})

            sections.append(_evacuation_section(ev))

        # ---- 11. Limitations ----
        lims = []
        if sim:
            lims += res.get("breach", {}).get("limitations", [])
            lims += res.get("breach", {}).get("reservoir_notes", [])
            lims += res.get("inundation", {}).get("limitations", [])
            if res.get("evacuation"):
                lims += res["evacuation"].get("limitations", [])
            if res.get("visual"):
                lims += res["visual"].get("limitations", [])
        lims.append("Regional presets are order-of-magnitude figures, not "
                    "site calibrations.")
        sections.append({"heading": "11. Limitations & Assumptions",
                         "blocks": [_list(list(dict.fromkeys(lims)))]})

        # ---- 12. Provenance ----
        prov_rows = [[i, s] for i, s in freshness]
        if sim:
            prov_rows.append(["Simulation parameters", "STORED (exact)"])
        prov_rows.append(["Report generated", "now"])
        sections.append({
            "heading": "12. Data Provenance & Freshness Manifest",
            "blocks": [
                _table(["Data item", "Status"], prov_rows),
                _text("Every figure derives from the stored artifacts "
                      "above. Items marked STALE should be refreshed "
                      "before operational use.")]})

        # ---- 13. Final summary (staleness live) ----
        stale_items = [i for i, s in freshness
                       if isinstance(s, str) and s.startswith("STALE")]
        sections.append(_final_summary(inc, sim, res if sim else {},
                                       region, stale_items))

        return {
            "ok": True,
            "title": "JAL-RAKSHA Comprehensive Assessment - {}".format(
                inc.name),
            "incident_id": incident_id,
            "simulation_id": sim.id if sim else None,
            "generated_at_utc": _utcnow().isoformat(),
            "region": {"key": region.key, "name": region.name},
            "sections": sections,
            "disclaimer": "Generated from stored models and data as of the "
                          "manifest timestamps. Planning support only - not "
                          "a substitute for official inundation studies, "
                          "EAPs, or field verification."}
    finally:
        db.close()


def _evacuation_section(ev):
    if not ev or not ev.get("clocks"):
        return {"heading": "10. Evacuation Plan",
                "blocks": [_warning(
                    "No evacuation assessment possible: no population/assets "
                    "layer inside the flood corridor. Upload an exposure CSV "
                    "and re-run.")]}
    clocks = sorted(ev["clocks"],
                    key=lambda c: (c["arrival_min"] is None,
                                   c["arrival_min"] or 1e9))
    red = [c for c in clocks if c["status_at_zero"] == "RED"]
    amber = [c for c in clocks if c["status_at_zero"] == "AMBER"]
    green = [c for c in clocks if c["status_at_zero"] == "GREEN"]
    arr_list = [c["arrival_min"] for c in clocks
                if c["arrival_min"] is not None]
    first_arr = min(arr_list) if arr_list else None
    amber_arr = 30
    amber_arrs = [c["arrival_min"] for c in amber
                  if c["arrival_min"] is not None]
    if amber_arrs:
        amber_arr = min(amber_arrs)
    sched = [
        "T+0: sirens / cell broadcast to all {} settlements; officials to "
        "RED settlements ({}) to direct VERTICAL movement.".format(
            len(clocks), ", ".join(c["name"] for c in red) or "none"),
        "T+0-{:.0f} min: AMBER settlements ({}) must be moving.".format(
            amber_arr, ", ".join(c["name"] for c in amber) or "none"),
        "By first arrival ({} min): GREEN settlements cleared outside the "
        "corridor.".format(first_arr if first_arr is not None else "-"),
        "Post-recession: no re-entry until the hydrograph recedes below "
        "2x base flow at ALL nodes and bridges are checked."]
    return {
        "heading": "10. Evacuation Plan",
        "blocks": [
            _text("Evacuation model: {}. Regional mobilization {} min "
                  "({}); walking lower-bound travel.".format(
                      ev["method"], ev["mobilization_min"],
                      ev["region_name"])),
            _kv([("Settlements assessed", len(clocks)),
                 ("RED - vertical evacuation only", len(red)),
                 ("AMBER - immediate start", len(amber)),
                 ("GREEN - comfortable margin", len(green))]),
            _table(
                ["Settlement", "Pop.", "Arrival (min)", "Needed (min)",
                 "Status"],
                [[c["name"], "{:,}".format(c["population"]),
                  c["arrival_min"] if c["arrival_min"] is not None
                  else "never",
                  str(c.get("t_needed_min", "-")),
                  c["status_at_zero"]] for c in clocks]),
            _text("PHASED SCHEDULE (T+0 = breach confirmed):"),
            _list(sched),
            _warning("Walking-time travel is a LOWER bound; roads often "
                     "fail first. RED = vertical evacuation doctrine.")]}


def _final_summary(inc, sim, res, region, stale_items):
    blocks = []
    if not sim:
        blocks.append(_text("{} has monitoring data but no completed "
                            "simulation. Run a breach scenario, then "
                            "regenerate this report.".format(inc.name)))
    else:
        risk = res.get("risk", {})
        ev = res.get("evacuation") or {}
        red = sum(1 for c in ev.get("clocks", [])
                  if c.get("status_at_zero") == "RED")
        band = risk.get("band", "-")
        recs_by_band = {
            "EXTREME": ["Immediate precautionary evacuation (vertical for "
                        "RED, route-out for AMBER).",
                        "24x7 monitoring; re-scan every satellite pass; "
                        "re-run on any observed growth.",
                        "Alert SDRF/NDRF and district administration."],
            "HIGH": ["Precautionary evacuation of low-lying settlements.",
                     "12-hourly satellite scans; pre-position rescue teams.",
                     "Brief settlements on warning signals."],
            "MODERATE": ["Intensify monitoring; complete exposure mapping.",
                         "Run p90 parameter scenarios to bound the risk."],
            "LOW": ["Routine surveillance; reassess if the growth engine "
                    "flags expansion."]}
        recs = recs_by_band.get(band, [])
        summary = ("ASSESSMENT: peak discharge {:,.0f} m3/s, {} km2 "
                   "inundation along {} km, {:,} people in corridor. "
                   "Risk {} ({}).".format(
                       res.get("breach", {}).get("peak_Q_m3s", 0),
                       res.get("inundation", {}).get("max_area_km2"),
                       res.get("inundation", {}).get("corridor_km"),
                       res.get("exposure", {}).get(
                           "total_population_exposed", 0),
                       risk.get("tdri", "-"), band))
        if red:
            summary += (" {} settlement(s) cannot self-evacuate - vertical "
                        "doctrine applies.".format(red))
        blocks.append(_text(summary))
        blocks.append(_list(["RECOMMENDATION {}: {}".format(i + 1, r)
                             for i, r in enumerate(recs)]))
    if stale_items:
        blocks.append(_warning(
            "STALE DATA PRESENT: {} - refresh and regenerate before "
            "operational use.".format("; ".join(stale_items))))
    else:
        blocks.append(_text(
            "DATA CURRENCY: assembled {}. Regenerate after every new scan "
            "or simulation.".format(
                _utcnow().strftime("%Y-%m-%d %H:%M UTC"))))
    return {"heading": "13. Final Summary & Recommendations",
            "blocks": blocks}
