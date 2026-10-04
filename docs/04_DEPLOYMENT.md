# Deployment & Operations

## Environment
JR_ENV=production (refuses insecure JWT_SECRET)
JWT_SECRET=<64+ random chars>
CORS_ORIGINS=https://jr.example.gov.in
DB_PATH=/var/lib/jalraksha/jalraksha.db (Postgres in Phase 4)
CDSE_USERNAME / CDSE_PASSWORD (free account)
MC_RUNS=120

## Migrations
Fresh install: create_all handles everything (or apply 001+002 manually).
Upgrade from v4.0: stop server, apply migrations/002_*, start.

## Operations checklist
- Daily: /api/status; scan monitor tab for VOID scenes.
- Weekly: review growth alerts; regenerate full reports for VERIFIED
  candidates.
- Monthly: DEM cache TTL refresh; archive old simulations; run the test
  suite against a staging copy of production config.

## Security posture
JWT auth, 4 roles, audit log on every write, sanitized uploads (uuid
names, PIL image verification), XSS escaping client+server, strict CORS,
security headers (CSP/nosniff/frame-deny/referrer), rate limiting
(240/min/IP), PBKDF2-256 200k iterations, production secret enforcement.
Residual risks documented in 05_LIMITATIONS.md.
