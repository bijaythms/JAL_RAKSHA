import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .config import cfg, UPLOADS_DIR
from .db import init_db, SessionLocal, Simulation
from .security import rate_limit
from . import jobs
from .routers import (auth, incidents, simulations, field, admin,
                      hydrology, satellite, detection, india, calibration, costs, dams, fastflood)

@asynccontextmanager
async def lifespan(app):
    init_db()
    jobs.install(asyncio.get_running_loop())
    db = SessionLocal()          # recover simulations orphaned by restart
    try:
        stale = db.query(Simulation).filter(
            Simulation.status.in_(("QUEUED", "RUNNING"))).all()
        for s in stale:
            s.status, s.error = "FAILED", "Interrupted by server restart - re-run."
        if stale:
            db.commit()
    finally:
        db.close()
    from .services.monitor_loop import install as install_monitor
    install_monitor(asyncio.get_running_loop())
    yield

app = FastAPI(title=f"{cfg.APP_NAME} API", version=cfg.VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cfg.CORS_ORIGINS, allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

@app.middleware("http")
async def rl_and_headers(request: Request, call_next):
    try:
        if request.url.path.startswith("/api"):
            rate_limit(request)
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "no-referrer-when-downgrade"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://unpkg.com https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://unpkg.com https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com data:; "
        "img-src 'self' data: blob: https://*.arcgisonline.com https://*.google.com https://*.googleapis.com https://*.openstreetmap.org https://unpkg.com; "
        "frame-src 'self' data: blob:; "
        "connect-src 'self'")
    return response

for r in (auth, incidents, simulations, field, admin,
          hydrology, satellite, detection, india, calibration, costs, dams, fastflood):
    app.include_router(r.router)

@app.get("/api/status")
def status():
    return {"app": cfg.APP_NAME, "version": cfg.VERSION,
            "subsystems": {
                "breach_engine": "level-pool + erosion (Hanson/Temple) or "
                                 "overtopping-only (concrete/masonry)",
                "flood_engine": "2D DEM cross-section bathtub solver (Priority-Flood on GLO-30 30m DEM) + 1D Muskingum-Cunge diffusion routing fallback. NOT full Saint-Venant 2D SWE. Suitable for broad valley flood-extent planning.",
                "exposure": "exact corridor tests",
                "uncertainty": f"Monte Carlo, {cfg.MC_RUNS} runs, cancellable",
                "detection": "S1 SAR / S2 / Landsat, water-frequency baseline, "
                             "river-buffer + ROI masking, GLO-30 geometry",
                "job_queue": "asyncio + progress + cancel + restart recovery",
                "auth": "JWT; roles viewer/reporter/analyst/admin; audited"},
            "storage": "UTC (display IST)"}

app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")
app.mount("/", StaticFiles(directory=str(
    Path(__file__).resolve().parent.parent / "frontend"), html=True),
    name="frontend")
