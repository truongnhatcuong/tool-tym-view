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
        "article[data-post-id]",
        "button[data-nguhanh-main='true']",
        "text=Bảng tin"
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
    """Best-effort login detection that accepts post-login app markers and localStorage."""
    try:
        url = page.url.lower()
        if "ucircle.net" not in url:
            return False

        # 1. Kiểm tra token trong localStorage (chính xác nhất)
        try:
            auth_val = await page.evaluate("() => localStorage.getItem('uc-core-auth')")
            if auth_val and ("access_token" in auth_val or "expires_at" in auth_val):
                return True
        except Exception:
            pass

        # 2. Nếu đang ở trang login thì chưa đăng nhập
        if await _looks_like_login_page(page):
            return False

        # 3. Kiểm tra các phần tử UI sau đăng nhập
        selectors = [
            "text=Logout",
            "text=Log out",
            "text=Sign out",
            "text=Profile",
            "text=Account",
            "button:has-text(Logout)",
            "button:has-text(Log out)",
            "button:has-text(Sign out)",
            "text=Đăng xuất",
            "text=Hồ sơ",
            "text=Bảng tin",
            "[data-tool='wavee']",
            "button[data-tool='wavee']",
            "section[data-wavee-video-id]",
            "button[data-wavee-grid-cell='true']",
            "article[data-post-id]",
            "button[data-nguhanh-main='true']"
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
    logger.info("Kiểm tra trạng thái đăng nhập UCircle...")
    try:
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=10000)
        except Exception:
            pass

        if await _is_logged_in(page):
            logger.info("Đã phát hiện trạng thái đăng nhập. Tự động cập nhật session.json...")
            try:
                await page.context.storage_state(path="session.json")
            except Exception:
                pass
            return

        print("\n" + "=" * 60)
        print("Vui lòng đăng nhập UCircle trên trình duyệt...")
        print("Hệ thống sẽ tự động phát hiện và lưu session khi bạn đăng nhập.")
        print("=" * 60 + "\n")

        logger.info("Đang chờ người dùng đăng nhập UCircle...")
        deadline = time.monotonic() + wait_timeout_seconds
        while time.monotonic() < deadline:
            if await _is_logged_in(page) or await _wait_for_logged_in_ui(page, timeout_seconds=5):
                logger.info("Đăng nhập UCircle thành công! Đang lưu session.json...")
                try:
                    await page.context.storage_state(path="session.json")
                    logger.info("Đã lưu session.json thành công để tái sử dụng đa luồng.")
                except Exception as e:
                    logger.warning(f"Không thể lưu session.json: {e}")
                return
            await asyncio.sleep(2)

        logger.warning("Hết thời gian chờ đăng nhập. Tiếp tục chạy...")
    except Exception as e:
        logger.error(f"Lỗi kiểm tra đăng nhập: {e}")

