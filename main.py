import asyncio
import argparse
import config
from utils.logger import logger
from playwright.async_api import async_playwright
from automation.browser import launch_browser
from automation.login import ensure_login
from automation.feed import switch_to_wavee_tab, click_specific_video
from automation.video import watch_video
from automation.actions import react_element_if_needed, scroll_to_next_video, is_video_already_reacted
from utils.helpers import random_delay

async def main():
    parser = argparse.ArgumentParser(description="UCircle Video QA Automation")
    parser.add_argument("--dry-run", action="store_true", help="Run without clicking Like")
    parser.add_argument("--videos", type=int, default=config.MAX_VIDEOS_PER_SESSION, help="Max videos per session")
    parser.add_argument("--watch-min", type=int, default=config.WATCH_MIN_SECONDS, help="Min watch time")
    parser.add_argument("--watch-max", type=int, default=config.WATCH_MAX_SECONDS, help="Max watch time")
    args = parser.parse_args()

    # Override config with CLI args
    is_dry_run = args.dry_run or config.DRY_RUN
    max_videos = args.videos
    watch_min = args.watch_min
    watch_max = args.watch_max
    
    target_video_id = "d4f2b67c-317c-46fd-bbb7-c1bab3ed4740"

    async with async_playwright() as p:
        browser = await launch_browser(p)
        try:
            page = browser.pages[0] if browser.pages else await browser.new_page()
            
            logger.info(f"Opening UCircle URL: {config.UCIRCLE_URL}")
            await page.goto(config.UCIRCLE_URL)
            
            await ensure_login(page)
            
            success_tab = await switch_to_wavee_tab(page)
            if not success_tab:
                logger.error("Could not switch to Wavee tab. Exiting.")
                return
                
            success_video = await click_specific_video(page, target_video_id)
            if success_video:
                for index in range(max_videos):
                    logger.info(f"--- Processing video {index + 1}/{max_videos} ---")

                    try:
                        if await is_video_already_reacted(page):
                            logger.info("Video already reacted (Hỏa/Thổ/Kim/Thủy/Mộc chosen). Skipping watch/react.")
                        else:
                            await watch_video(page, watch_min, watch_max)
                            await react_element_if_needed(page, dry_run=is_dry_run)
                    except Exception as e:
                        logger.error(f"Error processing video {index + 1}: {e}. Moving to next video.")

                    if index < max_videos - 1:
                        await scroll_to_next_video(page)
                        await random_delay(2, 4)
                
            logger.info("Session completed. Stopping automation.")
        except Exception as e:
            logger.error(f"Critical error in main loop: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    import os
    os.makedirs("logs/screenshots", exist_ok=True)
    asyncio.run(main())
