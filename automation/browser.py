from playwright.async_api import Playwright, BrowserContext
import config
from utils.logger import logger

async def launch_browser(p: Playwright) -> BrowserContext:
    logger.info("Browser started")
    browser = await p.chromium.launch_persistent_context(
        user_data_dir=config.PROFILE_DIR,
        headless=config.HEADLESS,
        args=["--disable-blink-features=AutomationControlled"]
    )
    return browser
