"""النشر على فيسبوك عبر Graph API.

في وضع mock يسجّل النشر ويعيد معرّفًا وهميًا دون اتصال فعلي.
في وضع live: ينفّذ استدعاء Graph API الحقيقي.
"""
import time

import httpx

from ..config import settings

GRAPH = "https://graph.facebook.com/v21.0"


def publish(page_id: str, page_token: str, caption: str,
            media_url: str, fmt: str = "post") -> dict:
    """ينشر على صفحة فيسبوك ويعيد {'id':..., 'ok':bool}."""
    if settings.is_mock or not (page_id and page_token):
        return {"ok": True, "id": f"fb_mock_{int(time.time())}", "mock": True}

    # --- وضع live ---
    if media_url:
        url = f"{GRAPH}/{page_id}/photos"
        data = {"url": media_url, "caption": caption, "access_token": page_token}
    else:
        url = f"{GRAPH}/{page_id}/feed"
        data = {"message": caption, "access_token": page_token}

    resp = httpx.post(url, data=data, timeout=60)
    resp.raise_for_status()
    return {"ok": True, "id": resp.json().get("id", ""), "mock": False}
