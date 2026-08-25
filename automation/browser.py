from playwright.async_api import Playwright, BrowserContext

from utils.logger import logger
from typing import Optional, Dict

async def launch_browser(
    p: Playwright,
    headless: bool = None,
    profile_dir: str = None,
    proxy: Optional[Dict[str, str]] = None
) -> BrowserContext:
    """
    Khởi động trình duyệt Chromium với persistent context.

    Args:
        p:           Playwright instance.
        headless:    Chạy ẩn hay không; None = lấy từ config.
        profile_dir: Thư mục lưu session; None = lấy từ config.
        proxy:       Dict proxy dạng Playwright ({"server": ..., "username": ..., "password": ...}).
                     None = không dùng proxy.
    """
    import os
    is_headless = headless if headless is not None else False

    proxy_info = f", proxy={proxy.get('server', '')}" if proxy else ""
    logger.info(f"Browser started (headless={is_headless}, session='session.json'{proxy_info})")

    browser_instance = await p.chromium.launch(
        headless=is_headless,
        args=["--disable-blink-features=AutomationControlled"]
    )

    context_kwargs = {}
    if proxy and proxy.get("server"):
        context_kwargs["proxy"] = proxy

    # Nạp session.json nếu đã có và hợp lệ (> 10 bytes)
    if os.path.exists("session.json") and os.path.getsize("session.json") > 10:
        try:
            context_kwargs["storage_state"] = "session.json"
        except Exception as e:
            logger.warning(f"Không thể áp dụng storage_state từ session.json: {e}")

    context = await browser_instance.new_context(**context_kwargs)
    
    return context

