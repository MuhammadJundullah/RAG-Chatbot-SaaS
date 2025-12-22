from typing import Optional
from urllib.parse import urlparse

from app.core.config import settings


def add_app_base_url(path: Optional[str]) -> Optional[str]:
    if not path:
        return path

    parsed = urlparse(path)
    if parsed.scheme and parsed.netloc:
        return path

    base = settings.APP_BASE_URL.rstrip("/")
    if path.startswith("/"):
        return f"{base}{path}"
    return f"{base}/{path}"
