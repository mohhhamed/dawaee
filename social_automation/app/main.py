"""نقطة الدخول: FastAPI + المجدوِل + نقاط التحكم + لوحة تحكم بسيطة."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .database import Base, engine, get_db, SessionLocal
from . import models, services
from .seed import seed_brands
from .scheduler import start_scheduler
from .config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


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


# ----------------------- نماذج الطلبات -----------------------
class SourceIn(BaseModel):
    brand_slug: str
    description: str = ""
    image_url: str = ""


# ----------------------- نقاط الـ API ------------------------
@app.get("/api/brands")
def list_brands(db: Session = Depends(get_db)):
    out = []
    for b in db.query(models.Brand).all():
        unused = db.query(models.Asset).filter(
            models.Asset.brand_id == b.id, models.Asset.used == False).count()  # noqa: E712
        scheduled = db.query(models.Post).filter(
            models.Post.brand_id == b.id, models.Post.status == "scheduled").count()
        published = db.query(models.Post).filter(
            models.Post.brand_id == b.id, models.Post.status == "published").count()
        out.append({
            "id": b.id, "slug": b.slug, "name": b.name, "field": b.field,
            "daily": {"posts": b.schedule.daily_posts, "stories": b.schedule.daily_stories,
                      "reels": b.schedule.daily_reels} if b.schedule else {},
            "bank_unused": unused, "scheduled": scheduled, "published": published,
        })
    return out


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
    """نشر فوري لكل ما حان وقته (لأغراض الاختبار)."""
    return {"published": services.publish_due_posts(db)}


@app.get("/api/posts")
def list_posts(status: str = "", db: Session = Depends(get_db)):
    q = db.query(models.Post).order_by(models.Post.scheduled_at.asc())
    if status:
        q = q.filter(models.Post.status == status)
    return [{
        "id": p.id, "brand_id": p.brand_id, "fmt": p.fmt, "status": p.status,
        "caption": p.caption[:80], "media_url": p.media_url,
        "scheduled_at": p.scheduled_at.isoformat() if p.scheduled_at else None,
        "external_post_id": p.external_post_id, "error": p.error,
    } for p in q.limit(200).all()]


# ----------------------- لوحة تحكم بسيطة ---------------------
@app.get("/", response_class=HTMLResponse)
def dashboard():
    mode = "تجريبي (Mock)" if settings.is_mock else "مباشر (Live)"
    return f"""<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>لوحة التحكم</title>
<style>
 body{{font-family:'Segoe UI',Tahoma,sans-serif;background:#0f1516;color:#e8eded;margin:0;padding:24px}}
 h1{{margin:0 0 4px}} .mode{{color:#2bbdaa;font-weight:700}}
 .card{{background:#161d1f;border:1px solid #28353a;border-radius:12px;padding:16px;margin:12px 0}}
 button{{background:#0e9c8a;color:#fff;border:0;border-radius:8px;padding:8px 14px;cursor:pointer;font-size:14px}}
 input,textarea,select{{width:100%;padding:8px;margin:4px 0;background:#0f1516;color:#e8eded;border:1px solid #28353a;border-radius:8px}}
 pre{{background:#0f1516;padding:12px;border-radius:8px;overflow:auto;direction:ltr;text-align:left}}
 .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}}
</style></head><body>
<h1>أتمتة السوشيال ميديا</h1><p>وضع التشغيل: <span class="mode">{mode}</span></p>
<div class="card"><h3>العلامات</h3><div id="brands" class="grid">جارِ التحميل…</div></div>
<div class="card"><h3>إضافة مصدر (وصف/صورة) وتوليد محتوى</h3>
 <select id="bslug"></select>
 <textarea id="desc" placeholder="وصف المنتج/المحتوى"></textarea>
 <input id="img" placeholder="رابط صورة (اختياري)">
 <button onclick="addSource()">حلّل وولّد المحتوى</button>
 <pre id="out"></pre>
</div>
<div class="card"><button onclick="runNow()">نشر فوري لما حان وقته (اختبار)</button>
 <pre id="run"></pre></div>
<script>
async function load(){{
  const bs=await (await fetch('/api/brands')).json();
  document.getElementById('brands').innerHTML=bs.map(b=>`<div class="card">
   <b>${{b.name}}</b> — ${{b.field}}<br>يوميًا: ${{b.daily.posts}} منشور · ${{b.daily.stories}} ستوري · ${{b.daily.reels}} ريلز
   <br>البنك: ${{b.bank_unused}} · مجدول: ${{b.scheduled}} · منشور: ${{b.published}}
   <br><button onclick="plan('${{b.slug}}')">خطّط اليوم</button></div>`).join('');
  document.getElementById('bslug').innerHTML=bs.map(b=>`<option value="${{b.slug}}">${{b.name}}</option>`).join('');
}}
async function addSource(){{
  const r=await fetch('/api/sources',{{method:'POST',headers:{{'Content-Type':'application/json'}},
   body:JSON.stringify({{brand_slug:bslug.value,description:desc.value,image_url:img.value}})}});
  document.getElementById('out').textContent=JSON.stringify(await r.json(),null,2);load();
}}
async function plan(s){{await fetch('/api/brands/'+s+'/plan',{{method:'POST'}});load();}}
async function runNow(){{
  const r=await fetch('/api/run-now',{{method:'POST'}});
  document.getElementById('run').textContent=JSON.stringify(await r.json(),null,2);load();
}}
load();
</script></body></html>"""
