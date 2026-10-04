"""In-process async job queue: progress, cancellation, TTL eviction."""
import asyncio, time, uuid, traceback

TTL_SECONDS = 3600
jobs: dict = {}
_queue: asyncio.Queue = None

class JobCancelled(Exception):
    pass

def install(loop):
    global _queue
    _queue = asyncio.Queue()
    loop.create_task(_worker())

def submit(fn) -> str:
    now = time.time()
    for k in [k for k, v in jobs.items()
              if v["status"] in ("DONE", "FAILED", "CANCELLED")
              and now - v["done_at"] > TTL_SECONDS]:
        jobs.pop(k, None)
    jid = uuid.uuid4().hex[:12]
    rec = {"id": jid, "status": "RUNNING", "progress": 0,
           "error": None, "cancel": False, "done_at": None}
    jobs[jid] = rec
    _queue.put_nowait((fn, rec))
    return jid

async def _worker():
    while True:
        fn, rec = await _queue.get()
        try:
            await asyncio.to_thread(fn, rec)
            if rec["status"] == "RUNNING":
                rec["status"] = "DONE"; rec["progress"] = 100
        except JobCancelled:
            rec["status"] = "CANCELLED"; rec["error"] = "Cancelled by user"
        except Exception as e:
            rec["status"] = "FAILED"; rec["error"] = f"{e}"
            traceback.print_exc()
        finally:
            rec["done_at"] = time.time()

def get(jid):
    rec = jobs.get(jid)
    if not rec:
        return {"status": "NOT_FOUND", "progress": 0, "error": None, "cancel": False}
    return {k: rec[k] for k in ("id", "status", "progress", "error", "cancel")}

def cancel(jid):
    rec = jobs.get(jid)
    if rec and rec["status"] == "RUNNING":
        rec["cancel"] = True
        return True
    return False
