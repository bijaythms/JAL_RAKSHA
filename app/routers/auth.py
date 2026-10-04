from fastapi import APIRouter, Depends, HTTPException
from ..db import SessionLocal, User
from ..schemas import LoginIn, PasswordChange
from ..security import (verify_password, create_token, get_user,
                         hash_password, audit)

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/token")
def login(body: LoginIn):
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.username == body.username).first()
        if not u or not verify_password(body.password, u.pw_hash):
            raise HTTPException(401, "Invalid credentials")
        return {"token": create_token(u.username, u.role),
                "role": u.role, "username": u.username}
    finally:
        db.close()

@router.get("/me")
def me(user=Depends(get_user)):
    return user

@router.patch("/password")
def change_password(body: PasswordChange, user=Depends(get_user)):
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.username == user["sub"]).first()
        if not u or not verify_password(body.old_password, u.pw_hash):
            raise HTTPException(401, "Old password incorrect")
        u.pw_hash = hash_password(body.new_password)
        audit(db, user["sub"], "user.password_change", user["sub"])
        db.commit()
        return {"ok": True}
    finally:
        db.close()
