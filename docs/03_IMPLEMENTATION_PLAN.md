# Implementation Plan

## Phase 0 - Local deployment (day 1)
pip install -r requirements.txt; set .env (JWT_SECRET, ADMIN_PASSWORD,
optional CDSE creds); pytest tests/ -q (must be green); python run.py;
verify the demo incident end-to-end (breach -> visual -> full report).

## Phase 1 - Data readiness (week 1)
- Free CDSE account; verify one S1 scene decodes and the sigma0 offset
  against its metadata (the -83 dB constant is the most VERIFY-critical
  number in the stack).
- Fetch one GLO-30 tile manually to confirm the AWS URL pattern.
- Replace placeholder unit costs in impact_models.THRESHOLDS with
  district Schedule of Rates.

## Phase 2 - Site calibration (weeks 2-4)
- Draw real centerlines for priority incidents.
- Upload exposure CSVs (villages, critical infra, agri parcels with area_ha).
- Refine region polygons for boundary cities; set per-zone river buffers.

## Phase 3 - Back-analysis validation (weeks 4-8) - CREDIBILITY GATE
Replay Chamoli 2021 and Sikkim South Lhonak 2023 through detector + breach
chain; compare predicted vs observed extents, arrival times, lake growth.
Publish POD/FAR (detection) and peak-Q error (breach) here. Tune thresholds
and re-run to confirm improvement.

## Phase 4 - Operational pilot (months 2-4)
3 districts (Himalayan GLOF / Ghats landslide / plains embankment). Train
officials (manual console, reports, verification). Email alert digest first;
SMS/IVR needs NDMA/SDMA integration. Production: uvicorn behind nginx,
Postgres, Celery+Redis (jobs.py is drop-in shaped), log aggregation.

## Phase 5 - Roadmap
WorldPop grid for national exposure; HEC-RAS 2D job adapter; CAP/SACHET
alerting; offline PWA field client; U-Net water classifier on S2.

## Risk register (top 5)
1. SAR calibration wrong -> all detection biased (Phase 1 verification).
2. Empirical equations misapplied to natural dams (ensemble spread always
   shown; Phase 3 replay).
3. Satellite API changes (cached baselines; graceful degradation).
4. Officials over-trust numbers (provenance + limitations on every
   artifact; training includes reading the manifest).
5. DB growth (job TTL, snapshot archiving, Postgres partitioning).
