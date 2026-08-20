from playwright.async_api import Page
from utils.logger import logger
from utils.selectors import UCircleSelectors
from utils.helpers import random_delay
import random

async def watch_video(page: Page, min_seconds: int, max_seconds: int):
    watch_time = random.uniform(min_seconds, max_seconds)
    logger.info(f"Watching video for {watch_time:.1f} seconds...")
    await page.wait_for_timeout(watch_time * 1000)
    logger.info(f"Video watched: {watch_time:.1f}s")
