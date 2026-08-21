import asyncio
import sys
import time
from playwright.async_api import Page
from utils.logger import logger


async def _looks_like_login_page(page: Page) -> bool:
    """Detect if the current page is still an auth/login screen."""
    try:
        url = page.url.lower()
        if "/login" in url or "/signin" in url or "/auth" in url:
            return True

        selectors = [
            "input[type='email']",
            "input[type='password']",
            "input[name*='email']",
            "input[name*='password']",
            "text=Login",
            "text=Sign in",
            "text=Đăng nhập",
            "button:has-text(Sign in)",
            "button:has-text(Login)",
            "button:has-text(Đăng nhập)",
        ]
        for selector in selectors:
            try:
                if await page.locator(selector).count() > 0:
                    return True
            except Exception:
                continue
        return False
    except Exception:
        return False


async def _wait_for_logged_in_ui(page: Page, timeout_seconds: int = 90) -> bool:
    """Wait until the post-login UCircle app UI appears."""
    selectors = [
        "button[data-tool='wavee']",
        "section[data-wavee-video-id]",
        "button[data-wavee-grid-cell='true']",
        "button[data-wavee-react='true']",
    ]
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            if await _looks_like_login_page(page):
                await asyncio.sleep(2)
                continue

            for selector in selectors:
                try:
                    locator = page.locator(selector)
                    if await locator.count() > 0:
                        return True
                except Exception:
                    continue

            await asyncio.sleep(2)
        except Exception:
            await asyncio.sleep(2)

    return False


async def _is_logged_in(page: Page) -> bool:
    """Best-effort login detection that accepts post-login app markers."""
    try:
        if await _looks_like_login_page(page):
            return False

        url = page.url.lower()
        if "ucircle.net" not in url:
            return False

        selectors = [
            "text=Logout",
            "text=Log out",
            "text=Sign out",
            "text=Profile",
            "text=Account",
            "button:has-text(Logout)",
            "button:has-text(Log out)",
            "button:has-text(Sign out)",
            "[data-tool='wavee']",
            "button[data-tool='wavee']",
            "section[data-wavee-video-id]",
            "button[data-wavee-grid-cell='true']",
        ]
        for selector in selectors:
            try:
                locator = page.locator(selector)
                if await locator.count() > 0:
                    return True
            except Exception:
                continue

        return False
    except Exception:
        return False


async def ensure_login(page: Page, wait_timeout_seconds: int = 900):
    logger.info("Checking login state...")
    try:
        await page.wait_for_load_state("networkidle", timeout=20000)

        if await _is_logged_in(page):
            logger.info("Login state already detected. Continuing automation.")
            return

        print("\n" + "=" * 60)
        print("Please login manually in the browser.")
        print("Then either press ENTER in this terminal or wait for the script to continue automatically.")
        print("=" * 60 + "\n")

        if sys.stdin is not None and hasattr(sys.stdin, "isatty") and sys.stdin.isatty():
            try:
                print("If you already logged in, press ENTER now to continue anyway.")
                await asyncio.to_thread(input, "")
                logger.info("User pressed Enter; forcing continuation after manual login override.")
                return
            except EOFError:
                logger.warning("stdin closed unexpectedly; continuing with browser-login wait loop.")

        logger.info("Waiting for the authenticated UCircle app UI to appear after login...")
        deadline = time.monotonic() + wait_timeout_seconds
        while time.monotonic() < deadline:
            if await _wait_for_logged_in_ui(page, timeout_seconds=15):
                logger.info("Login state became active. Continuing automation...")
                return
            if await _is_logged_in(page):
                logger.info("Login state detected after waiting. Continuing automation...")
                return
            await asyncio.sleep(5)

        logger.warning("Login wait timed out. Continuing anyway; if user is still not logged in, next steps may fail.")
    except Exception as e:
        logger.error(f"Error during login check: {e}")
