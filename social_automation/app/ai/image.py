"""توليد الصور بالذكاء الاصطناعي.

في وضع mock يعيد رابط صورة نائبة (placeholder) حتى تُختبر المنظومة.
في وضع live: استبدل جسم generate_image() باستدعاء مزوّد الصور
(gpt-image / DALL·E / Stability / Flux) ثم ارفع الناتج عبر storage.upload().
"""
from urllib.parse import quote

from ..config import settings


def generate_image(prompt: str, fmt: str = "post") -> str:
    """يعيد رابط صورة (URL) للصيغة المطلوبة."""
    # أبعاد مناسبة لكل صيغة
    size = {"post": "1080x1080", "story": "1080x1920", "reel": "1080x1920"}.get(fmt, "1080x1080")

    if settings.is_mock or not settings.IMAGE_API_KEY:
        w, h = size.split("x")
        label = quote((prompt or "content")[:40])
        # صورة نائبة تُظهر النص والأبعاد — لا تتطلب أي مفتاح
        return f"https://placehold.co/{w}x{h}/0e9c8a/ffffff/png?text={label}"

    # --- وضع live: نقطة الربط الفعلية ---
    raise NotImplementedError("فعّل استدعاء مزوّد الصور هنا في وضع live.")
