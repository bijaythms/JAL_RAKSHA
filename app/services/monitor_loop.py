"""Background scheduler: scans due zones every 15 min, per-zone timeout."""
import asyncio, traceback
from datetime import datetime, timedelta, timezone
from ..db import SessionLocal, MonitoringZone
from . import detection


async def _scan_with_timeout(zid):
    try:
        return await asyncio.wait_for(detection.scan_zone(zid), timeout=600)
    except asyncio.TimeoutError:
        return {"ok": False, "error": "scan timed out after 600 s"}


async def monitor_loop():
    while True:
        try:
            db = SessionLocal()
            try:
                due = [z.id for z in db.query(MonitoringZone)
                       .filter(MonitoringZone.enabled == True).all()
                       if not z.last_scan_at or
                       datetime.now(timezone.utc) - z.last_scan_at >=
                       timedelta(hours=z.scan_interval_hr)]
            finally:
                db.close()
            for zid in due:
                try:
                    r = await _scan_with_timeout(zid)
                    if not r.get("ok"):
                        print(f"[monitor] {zid}: {r.get('error', 'failed')}")
                except Exception:
                    traceback.print_exc()
                await asyncio.sleep(30)
        except Exception:
            traceback.print_exc()
        await asyncio.sleep(900)


def install(loop):
    loop.create_task(monitor_loop())
