from playwright.async_api import Page
from utils.logger import logger
from utils.selectors import UCircleSelectors
from utils.helpers import random_delay
import random

async def detect_react_state(react_button) -> bool:
    # data-wavee-react-enta-state luôn là "absent" bất kể đã react hay chưa —
    # KHÔNG dùng để xác định trạng thái. Giá trị lựa chọn thật nằm ở
    # data-wavee-react-mine (vd. "kim", "tho", "hoa", "thuy", "moc").
    mine = await react_button.get_attribute("data-wavee-react-mine")
    if mine and mine.strip():
        return True
    return False

async def get_active_video_id(page: Page) -> str | None:
    # Tất cả section video được mount sẵn cùng lúc trong dialog cuộn dọc
    # (không bị huỷ/tái tạo theo video), mỗi section cao bằng viewport.
    # Vì vậy không thể dùng ":visible" để xác định video đang xem — section
    # đã cuộn qua vẫn có bounding box hợp lệ nên Playwright vẫn tính là visible.
    # Phải tự tìm section có rect.top gần 0 nhất (đang nằm trong khung nhìn).
    try:
        return await page.evaluate(
            """
            () => {
                const sections = document.querySelectorAll('section[data-wavee-video-id]');
                let best = null, bestDist = Infinity;
                for (const s of sections) {
                    const r = s.getBoundingClientRect();
                    if (r.bottom > 0 && r.top < window.innerHeight) {
                        const dist = Math.abs(r.top);
                        if (dist < bestDist) {
                            bestDist = dist;
                            best = s.getAttribute('data-wavee-video-id');
                        }
                    }
                }
                return best;
            }
            """
        )
    except Exception as e:
        logger.warning(f"Could not determine active video section: {e}")
        return None

def _react_button_locator(page: Page, active_video_id: str | None):
    if active_video_id:
        return page.locator(
            f'section[data-wavee-video-id="{active_video_id}"] {UCircleSelectors.REACT_BTN}'
        ).first
    return page.locator(UCircleSelectors.REACT_BTN).first

async def is_video_already_reacted(page: Page) -> bool:
    try:
        active_video_id = await get_active_video_id(page)
        react_button = _react_button_locator(page, active_video_id)
        await react_button.wait_for(state="visible", timeout=5000)
        return await detect_react_state(react_button)
    except Exception as e:
        logger.warning(f"Could not determine react state: {e}")
        return False

async def react_element_if_needed(page: Page, dry_run: bool = True) -> bool:
    try:
        active_video_id = await get_active_video_id(page)
        logger.info(f"Active video section: {active_video_id}")

        # Tìm nút bấm mở bảng tương tác đúng trong section đang xem
        react_button = _react_button_locator(page, active_video_id)
        await react_button.wait_for(state="visible", timeout=5000)

        is_reacted = await detect_react_state(react_button)

        if is_reacted:
            logger.info("Reaction state: already-reacted. Skipping.")
            return False

        logger.info("Reaction state: not-reacted. Proceeding to react.")
        
        if dry_run:
            logger.info("[DRY-RUN] Will click React button and choose a random element here.")
        else:
            await random_delay(0.5, 1.0)
            await react_button.click()
            logger.info("React button clicked. Waiting for picker to appear...")
            
            # Đợi bảng chọn hiện ra (animation mở picker có thể mất hơn 3s)
            picker_id = await react_button.get_attribute("aria-controls")
            if picker_id:
                picker = page.locator(f'#{picker_id}')
            else:
                picker = page.locator(
                    f'section[data-wavee-video-id="{active_video_id}"] {UCircleSelectors.REACT_PICKER}'
                ).first if active_video_id else page.locator(UCircleSelectors.REACT_PICKER).first
            await picker.wait_for(state="visible", timeout=8000)

            # Lấy danh sách các nút ngũ hành bên trong đúng picker vừa mở
            elements = picker.locator(UCircleSelectors.REACT_ELEMENTS)
            count = await elements.count()
            
            if count > 0:
                # Chọn random 1 phần tử
                random_index = random.randint(0, count - 1)
                random_element_btn = elements.nth(random_index)
                element_name = await random_element_btn.get_attribute("data-wavee-element")
                
                await random_delay(0.5, 1.5)
                await random_element_btn.click()
                logger.info(f"Successfully reacted with: {element_name}")
            else:
                logger.warning("Picker appeared but no elements found to click!")
                
            await random_delay(1, 2)
        
        return True
    except Exception as e:
        # Nếu picker không kịp hiện nhưng thực ra video đã được react rồi
        # (vd. do click trước đó hoặc do UI tự đổi trạng thái), coi như xong,
        # không cần log lỗi và chụp màn hình.
        if await is_video_already_reacted(page):
            logger.info("Reaction state: already-reacted after retry check. Skipping.")
            return False

        logger.error(f"Failed to process React logic: {e}")
        try:
            import time
            await page.screenshot(path=f"logs/screenshots/error_react_{int(time.time())}.png")
        except:
            pass
        return False

async def scroll_to_next_video(page: Page) -> bool:
    try:
        logger.info("Scrolling to next video...")
        # Ở các trình xem video dạng feed, nhấn ArrowDown hoặc cuộn chuột sẽ chuyển sang video tiếp theo
        await page.keyboard.press("ArrowDown")
        await random_delay(1, 2)
        return True
    except Exception as e:
        logger.error(f"Failed to scroll to next video: {e}")
        return False
