-- Upgrade path for existing v4.0 installs. Idempotent guards where SQLite
-- allows; on Postgres wrap in DO blocks or use IF NOT EXISTS (PG 9.6+).
ALTER TABLE incidents ADD COLUMN is_manual INTEGER DEFAULT 0;
CREATE TABLE IF NOT EXISTS lake_observations (
  id INTEGER PRIMARY KEY, candidate_id VARCHAR(32), scene_id VARCHAR(120),
  area_m2 REAL, wse_m REAL, volume_m3 REAL,
  observed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE UNIQUE INDEX IF NOT EXISTS ix_obs_cand_scene
  ON lake_observations(candidate_id, scene_id);
CREATE TABLE IF NOT EXISTS monitoring_zones (
  id VARCHAR(32) PRIMARY KEY, name VARCHAR(120), lat1 REAL, lon1 REAL,
  lat2 REAL, lon2 REAL, lookback_days INTEGER DEFAULT 30,
  scan_interval_hr INTEGER DEFAULT 12, enabled INTEGER DEFAULT 1,
  last_scan_at TIMESTAMP, river_buffer_m REAL DEFAULT 300,
  roi_polygon TEXT, created_by VARCHAR(64),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS lake_candidates (
  id VARCHAR(32) PRIMARY KEY, zone_id VARCHAR(32), lat REAL, lon REAL,
  bbox TEXT, area_m2 REAL, depth_m REAL, volume_m3 REAL, wse_m REAL,
  score REAL, compactness REAL, river_adjacency REAL,
  status VARCHAR(12) DEFAULT 'DETECTED', growing INTEGER DEFAULT 0,
  alert_level VARCHAR(10) DEFAULT 'NONE', first_seen_scene VARCHAR(120),
  last_seen_scene VARCHAR(120),
  first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  verified_by VARCHAR(64), incident_id VARCHAR(32));
