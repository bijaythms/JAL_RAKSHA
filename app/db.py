"""Models, WAL engine, seeding, collision-free IDs, UTC everywhere."""
import json, uuid, os
from datetime import datetime, timezone
from sqlalchemy import (create_engine, Column, String, Float, Integer,
                        DateTime, Text, Boolean, event)
from sqlalchemy.orm import declarative_base, sessionmaker
from .config import cfg

engine = create_engine(
    cfg.DB_URL,
    connect_args={"check_same_thread": False, "timeout": 30},
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

@event.listens_for(engine, "connect")
def set_wal_mode(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA cache_size=-64000")  # 64MB
    cursor.execute("PRAGMA temp_store=MEMORY")
    cursor.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False)
Base = declarative_base()

def utcnow():
    return datetime.now(timezone.utc)

def new_id(prefix):
    return f"{prefix}-{utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, index=True)
    pw_hash = Column(String(256))
    role = Column(String(16))
    created_at = Column(DateTime, default=utcnow)

class Incident(Base):
    __tablename__ = "incidents"
    id = Column(String(32), primary_key=True)
    name = Column(String(200))
    incident_type = Column(String(40))
    river_name = Column(String(120), default="")
    lat = Column(Float); lon = Column(Float)
    region = Column(String(120), default="")
    status = Column(String(30), default="NEW_ANALYSIS")
    centerline = Column(Text, default="[]")
    dem_upload_id = Column(String(32), nullable=True)
    is_manual = Column(Boolean, default=False)
    created_by = Column(String(64))
    created_at = Column(DateTime, default=utcnow)

class Upload(Base):
    __tablename__ = "uploads"
    id = Column(String(32), primary_key=True, default=lambda: new_id("UP"))
    kind = Column(String(24))
    original_name = Column(String(255))
    stored_name = Column(String(64))
    incident_id = Column(String(32), nullable=True, index=True)
    meta = Column(Text, default="{}")
    created_at = Column(DateTime, default=utcnow)

class Asset(Base):
    __tablename__ = "assets"
    id = Column(Integer, primary_key=True)
    incident_id = Column(String(32), index=True)
    kind = Column(String(20))
    name = Column(String(120))
    lat = Column(Float); lon = Column(Float)
    population = Column(Integer, default=0)
    buildings = Column(Integer, default=0)
    livestock = Column(Integer, default=0)
    attributes = Column(Text, default="{}")
    source = Column(String(24), default="seed")
    critical = Column(Boolean, default=False)

class Simulation(Base):
    __tablename__ = "simulations"
    id = Column(String(32), primary_key=True, default=lambda: new_id("SIM"))
    incident_id = Column(String(32), index=True)
    label = Column(String(120), default="")
    params = Column(Text)
    status = Column(String(16), default="QUEUED")
    error = Column(Text, default="")
    results = Column(Text, default="{}")
    created_by = Column(String(64))
    created_at = Column(DateTime, default=utcnow)

class DamageReport(Base):
    __tablename__ = "damage_reports"
    id = Column(String(32), primary_key=True, default=lambda: new_id("DR"))
    incident_id = Column(String(32), index=True)
    lat = Column(Float); lon = Column(Float)
    incident_type = Column(String(40), default="Flood")
    water_depth_m = Column(Float, default=0.0)
    damage_description = Column(Text)
    infrastructure_damage = Column(Text, default="")
    reporter_name = Column(String(80), default="Anonymous")
    photo_path = Column(String(128), nullable=True)
    status = Column(String(12), default="PENDING")
    verified_by = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=utcnow)

class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(Integer, primary_key=True)
    ts = Column(DateTime, default=utcnow)
    username = Column(String(64))
    action = Column(String(64))
    detail = Column(Text, default="")

class MonitoringZone(Base):
    __tablename__ = "monitoring_zones"
    id = Column(String(32), primary_key=True)
    name = Column(String(120))
    lat1 = Column(Float); lon1 = Column(Float)
    lat2 = Column(Float); lon2 = Column(Float)
    lookback_days = Column(Integer, default=30)
    scan_interval_hr = Column(Integer, default=12)
    enabled = Column(Boolean, default=True)
    last_scan_at = Column(DateTime, nullable=True)
    river_buffer_m = Column(Float, default=300.0)
    roi_polygon = Column(Text, nullable=True)
    created_by = Column(String(64))
    created_at = Column(DateTime, default=utcnow)

class LakeCandidate(Base):
    __tablename__ = "lake_candidates"
    id = Column(String(32), primary_key=True)
    zone_id = Column(String(32), index=True)
    lat = Column(Float); lon = Column(Float)
    bbox = Column(Text)
    area_m2 = Column(Float)
    depth_m = Column(Float, nullable=True)
    volume_m3 = Column(Float, nullable=True)
    wse_m = Column(Float, nullable=True)
    score = Column(Float)
    compactness = Column(Float)
    river_adjacency = Column(Float)
    status = Column(String(12), default="DETECTED")
    growing = Column(Boolean, default=False)
    alert_level = Column(String(10), default="NONE")
    first_seen_scene = Column(String(120))
    last_seen_scene = Column(String(120))
    first_seen_at = Column(DateTime, default=utcnow)
    last_seen_at = Column(DateTime, default=utcnow)
    verified_by = Column(String(64), nullable=True)
    incident_id = Column(String(32), nullable=True)

class LakeObservation(Base):
    __tablename__ = "lake_observations"
    id = Column(Integer, primary_key=True)
    candidate_id = Column(String(32), index=True)
    scene_id = Column(String(120))
    area_m2 = Column(Float)
    wse_m = Column(Float, nullable=True)
    volume_m3 = Column(Float, nullable=True)
    observed_at = Column(DateTime, default=utcnow)

def init_db():
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        if not db.query(User).first():
            from .security import hash_password
            db.add(User(username=os.getenv("ADMIN_USERNAME", "admin"),
                        pw_hash=hash_password(
                            os.getenv("ADMIN_PASSWORD", "ChangeMeNow123")),
                        role="admin"))
            db.add(User(username="analyst",
                        pw_hash=hash_password("analyst123"), role="analyst"))
            db.add(User(username="reporter",
                        pw_hash=hash_password("reporter123"), role="reporter"))
        if not db.query(Incident).filter(Incident.id == "JR-DEMO-0001").first():
            db.add(Incident(id="JR-DEMO-0001",
                            name="Rishiganga Valley Landslide Dam (DEMO)",
                            incident_type="Landslide Dam",
                            river_name="Rishiganga River",
                            lat=30.4828, lon=79.7214,
                            region="Chamoli, Uttarakhand",
                            status="ACTIVE_MONITORING", created_by="seed",
                            centerline=json.dumps(_demo_centerline())))
            for a in _demo_assets():
                db.add(Asset(**a))
            db.add(DamageReport(
                incident_id="JR-DEMO-0001", lat=30.4952, lon=79.6980,
                incident_type="Bridge damage", water_depth_m=4.8,
                damage_description="Raini bridge abutment submerged by debris pulse.",
                infrastructure_damage="Road severed.",
                reporter_name="SDRF Unit B", status="VERIFIED", verified_by="seed"))
        if not db.query(MonitoringZone).first():
            for name, la1, lo1, la2, lo2 in _SEED_ZONES:
                db.add(MonitoringZone(id=new_id("MZ"), name=name,
                                      lat1=la1, lon1=lo1, lat2=la2, lon2=lo2,
                                      created_by="seed"))
        db.commit()
    finally:
        db.close()

def _demo_centerline():
    return [[30.4828,79.7214],[30.4840,79.7170],[30.4860,79.7110],
            [30.4880,79.7050],[30.4900,79.6990],[30.4920,79.6920],
            [30.4930,79.6850],[30.4935,79.6780],[30.4940,79.6700],
            [30.4940,79.6620],[30.4942,79.6540],[30.4940,79.6460],
            [30.4940,79.6380],[30.4945,79.6300]]

_SEED_ZONES = [
    ("Chamoli-Dhauliganga corridor", 30.30, 79.55, 30.60, 79.90),
    ("Upper Ganga headwaters (Joshimath)", 30.35, 79.45, 30.70, 79.80),
    ("Satluj-Pareechu (Spiti)", 31.70, 78.20, 32.20, 78.90),
    ("Teesta-Sikkim GLOF belt", 27.80, 88.20, 28.30, 88.90),
    ("Upper Brahmaputra-Subansiri", 27.90, 94.00, 28.40, 94.70),
    ("Chenab-Lahaul valleys", 32.60, 76.60, 33.20, 77.40),
    ("Alaknanda-Nandadevi", 30.10, 79.30, 30.55, 79.75),
]

def _demo_assets():
    S = lambda n, la, lo, p, b, extra=None: dict(
        incident_id="JR-DEMO-0001", kind="settlement", name=n, lat=la, lon=lo,
        population=p, buildings=b, livestock=int(p * 0.8), critical=False,
        attributes=json.dumps(extra or {}), source="seed")
    I = lambda n, la, lo, t: dict(
        incident_id="JR-DEMO-0001", kind="infrastructure", name=n, lat=la,
        lon=lo, population=0, buildings=0, livestock=0, critical=True,
        attributes=json.dumps({"type": t}), source="seed")
    A = lambda n, la, lo, ha, crop: dict(
        incident_id="JR-DEMO-0001", kind="agriculture", name=n, lat=la, lon=lo,
        population=0, buildings=0, livestock=0, critical=False,
        attributes=json.dumps({"area_ha": ha, "crop": crop}), source="seed")
    return [
        S("Raini Village", 30.4952, 79.6980, 620, 112, {"district": "Chamoli"}),
        S("Selang", 30.4960, 79.6700, 310, 58),
        S("Tapovan Township", 30.4940, 79.6400, 980, 210),
        S("Joshimath Periphery", 30.4930, 79.6290, 1510, 340),
        I("Raini Footbridge", 30.4948, 79.6990, "bridge"),
        I("Rishiganga HEP Intake", 30.4890, 79.7000, "power intake"),
        I("Tapovan Barrage", 30.4941, 79.6390, "barrage"),
        I("NH-7 Road Km 22", 30.4930, 79.6650, "highway"),
        I("Primary Health Centre", 30.4944, 79.6410, "hospital"),
        I("Sewage Treatment Plant", 30.4946, 79.6360, "utility"),
        A("Raini terraces", 30.4950, 79.6975, 12.0, "wheat"),
        A("Selang fields", 30.4960, 79.6695, 18.5, "paddy"),
        A("Tapovan orchards", 30.4942, 79.6410, 24.0, "orchard"),
        A("Joshimath periphery farms", 30.4932, 79.6300, 31.0, "vegetables"),
    ]
