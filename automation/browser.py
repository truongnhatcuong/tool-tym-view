import os
import json
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
    Khởi động trình duyệt Chromium.

    TỰ ĐỘNG nạp session.json (nếu có) để tất cả luồng (1 luồng hay 10 luồng)
    đều tự động dùng chung session đã đăng nhập, không bắt login lại.
    """
    is_headless = headless if headless is not None else False
    proxy_info = f", proxy={proxy.get('server', '')}" if proxy else ""

    context_kwargs: dict = {
        "headless": is_headless,
        "args": ["--disable-blink-features=AutomationControlled"],
    }
    if proxy and proxy.get("server"):
        context_kwargs["proxy"] = proxy

    has_session = os.path.exists("session.json")

    # ── Trường hợp 1: Dùng persistent context với profile_dir ───────────────
    if profile_dir:
        abs_dir = os.path.abspath(profile_dir)
        os.makedirs(abs_dir, exist_ok=True)
        logger.info(
            f"Browser started (persistent: '{abs_dir}', headless={is_headless}, session.json={has_session}{proxy_info})"
        )
        context = await p.chromium.launch_persistent_context(
            abs_dir,
            **context_kwargs,
        )

        # Nạp session.json (cookies + localStorage uc-core-auth) vào persistent context nếu file tồn tại
        if has_session:
            try:
                with open("session.json", "r", encoding="utf-8") as f:
                    state = json.load(f)
                cookies = state.get("cookies", [])
                origins = state.get("origins", [])

                if cookies:
                    await context.add_cookies(cookies)
                    logger.info(f"-> Đã nạp {len(cookies)} cookies từ session.json.")

                if origins:
                    for origin_entry in origins:
                        ls_items = origin_entry.get("localStorage", [])
                        for item in ls_items:
                            k = json.dumps(item["name"])
                            v = json.dumps(item["value"])
                            await context.add_init_script(
                                f"try {{ localStorage.setItem({k}, {v}); }} catch(e) {{}}"
                            )
                    logger.info(f"-> Đã nạp localStorage (uc-core-auth) từ session.json vào persistent profile.")
            except Exception as e:
                logger.warning(f"Không nạp được session.json: {e}")

        return context

    # ── Trường hợp 2: Non-persistent context ────────────────────────────────
    logger.info(
        f"Browser started (standard, headless={is_headless}, session.json={has_session}{proxy_info})"
    )
    browser_instance = await p.chromium.launch(
        headless=is_headless,
        args=["--disable-blink-features=AutomationControlled"],
        **({"proxy": proxy} if proxy and proxy.get("server") else {}),
    )

    new_ctx_kwargs: dict = {}
    if proxy and proxy.get("server"):
        new_ctx_kwargs["proxy"] = proxy
    if has_session:
        new_ctx_kwargs["storage_state"] = "session.json"

    context = await browser_instance.new_context(**new_ctx_kwargs)
    return context



