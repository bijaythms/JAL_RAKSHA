"""JWT auth, roles, rate limiting, audit, text sanitization."""
import hmac, hashlib, base64, json, time, os, re
from datetime import datetime, timedelta, timezone
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .config import cfg
from .db import SessionLocal, User, AuditLog

bearer = HTTPBearer(auto_error=False)
_ROLES = {"viewer": 0, "reporter": 1, "analyst": 2, "admin": 3}

def hash_password(pw: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 200_000)
    return f"{salt.hex()}${dk.hex()}"

def verify_password(pw: str, stored: str) -> bool:
    try:
        salt_h, dk_h = stored.split("$")
        dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt_h), 200_000)
        return hmac.compare_digest(dk.hex(), dk_h)
    except Exception:
        return False

def _b64(d): return base64.urlsafe_b64encode(d).rstrip(b"=").decode()
def _unb64(s): return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))

def create_token(username: str, role: str) -> str:
    h = _b64(json.dumps({"alg": cfg.JWT_ALG, "typ": "JWT"}).encode())
    p = _b64(json.dumps({"sub": username, "role": role,
        "exp": (datetime.now(timezone.utc) +
                timedelta(hours=cfg.TOKEN_HOURS)).timestamp()}).encode())
    s = _b64(hmac.new(cfg.JWT_SECRET.encode(), f"{h}.{p}".encode(),
                      hashlib.sha256).digest())
    return f"{h}.{p}.{s}"

def decode_token(token: str):
    try:
        h, p, s = token.split(".")
        expect = _b64(hmac.new(cfg.JWT_SECRET.encode(),
                               f"{h}.{p}".encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(s, expect): return None
        payload = json.loads(_unb64(p))
        if payload.get("exp", 0) < time.time(): return None
        return payload
    except Exception:
        return None

def get_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    # In development/demo mode allow unauthenticated as viewer only
    if creds is None:
        if cfg.ENV == "development":
            return {"sub": "anonymous", "role": "viewer"}
        raise HTTPException(401, "Authentication required. Please log in.")
    payload = decode_token(creds.credentials)
    if not payload:
        if cfg.ENV == "development":
            return {"sub": "anonymous", "role": "viewer"}
        raise HTTPException(401, "Invalid or expired token. Please log in again.")
    return payload

def require_role(minimum: str):
    def dep(user=Depends(get_user)):
        if _ROLES.get(user["role"], -1) < _ROLES[minimum]:
            raise HTTPException(403, f"Requires role '{minimum}' or higher")
        return user
    return dep

def audit(db, username, action, detail=""):
    db.add(AuditLog(username=username, action=action, detail=str(detail)[:2000]))

_TAG = re.compile(r"<[^>]*>")
def sanitize_text(s: str, limit: int = 2000) -> str:
    return _TAG.sub("", (s or ""))[:limit]

_hits: dict = {}
def rate_limit(request: Request):
    ip = request.client.host if request.client else "?"
    now = time.time()
    window = [t for t in _hits.get(ip, []) if now - t < 60]
    if len(window) >= cfg.RATE_LIMIT_PER_MIN:
        raise HTTPException(429, "Rate limit exceeded")
    window.append(now)
    _hits[ip] = window
    if len(_hits) > 5000:
        for k in [k for k, v in _hits.items() if not v or now - v[-1] > 120]:
            _hits.pop(k, None)
