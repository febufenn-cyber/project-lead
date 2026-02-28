import random

from app.config import get_settings


class ProxyManager:
    def __init__(self):
        settings = get_settings()
        self.proxies = [p.strip() for p in settings.proxy_list.split(",") if p.strip()] if settings.proxy_list else []

    def get_proxy(self) -> str | None:
        if not self.proxies:
            return None
        return random.choice(self.proxies)
