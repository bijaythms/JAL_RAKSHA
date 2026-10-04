from fastapi import APIRouter, Depends, HTTPException, Query
from ..db import SessionLocal, User, AuditLog
from ..schemas import UserCreate
from ..security import require_role, audit, hash_password

router = APIRouter(prefix="/api/admin", tags=["admin"])

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

@router.get("/users")
def list_users(db=Depends(get_db), user=Depends(require_role("admin"))):
    return [{"username": u.username, "role": u.role,
             "created_at": u.created_at.isoformat()}
            for u in db.query(User).order_by(User.username).all()]

@router.post("/users", status_code=201)
def create_user(body: UserCreate, db=Depends(get_db),
                user=Depends(require_role("admin"))):
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(409, "Username exists")
    db.add(User(username=body.username,
                pw_hash=hash_password(body.password), role=body.role))
    audit(db, user["sub"], "user.create", f"{body.username}:{body.role}")
    db.commit()
    return {"username": body.username, "role": body.role}

@router.delete("/users/{username}")
def delete_user(username: str, db=Depends(get_db),
                user=Depends(require_role("admin"))):
    if username == user["sub"]:
        raise HTTPException(400, "Cannot delete yourself")
    u = db.query(User).filter(User.username == username).first()
    if not u:
        raise HTTPException(404, "User not found")
    db.delete(u); audit(db, user["sub"], "user.delete", username); db.commit()
    return {"ok": True}

@router.get("/audit")
def audit_log(db=Depends(get_db), user=Depends(require_role("admin")),
              limit: int = Query(50, ge=1, le=200),
              offset: int = Query(0, ge=0)):
    q = db.query(AuditLog).order_by(AuditLog.id.desc())
    return {"total": q.count(), "items": [{
        "ts": a.ts.isoformat(), "username": a.username,
        "action": a.action, "detail": a.detail[:200]}
        for a in q.limit(limit).offset(offset).all()]}
