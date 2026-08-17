"""رفع الوسائط إلى تخزين عام (مطلوب لإنستغرام في وضع live).

في وضع mock يعيد الرابط كما هو (روابط placeholder عامة أصلًا).
في وضع live: نفّذ الرفع إلى S3 أو أي تخزين يعطي رابطًا عامًا.
"""
from .config import settings


def upload(local_path_or_url: str, key: str = "") -> str:
    """يعيد رابطًا عامًا للوسيط."""
    if settings.is_mock or not settings.S3_BUCKET:
        return local_path_or_url

    # --- وضع live: ارفع إلى S3 وأعد الرابط العام ---
    raise NotImplementedError("فعّل الرفع إلى التخزين السحابي هنا في وضع live.")
