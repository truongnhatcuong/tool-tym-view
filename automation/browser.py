from playwright.async_api import Playwright, BrowserContext
import config
from utils.logger import logger

async def launch_browser(p: Playwright, headless: bool = None, profile_dir: str = None) -> BrowserContext:
    user_data_dir = profile_dir if profile_dir is not None else config.PROFILE_DIR
    is_headless = headless if headless is not None else config.HEADLESS
    
    logger.info(f"Browser started (headless={is_headless}, profile='{user_data_dir}')")
    browser = await p.chromium.launch_persistent_context(
        user_data_dir=user_data_dir,
        headless=is_headless,
        args=["--disable-blink-features=AutomationControlled"]
    )
    return browser
