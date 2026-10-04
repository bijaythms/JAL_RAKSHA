-- JAL-RAKSHA v4.1 initial schema (fresh installs; create_all also handles this)
-- Apply only when managing the schema manually (e.g., Postgres migration).
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY, username VARCHAR(64) UNIQUE, pw_hash VARCHAR(256),
  role VARCHAR(16), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS incidents (
  id VARCHAR(32) PRIMARY KEY, name VARCHAR(200), incident_type VARCHAR(40),
  river_name VARCHAR(120) DEFAULT '', lat REAL, lon REAL,
  region VARCHAR(120) DEFAULT '', status VARCHAR(30) DEFAULT 'NEW_ANALYSIS',
  centerline TEXT DEFAULT '[]', dem_upload_id VARCHAR(32),
  is_manual INTEGER DEFAULT 0, created_by VARCHAR(64),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS uploads (
  id VARCHAR(32) PRIMARY KEY, kind VARCHAR(24), original_name VARCHAR(255),
  stored_name VARCHAR(64), incident_id VARCHAR(32), meta TEXT DEFAULT '{}',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS assets (
  id INTEGER PRIMARY KEY, incident_id VARCHAR(32), kind VARCHAR(20),
  name VARCHAR(120), lat REAL, lon REAL, population INTEGER DEFAULT 0,
  buildings INTEGER DEFAULT 0, livestock INTEGER DEFAULT 0,
  attributes TEXT DEFAULT '{}', source VARCHAR(24) DEFAULT 'seed',
  critical INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS simulations (
  id VARCHAR(32) PRIMARY KEY, incident_id VARCHAR(32), label VARCHAR(120),
  params TEXT, status VARCHAR(16) DEFAULT 'QUEUED', error TEXT DEFAULT '',
  results TEXT DEFAULT '{}', created_by VARCHAR(64),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS damage_reports (
  id VARCHAR(32) PRIMARY KEY, incident_id VARCHAR(32), lat REAL, lon REAL,
  incident_type VARCHAR(40) DEFAULT 'Flood', water_depth_m REAL DEFAULT 0,
  damage_description TEXT, infrastructure_damage TEXT DEFAULT '',
  reporter_name VARCHAR(80) DEFAULT 'Anonymous', photo_path VARCHAR(128),
  status VARCHAR(12) DEFAULT 'PENDING', verified_by VARCHAR(64),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS audit_log (
  id INTEGER PRIMARY KEY, ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  username VARCHAR(64), action VARCHAR(64), detail TEXT DEFAULT '');
