from playwright.async_api import Page
from utils.logger import logger
from utils.selectors import UCircleSelectors
from utils.helpers import random_delay

async def switch_to_wavee_tab(page: Page) -> bool:
    logger.info("Switching to Wavee tab...")
    wavee_btn = page.locator(UCircleSelectors.WAVEE_TAB_BTN)
    try:
        await wavee_btn.wait_for(state="visible", timeout=10000)
        await wavee_btn.click()
        logger.info("Clicked on Wavee tab successfully.")
        await random_delay()
        return True
    except Exception as e:
        logger.error(f"Wavee tab not found or failed to click: {e}")
        return False

async def click_specific_video(page: Page, video_id: str) -> bool:
    logger.info(f"Looking for video with ID: {video_id}")

    # URL may already contain v=<video_id>, which opens the grid-viewer dialog
    # on load. When that happens the dialog overlay sits on top of the grid
    # and intercepts pointer events, so clicking the underlying grid cell
    # times out. Detect that case first and treat it as already-open.
    dialog_section = page.locator(
        f'div[role="dialog"][data-wavee-grid-viewer="true"] section[data-wavee-video-id="{video_id}"]'
    )
    try:
        if await dialog_section.count() > 0 and await dialog_section.first.is_visible():
            logger.info(f"Video {video_id} is already open in the viewer dialog. Skipping click.")
            return True
    except Exception:
        pass

    selector = UCircleSelectors.get_specific_video_selector(video_id)
    video_btn = page.locator(selector)
    try:
        await video_btn.wait_for(state="visible", timeout=15000)
        await video_btn.scroll_into_view_if_needed()
        try:
            await video_btn.click(timeout=5000)
        except Exception:
            # A viewer dialog may be covering the grid cell; force the click
            # through the overlay instead of failing the whole session.
            logger.warning(f"Normal click on {video_id} intercepted, retrying with force click.")
            await video_btn.click(force=True)
        logger.info(f"Opened video {video_id} successfully.")
        return True
    except Exception as e:
        logger.error(f"Failed to find or click video {video_id}: {e}")
        return False
