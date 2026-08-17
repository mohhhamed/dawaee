"""تحليل الصور والوصف بالذكاء الاصطناعي (Vision).

في وضع mock يعيد تحليلًا نصيًا وهميًا حتى تُختبر المنظومة كاملة دون مفاتيح.
في وضع live: استبدل جسم analyze() باستدعاء مزوّد الرؤية (Claude/GPT vision).
"""
from ..config import settings


def analyze(description: str, image_url: str = "") -> str:
    """يحلّل مُدخل العلامة ويعيد وصفًا للهوية والمحتوى والنبرة."""
    if settings.is_mock or not settings.VISION_API_KEY:
        parts = []
        if description:
            parts.append(f"الموضوع المستخلص: {description.strip()[:120]}")
        if image_url:
            parts.append("تحليل الصورة: ألوان متناسقة، جودة جيدة، مناسبة للنشر.")
        parts.append("النبرة المقترحة: احترافية وودّية، مع دعوة واضحة للتفاعل.")
        return " | ".join(parts) or "لا يوجد محتوى كافٍ للتحليل."

    # --- وضع live: نقطة الربط الفعلية ---
    # مثال (Anthropic): أرسل الصورة + الوصف واطلب تحليلًا للهوية والنبرة.
    raise NotImplementedError("فعّل استدعاء مزوّد الرؤية هنا في وضع live.")
