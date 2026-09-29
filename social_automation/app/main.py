"""نقطة الدخول: FastAPI + المجدوِل + نقاط التحكم + لوحة تحكم كاملة."""
import logging
import os
import shutil
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .database import Base, engine, get_db, SessionLocal
from . import models, services, runtime_settings as rs
from .seed import seed_brands
from .scheduler import start_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

BASE_DIR = os.path.dirname(__file__)
MEDIA_DIR = os.path.join("data", "media")
os.makedirs(MEDIA_DIR, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_brands(db)
    finally:
        db.close()
    sched = start_scheduler()
    yield
    sched.shutdown(wait=False)


app = FastAPI(title="أتمتة السوشيال ميديا", lifespan=lifespan)
app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")


# ============================ نماذج الطلبات ============================
class SourceIn(BaseModel):
    brand_slug: str
    description: str = ""
    image_url: str = ""


class BrandUpdate(BaseModel):
    name: str | None = None
    field: str | None = None
    timezone: str | None = None
    tone: str | None = None
    hashtags: str | None = None
    fb_page_id: str | None = None
    fb_page_token: str | None = None
    ig_account_id: str | None = None
    daily_posts: int | None = None
    daily_stories: int | None = None
    daily_reels: int | None = None
    times: dict | None = None
    active: bool | None = None


# ============================ الإعدادات والمفاتيح ============================
@app.get("/api/settings")
def get_settings():
    return rs.masked_status()


@app.post("/api/settings")
def save_settings(values: dict):
    # لا نحفظ القيم المُقنّعة "configured" (تعني: اتركها كما هي)
    clean = {k: v for k, v in values.items() if v != "configured"}
    rs.set_many(clean)
    return {"ok": True, "settings": rs.masked_status()}


# ============================ العلامات ============================
def _brand_stats(db: Session, b: models.Brand) -> dict:
    unused = db.query(models.Asset).filter(
        models.Asset.brand_id == b.id, models.Asset.used == False).count()  # noqa: E712
    scheduled = db.query(models.Post).filter(
        models.Post.brand_id == b.id, models.Post.status == "scheduled").count()
    published = db.query(models.Post).filter(
        models.Post.brand_id == b.id, models.Post.status == "published").count()
    return {"bank_unused": unused, "scheduled": scheduled, "published": published}


@app.get("/api/brands")
def list_brands(db: Session = Depends(get_db)):
    out = []
    for b in db.query(models.Brand).all():
        cfg = b.schedule
        out.append({
            "id": b.id, "slug": b.slug, "name": b.name, "field": b.field,
            "active": b.active,
            "daily": {"posts": cfg.daily_posts, "stories": cfg.daily_stories,
                      "reels": cfg.daily_reels} if cfg else {},
            **_brand_stats(db, b),
            "meta_ready": bool(b.fb_page_id and b.fb_page_token),
        })
    return out


@app.get("/api/brands/{slug}")
def get_brand(slug: str, db: Session = Depends(get_db)):
    b = db.query(models.Brand).filter(models.Brand.slug == slug).first()
    if not b:
        raise HTTPException(404, "العلامة غير موجودة")
    cfg = b.schedule
    return {
        "slug": b.slug, "name": b.name, "field": b.field, "timezone": b.timezone,
        "tone": b.tone, "hashtags": b.hashtags, "active": b.active,
        "fb_page_id": b.fb_page_id,
        "fb_page_token": "configured" if b.fb_page_token else "",  # لا نكشف التوكِن
        "ig_account_id": b.ig_account_id,
        "daily_posts": cfg.daily_posts, "daily_stories": cfg.daily_stories,
        "daily_reels": cfg.daily_reels, "times": cfg.times or {},
        **_brand_stats(db, b),
    }


@app.post("/api/brands/{slug}")
def update_brand(slug: str, payload: BrandUpdate, db: Session = Depends(get_db)):
    b = db.query(models.Brand).filter(models.Brand.slug == slug).first()
    if not b:
        raise HTTPException(404, "العلامة غير موجودة")
    data = payload.model_dump(exclude_unset=True)

    # لا نحفظ التوكِن المقنّع "configured" (يعني: اتركه)
    if data.get("fb_page_token") == "configured":
        data.pop("fb_page_token")

    cfg = b.schedule
    for key in ("daily_posts", "daily_stories", "daily_reels", "times"):
        if key in data:
            setattr(cfg, key, data.pop(key))
    for key, val in data.items():
        setattr(b, key, val)
    db.commit()
    return {"ok": True}


# ============================ المصادر والرفع ============================
@app.post("/api/upload")
async def upload_image(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename or "")[1].lower() or ".png"
    if ext not in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
        raise HTTPException(400, "نوع صورة غير مدعوم")
    name = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(MEDIA_DIR, name)
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"url": f"/media/{name}"}


@app.post("/api/sources")
def add_source(payload: SourceIn, db: Session = Depends(get_db)):
    brand = db.query(models.Brand).filter(models.Brand.slug == payload.brand_slug).first()
    if not brand:
        raise HTTPException(404, "العلامة غير موجودة")
    src = models.Source(brand_id=brand.id, description=payload.description,
                        image_url=payload.image_url)
    db.add(src)
    db.commit()
    db.refresh(src)
    assets = services.generate_assets_for_source(db, src)
    return {"source_id": src.id, "analysis": src.ai_analysis, "generated": len(assets)}


# ============================ بنك المحتوى ============================
@app.get("/api/brands/{slug}/assets")
def list_assets(slug: str, db: Session = Depends(get_db)):
    b = db.query(models.Brand).filter(models.Brand.slug == slug).first()
    if not b:
        raise HTTPException(404, "العلامة غير موجودة")
    rows = (db.query(models.Asset).filter(models.Asset.brand_id == b.id)
            .order_by(models.Asset.created_at.desc()).limit(200).all())
    return [{
        "id": a.id, "fmt": a.fmt, "caption": a.caption, "hashtags": a.hashtags,
        "media_url": a.media_url, "used": a.used,
    } for a in rows]


class AssetEdit(BaseModel):
    caption: str | None = None
    hashtags: str | None = None


@app.post("/api/assets/{asset_id}")
def edit_asset(asset_id: int, payload: AssetEdit, db: Session = Depends(get_db)):
    a = db.get(models.Asset, asset_id)
    if not a:
        raise HTTPException(404, "غير موجود")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(a, k, v)
    db.commit()
    return {"ok": True}


@app.delete("/api/assets/{asset_id}")
def delete_asset(asset_id: int, db: Session = Depends(get_db)):
    a = db.get(models.Asset, asset_id)
    if a:
        db.delete(a)
        db.commit()
    return {"ok": True}


# ============================ الجدولة والنشر ============================
@app.post("/api/brands/{slug}/plan")
def plan_today(slug: str, db: Session = Depends(get_db)):
    brand = db.query(models.Brand).filter(models.Brand.slug == slug).first()
    if not brand:
        raise HTTPException(404, "العلامة غير موجودة")
    services.refill_brand_bank(db, brand)
    posts = services.plan_day(db, brand)
    return {"scheduled": len(posts)}


@app.post("/api/run-now")
def run_now(db: Session = Depends(get_db)):
    return {"published": services.publish_due_posts(db)}


@app.get("/api/posts")
def list_posts(status: str = "", slug: str = "", db: Session = Depends(get_db)):
    q = db.query(models.Post)
    if slug:
        b = db.query(models.Brand).filter(models.Brand.slug == slug).first()
        if b:
            q = q.filter(models.Post.brand_id == b.id)
    if status:
        q = q.filter(models.Post.status == status)
    rows = q.order_by(models.Post.scheduled_at.asc()).limit(200).all()
    return [{
        "id": p.id, "brand_id": p.brand_id, "fmt": p.fmt, "status": p.status,
        "caption": p.caption, "media_url": p.media_url,
        "scheduled_at": p.scheduled_at.isoformat() if p.scheduled_at else None,
        "external_post_id": p.external_post_id, "error": p.error,
    } for p in rows]


@app.delete("/api/posts/{post_id}")
def delete_post(post_id: int, db: Session = Depends(get_db)):
    p = db.get(models.Post, post_id)
    if p:
        # أعِد القطعة للبنك إن لم تُنشر بعد
        if p.status == "scheduled" and p.asset_id:
            a = db.get(models.Asset, p.asset_id)
            if a:
                a.used = False
        db.delete(p)
        db.commit()
    return {"ok": True}


# ============================ لوحة التحكم ============================
@app.get("/", response_class=HTMLResponse)
def dashboard():
    return FileResponse(os.path.join(BASE_DIR, "static", "index.html"))
