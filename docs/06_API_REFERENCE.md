# API Reference (summary - full interactive docs at /docs)

Auth: Authorization: Bearer <token>. Roles: viewer < reporter < analyst < admin.
All timestamps UTC ISO-8601. Rate limit 240 req/min/IP.

AUTH          POST /api/auth/token | GET /me | PATCH /password
INCIDENTS     GET/POST /api/incidents - GET/PATCH/DELETE /api/incidents/{id}
              PUT /{id}/centerline - GET /{id}/assets - GET /{id}/dem
              POST /{id}/uploads (CSV DEM / CSV assets / GeoJSON points)
              GET /{id}/full-report?run_id  <- 13-section comprehensive report
SIMULATIONS   POST /api/simulations?incident_id (full BreachParams body)
              POST /api/simulations/manual (provenance in response)
              GET/DELETE /api/simulations/{id} - GET /{id}/visual
              GET /{id}/provenance - GET /{id}/report (deprecated)
              GET /{id}/export/{nodes.csv|exposure.csv|flood.geojson}
JOBS          GET /api/jobs/{jid} - POST /api/jobs/{jid}/cancel
FIELD         GET/POST /api/damage-reports - PATCH /{rid}/verify
HYDROLOGY     POST /inflow - GET /cn-table - GET /usgs-gauge/{site}
              GET /breach-estimates?volume_m3&height_m&mode
SATELLITE     GET /search?incident_id&start&end&source&cloud_max
              POST /analyze - POST /change
DETECTION     GET/POST /api/detection/zones - DELETE /zones/{zid}
              PUT/DELETE /zones/{zid}/roi - PUT /zones/{zid}/buffer
              POST /zones/{zid}/scan - POST /zones/{zid}/baseline/rebuild
              GET /candidates - PATCH /candidates/{cid}/verify
              POST /candidates/{cid}/promote - GET /candidates/{cid}/growth
              GET /alerts
INDIA         GET /region?lat&lon - PUT /region-override - GET /sites
              POST /snowmelt-inflow - POST /national-run
ADMIN         GET/POST /api/admin/users - DELETE /users/{u} - GET /audit
STATUS        GET /api/status

BreachParams: stored_volume_m3<=1e11, dam_height_m<=400, breach_width_m<=600,
dam_material includes Concrete/Masonry (overtopping-only paradigm),
with_uncertainty enables Monte Carlo. Concrete/Masonry results carry
engine:"v4.1-overtop".

Errors: 401 auth - 403 role - 404 missing - 413 oversize - 422 validation
(names the failing field) - 429 rate limit - 500 logged server-side.
