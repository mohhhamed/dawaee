"""إعدادات وقت التشغيل: تقرأ من قاعدة البيانات أولًا ثم من .env كاحتياط.

هكذا يستطيع المستخدم تعديل المفاتيح ووضع التشغيل من المتصفح دون لمس أي ملف.
"""
from .config import settings as env_settings
from .database import SessionLocal
from . import models

# المفاتيح المسموح تخزينها/تعديلها من الواجهة
KEYS = [
    "APP_MODE",
    "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "IMAGE_API_KEY", "VISION_API_KEY",
    "S3_BUCKET", "S3_ACCESS_KEY", "S3_SECRET_KEY", "S3_REGION",
]

_SECRET_HINT = ("KEY", "SECRET", "TOKEN")


def get(key: str, default: str = "") -> str:
    """قيمة الإعداد: قاعدة البيانات أولًا، فإن لم توجد فمن .env."""
    db = SessionLocal()
    try:
        row = db.get(models.AppSetting, key)
        if row and row.value not in (None, ""):
            return row.value
    finally:
        db.close()
    return getattr(env_settings, key, default) or default


def set_many(values: dict) -> None:
    """حفظ مجموعة إعدادات في قاعدة البيانات."""
    db = SessionLocal()
    try:
        for k, v in values.items():
            if k not in KEYS:
                continue
            row = db.get(models.AppSetting, k)
            if row:
                row.value = v or ""
            else:
                db.add(models.AppSetting(key=k, value=v or ""))
        db.commit()
    finally:
        db.close()


def is_mock() -> bool:
    """النظام تجريبي ما لم يُضبط APP_MODE=live صراحةً."""
    return get("APP_MODE", "mock").lower() != "live"


def masked_status() -> dict:
    """حالة المفاتيح للعرض في الواجهة (دون كشف القيم السرية)."""
    out = {}
    for k in KEYS:
        val = get(k, "")
        if k == "APP_MODE":
            out[k] = val or "mock"
        elif any(h in k for h in _SECRET_HINT):
            out[k] = "configured" if val else ""   # لا نكشف القيمة
        else:
            out[k] = val
    return out
