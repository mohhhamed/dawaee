"""توليد نصوص المنشورات (كابشن + هاشتاغ) بالذكاء الاصطناعي.

في وضع mock يولّد نصًا عربيًا معقولًا محليًا دون مفاتيح.
في وضع live: استبدل جسم generate_caption() باستدعاء Claude/GPT.
"""
import random

from ..config import settings

# قوالب تجريبية بسيطة حسب الصيغة
_TEMPLATES = {
    "post": [
        "اكتشف {topic} من {brand} ✨ جودة تليق بذوقك.",
        "{topic} — لمسة تصنع الفرق مع {brand}. تواصل معنا اليوم!",
        "نقدّم لك {topic} بأناقة من {brand}. لا تفوّت العرض 👌",
    ],
    "story": [
        "🔥 جديد {brand}: {topic}",
        "شاهد الآن: {topic} من {brand}",
    ],
    "reel": [
        "🎬 جولة سريعة في {topic} مع {brand} — شاهد حتى النهاية!",
    ],
}


def generate_caption(brand_name: str, analysis: str, fmt: str = "post",
                     tone: str = "", hashtags: str = "") -> dict:
    """يعيد dict فيه caption و hashtags."""
    if settings.is_mock or not (settings.ANTHROPIC_API_KEY or settings.OPENAI_API_KEY):
        topic = (analysis.split("|")[0].replace("الموضوع المستخلص:", "").strip()
                 or "منتجاتنا")
        template = random.choice(_TEMPLATES.get(fmt, _TEMPLATES["post"]))
        caption = template.format(topic=topic[:60], brand=brand_name)
        tags = hashtags or f"#{brand_name.replace(' ', '_')} #عرض #جودة"
        return {"caption": caption, "hashtags": tags}

    # --- وضع live: نقطة الربط الفعلية ---
    raise NotImplementedError("فعّل استدعاء مزوّد النص هنا في وضع live.")
