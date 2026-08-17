"""المجدوِل — يعمل باستمرار: ينشر المستحقّ، يخطّط اليوم، ويعيد ملء البنك."""
import logging
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler

from .database import SessionLocal
from . import models, services

log = logging.getLogger("scheduler")


def _tick_publish():
    """كل دقيقة: انشر ما حان وقته."""
    db = SessionLocal()
    try:
        n = services.publish_due_posts(db)
        if n:
            log.info("نُشر %d منشور", n)
    finally:
        db.close()


def _daily_plan():
    """يوميًا: خطّط منشورات اليوم وأعد ملء البنك لكل علامة نشطة."""
    db = SessionLocal()
    try:
        for brand in db.query(models.Brand).filter(models.Brand.active == True).all():  # noqa: E712
            services.refill_brand_bank(db, brand)
            posts = services.plan_day(db, brand)
            log.info("العلامة %s: جُدول %d منشور لليوم", brand.name, len(posts))
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler:
    sched = BackgroundScheduler(timezone="UTC")
    # نشر المستحقّ كل دقيقة
    sched.add_job(_tick_publish, "interval", minutes=1, id="publish", replace_existing=True)
    # تخطيط يومي عند منتصف الليل + مرة عند الإقلاع
    sched.add_job(_daily_plan, "cron", hour=0, minute=5, id="daily", replace_existing=True)
    sched.add_job(_daily_plan, "date", run_date=datetime.now(), id="bootstrap")
    sched.start()
    log.info("المجدوِل يعمل.")
    return sched
