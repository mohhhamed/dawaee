"""النشر على إنستغرام عبر Graph API (خطوتان: إنشاء حاوية ثم نشر).

في وضع mock يعيد معرّفًا وهميًا. في وضع live ينفّذ الخطوتين الحقيقيتين.
ملاحظة: إنستغرام يتطلب أن تكون media_url رابطًا عامًا (يُرفع أولًا عبر storage).
"""
import time

import httpx

from ..config import settings

GRAPH = "https://graph.facebook.com/v21.0"


def publish(ig_user_id: str, page_token: str, caption: str,
            media_url: str, fmt: str = "post") -> dict:
    """ينشر على إنستغرام ويعيد {'id':..., 'ok':bool}."""
    if settings.is_mock or not (ig_user_id and page_token and media_url):
        return {"ok": True, "id": f"ig_mock_{int(time.time())}", "mock": True}

    # --- وضع live ---
    # 1) إنشاء حاوية الوسائط
    container_params = {"caption": caption, "access_token": page_token}
    if fmt in ("reel", "story"):
        container_params["media_type"] = "REELS" if fmt == "reel" else "STORIES"
        container_params["video_url"] = media_url
    else:
        container_params["image_url"] = media_url

    c = httpx.post(f"{GRAPH}/{ig_user_id}/media", data=container_params, timeout=120)
    c.raise_for_status()
    creation_id = c.json()["id"]

    # 2) نشر الحاوية
    p = httpx.post(f"{GRAPH}/{ig_user_id}/media_publish",
                   data={"creation_id": creation_id, "access_token": page_token}, timeout=120)
    p.raise_for_status()
    return {"ok": True, "id": p.json().get("id", ""), "mock": False}
