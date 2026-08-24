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
    user_data_dir = profile_dir if profile_dir is not None else "./browser-profile"
    is_headless = headless if headless is not None else False

    proxy_info = f", proxy={proxy.get('server', '')}" if proxy else ""
    logger.info(f"Browser started (headless={is_headless}, profile='{user_data_dir}'{proxy_info})")

    launch_kwargs = {
        "user_data_dir": user_data_dir,
        "headless": is_headless,
        "args": ["--disable-blink-features=AutomationControlled"],
    }

    if proxy and proxy.get("server"):
        launch_kwargs["proxy"] = proxy

    browser = await p.chromium.launch_persistent_context(**launch_kwargs)
    return browser
