"""تهيئة العلامتين الأوليين: بيج رايش (ديكور) و إنكيدو (مدارس)."""
from sqlalchemy.orm import Session

from . import models


def seed_brands(db: Session) -> None:
    """ينشئ العلامتين وإعداداتهما إن لم تكونا موجودتين."""
    if db.query(models.Brand).count() > 0:
        return

    page_reich = models.Brand(
        slug="page_reich", name="بيج رايش", field="ديكور",
        timezone="Asia/Baghdad",
        tone="أنيقة وراقية، تُبرز جمال التصميم والتفاصيل.",
        hashtags="#بيج_رايش #ديكور #تصميم_داخلي #أثاث",
    )
    page_reich.schedule = models.ScheduleConfig(
        daily_posts=3, daily_stories=2, daily_reels=1, refill_threshold=20,
        times={
            "post": ["10:00", "14:00", "20:00"],
            "story": ["12:00", "18:00"],
            "reel": ["21:00"],
        },
    )

    enkidu = models.Brand(
        slug="enkidu", name="إنكيدو", field="مدارس",
        timezone="Asia/Baghdad",
        tone="تربوية وموثوقة، تخاطب أولياء الأمور والطلاب بثقة.",
        hashtags="#إنكيدو #مدارس #تعليم #تسجيل",
    )
    enkidu.schedule = models.ScheduleConfig(
        daily_posts=3, daily_stories=2, daily_reels=1, refill_threshold=20,
        times={
            "post": ["09:00", "13:00", "19:00"],
            "story": ["11:00", "17:00"],
            "reel": ["20:00"],
        },
    )

    db.add_all([page_reich, enkidu])
    db.commit()
