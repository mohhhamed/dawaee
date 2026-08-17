"""منطق التنسيق: تحليل المصادر، توليد بنك المحتوى، وجدولة النشر بالكمّيات."""
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from . import models
from .ai import vision, text, image
from .publishers import facebook, instagram


# ----------------------------------------------------------------------
#  1) تحليل المصدر وتوليد قطع محتوى منه
# ----------------------------------------------------------------------
def analyze_source(db: Session, source: models.Source) -> str:
    """يحلّل الصورة/الوصف بالرؤية ويحفظ النتيجة."""
    result = vision.analyze(source.description, source.image_url)
    source.ai_analysis = result
    db.commit()
    return result


def generate_assets_for_source(db: Session, source: models.Source,
                               per_format: dict | None = None) -> list[models.Asset]:
    """يولّد قطع محتوى (post/story/reel) من مصدر واحد ويضيفها لبنك المحتوى."""
    if not source.ai_analysis:
        analyze_source(db, source)

    brand = source.brand
    per_format = per_format or {"post": 2, "story": 1, "reel": 1}
    created: list[models.Asset] = []

    for fmt, count in per_format.items():
        for _ in range(count):
            txt = text.generate_caption(brand.name, source.ai_analysis, fmt,
                                        brand.tone, brand.hashtags)
            prompt = f"{brand.field} — {source.description[:80]}"
            media = image.generate_image(prompt, fmt)
            asset = models.Asset(
                brand_id=brand.id, source_id=source.id, fmt=fmt,
                caption=txt["caption"], hashtags=txt["hashtags"],
                media_url=media, prompt=prompt,
            )
            db.add(asset)
            created.append(asset)

    db.commit()
    return created


def refill_brand_bank(db: Session, brand: models.Brand) -> int:
    """يعيد ملء بنك المحتوى إن نزل عدد القطع غير المستخدمة تحت الحد."""
    threshold = brand.schedule.refill_threshold if brand.schedule else 20
    unused = (db.query(models.Asset)
              .filter(models.Asset.brand_id == brand.id, models.Asset.used == False)  # noqa: E712
              .count())
    if unused >= threshold:
        return 0

    total = 0
    for source in brand.sources:
        total += len(generate_assets_for_source(db, source))
    return total


# ----------------------------------------------------------------------
#  2) الجدولة بالكمّيات اليومية
# ----------------------------------------------------------------------
def _pick_asset(db: Session, brand_id: int, fmt: str) -> models.Asset | None:
    return (db.query(models.Asset)
            .filter(models.Asset.brand_id == brand_id,
                    models.Asset.fmt == fmt,
                    models.Asset.used == False)  # noqa: E712
            .order_by(models.Asset.created_at.asc())
            .first())


def plan_day(db: Session, brand: models.Brand, day: datetime | None = None) -> list[models.Post]:
    """يجدول منشورات اليوم لعلامة حسب الكمّيات والأوقات المحددة."""
    cfg = brand.schedule
    if not cfg:
        return []

    day = day or datetime.now()
    times = cfg.times or {}
    quotas = {"post": cfg.daily_posts, "story": cfg.daily_stories, "reel": cfg.daily_reels}
    scheduled: list[models.Post] = []

    for fmt, quota in quotas.items():
        slot_times = times.get(fmt, [])
        for i in range(quota):
            asset = _pick_asset(db, brand.id, fmt)
            if not asset:
                break  # نفد البنك لهذه الصيغة — سيُعاد ملؤه لاحقًا

            hhmm = slot_times[i] if i < len(slot_times) else f"{9 + i:02d}:00"
            hh, mm = (int(x) for x in hhmm.split(":"))
            when = day.replace(hour=hh, minute=mm, second=0, microsecond=0)

            post = models.Post(
                brand_id=brand.id, asset_id=asset.id, fmt=fmt,
                caption=f"{asset.caption}\n\n{asset.hashtags}".strip(),
                media_url=asset.media_url, platform="both",
                status="scheduled", scheduled_at=when,
            )
            asset.used = True
            db.add(post)
            # flush ضروري: بدونه لا يرى الاستعلام التالي أن هذه القطعة استُخدمت
            # (autoflush=False) فيلتقطها مرة أخرى وينتج محتوى مكرّر.
            db.flush()
            scheduled.append(post)

    db.commit()
    return scheduled


# ----------------------------------------------------------------------
#  3) النشر الفعلي للمنشورات المستحقّة
# ----------------------------------------------------------------------
def publish_due_posts(db: Session, now: datetime | None = None) -> int:
    """ينشر كل منشور حان وقته ولم يُنشر بعد."""
    now = now or datetime.now()
    due = (db.query(models.Post)
           .filter(models.Post.status == "scheduled",
                   models.Post.scheduled_at <= now)
           .all())

    published = 0
    for post in due:
        brand = post.brand
        try:
            ids = []
            if post.platform in ("fb", "both"):
                r = facebook.publish(brand.fb_page_id, brand.fb_page_token,
                                     post.caption, post.media_url, post.fmt)
                ids.append(f"fb:{r['id']}")
            if post.platform in ("ig", "both"):
                r = instagram.publish(brand.ig_account_id, brand.fb_page_token,
                                      post.caption, post.media_url, post.fmt)
                ids.append(f"ig:{r['id']}")

            post.status = "published"
            post.published_at = now
            post.external_post_id = ", ".join(ids)
            published += 1
        except Exception as exc:  # noqa: BLE001
            post.status = "failed"
            post.error = str(exc)[:500]

    db.commit()
    return published
