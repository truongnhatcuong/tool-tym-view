from playwright.async_api import Page
from utils.logger import logger
from utils.selectors import UCircleSelectors
from utils.helpers import random_delay

async def switch_to_wavee_tab(page: Page) -> bool:
    logger.info("Switching to Wavee tab...")
    wavee_btn = page.locator(UCircleSelectors.WAVEE_TAB_BTN)
    try:
        await wavee_btn.wait_for(state="visible", timeout=15000)
        await wavee_btn.click()
        logger.info("Clicked on Wavee tab successfully.")
        await page.wait_for_load_state("networkidle", timeout=20000)
        await page.wait_for_timeout(2500)
        return True
    except Exception as e:
        logger.error(f"Wavee tab not found or failed to click: {e}")
        return False

async def click_specific_video(page: Page, video_id: str) -> bool:
    logger.info(f"Looking for video with ID: {video_id}")

    # URL may already contain v=<video_id>, which opens the grid-viewer dialog
    # on load. When that happens the dialog overlay sits on top of the grid
    # and intercepts pointer events. Detect that case first and treat it as already-open.
    dialog_section = page.locator(
        f'div[role="dialog"][data-wavee-grid-viewer="true"] section[data-wavee-video-id="{video_id}"]'
    )
    try:
        if await dialog_section.count() > 0 and await dialog_section.first.is_visible():
            logger.info(f"Video {video_id} is already open in the viewer dialog. Skipping click.")
            return True
    except Exception:
        pass

    selector_candidates = [
        f'button[data-wavee-grid-cell="true"][data-wavee-video-id="{video_id}"]',
        f'section[data-wavee-video-id="{video_id}"]',
        f'div[data-wavee-video-id="{video_id}"]',
        f'[data-wavee-video-id="{video_id}"]',
        f'button[data-wavee-video-id="{video_id}"]',
    ]

    for selector in selector_candidates:
        try:
            video_btn = page.locator(selector)
            if await video_btn.count() == 0:
                continue
            target = video_btn.first
            await target.wait_for(state="visible", timeout=10000)
            await target.scroll_into_view_if_needed()
            try:
                await target.click(timeout=5000)
            except Exception:
                logger.warning(f"Normal click on {video_id} intercepted, retrying with force click.")
                await target.click(force=True)
            logger.info(f"Opened video {video_id} successfully.")
            return True
        except Exception:
            continue

    # Fallback: the feed may not expose the exact video id in the current DOM,
    # but still includes a grid cell or a visible Wavee video item. Click the first valid item.
    fallback_selectors = [
        'button[data-wavee-grid-cell="true"]',
        '[data-wavee-grid-cell="true"]',
        'section[data-wavee-video-id]',
        'div[data-wavee-video-id]',
        '[data-wavee-video-id]',
        'video',
    ]

    for selector in fallback_selectors:
        try:
            video_btn = page.locator(selector)
            count = await video_btn.count()
            if count == 0:
                continue
            for index in range(min(count, 5)):
                target = video_btn.nth(index)
                if not await target.is_visible():
                    continue
                await target.scroll_into_view_if_needed()
                try:
                    await target.click(timeout=4000)
                    logger.warning(f"Opened first available Wavee video instead of exact ID {video_id}.")
                    return True
                except Exception:
                    try:
                        await target.click(force=True)
                        logger.warning(f"Opened first available Wavee video via force click instead of exact ID {video_id}.")
                        return True
                    except Exception:
                        continue
        except Exception:
            continue

    logger.error(f"Failed to find or click video {video_id}: timeout waiting for any matching selector")
    return False
