import uuid, io
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, \
    Form, Query
from sqlalchemy.orm import Session
from ..db import SessionLocal, DamageReport, Incident, new_id
from ..schemas import VerifyIn
from ..security import require_role, audit, sanitize_text
from ..config import cfg, UPLOADS_DIR
from PIL import Image

router = APIRouter(prefix="/api/damage-reports", tags=["field"])

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

@router.get("")
def list_damage(incident_id: str = None, db=Depends(get_db),
                user=Depends(require_role("viewer")),
                limit: int = Query(50, ge=1, le=200),
                offset: int = Query(0, ge=0)):
    q = db.query(DamageReport)
    if incident_id:
        q = q.filter(DamageReport.incident_id == incident_id)
    q = q.order_by(DamageReport.created_at.desc())
    total = q.count()
    return {"total": total, "items": [{
        "id": d.id, "incident_id": d.incident_id, "lat": d.lat, "lon": d.lon,
        "incident_type": d.incident_type, "water_depth_m": d.water_depth_m,
        "damage_description": d.damage_description,
        "infrastructure_damage": d.infrastructure_damage,
        "reporter_name": d.reporter_name, "status": d.status,
        "photo_url": f"/uploads/{d.photo_path}" if d.photo_path else None,
        "created_at": d.created_at.isoformat()}
        for d in q.limit(limit).offset(offset).all()]}

@router.post("", status_code=201)
async def submit(
    incident_id: str = Form(...),
    lat: float = Form(..., ge=-90, le=90),
    lon: float = Form(..., ge=-180, le=180),
    incident_type: str = Form("Flood"),
    water_depth_m: float = Form(0.5, ge=0, le=100),
    damage_description: str = Form(..., min_length=5),
    infrastructure_damage: str = Form(""),
    reporter_name: str = Form("Anonymous"),
    photo: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    user=Depends(require_role("reporter"))):
    if not db.get(Incident, incident_id):
        raise HTTPException(404, "Incident not found")
    photo_path = None
    if photo and photo.filename:
        ext = "." + photo.filename.rsplit(".", 1)[-1].lower()
        if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
            raise HTTPException(400, "Photo must be JPG/PNG/WebP")
        raw = await photo.read()
        if len(raw) > cfg.MAX_PHOTO_MB * 1024 * 1024:
            raise HTTPException(413, f"Photo max {cfg.MAX_PHOTO_MB} MB")
        try:
            img = Image.open(io.BytesIO(raw)); img.verify()
        except Exception:
            raise HTTPException(400, "Corrupt or non-image file")
        photo_path = f"{uuid.uuid4().hex}{ext}"
        (UPLOADS_DIR / photo_path).write_bytes(raw)
    d = DamageReport(id=new_id("DR"), incident_id=incident_id,
                     lat=lat, lon=lon,
                     incident_type=sanitize_text(incident_type, 40),
                     water_depth_m=water_depth_m,
                     damage_description=sanitize_text(damage_description),
                     infrastructure_damage=sanitize_text(infrastructure_damage),
                     reporter_name=sanitize_text(reporter_name, 80) or "Anonymous",
                     photo_path=photo_path)
    db.add(d); audit(db, user["sub"], "damage.submit", d.id); db.commit()
    return {"id": d.id, "status": d.status,
            "photo_url": f"/uploads/{photo_path}" if photo_path else None}

@router.patch("/{rid}/verify")
def verify(rid: str, body: VerifyIn, db=Depends(get_db),
           user=Depends(require_role("analyst"))):
    d = db.get(DamageReport, rid)
    if not d:
        raise HTTPException(404, "Report not found")
    d.status = body.status; d.verified_by = user["sub"]
    audit(db, user["sub"], f"damage.{body.status.lower()}", rid); db.commit()
    return {"id": d.id, "status": d.status}
