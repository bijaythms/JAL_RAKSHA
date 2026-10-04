import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = BASE_DIR / "uploads"
for d in (DATA_DIR, UPLOADS_DIR):
    d.mkdir(parents=True, exist_ok=True)

class Config:
    APP_NAME = "JAL-RAKSHA"
    VERSION = "4.1.0"
    ENV = os.getenv("JR_ENV", "development")
    JWT_SECRET = os.getenv("JWT_SECRET", "dev-insecure-secret")
    JWT_ALG = "HS256"
    TOKEN_HOURS = 24
    if ENV == "production" and JWT_SECRET == "dev-insecure-secret":
        raise RuntimeError("JR_ENV=production but JWT_SECRET is unset/default. "
                           "Set a long random JWT_SECRET.")
    CORS_ORIGINS = [o.strip() for o in
                    os.getenv("CORS_ORIGINS", "http://localhost:8000").split(",")
                    if o.strip()]
    DB_PATH = os.getenv("DB_PATH", str(DATA_DIR / "jalraksha.db"))
    DB_URL = f"sqlite:///{DB_PATH}"
    MAX_UPLOAD_MB = 100
    MAX_PHOTO_MB = 5
    RATE_LIMIT_PER_MIN = 240
    MC_RUNS = int(os.getenv("MC_RUNS", "120"))
    IST = "Asia/Kolkata"
    CDSE_USERNAME = os.getenv("CDSE_USERNAME", "")
    CDSE_PASSWORD = os.getenv("CDSE_PASSWORD", "")

cfg = Config()
