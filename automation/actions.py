from playwright.async_api import Page
from utils.logger import logger
from utils.selectors import UCircleSelectors
from utils.helpers import random_delay
import random

# Shuffle bag: đảm bảo dùng hết cả 5 hệ (Hỏa/Thổ/Kim/Thủy/Mộc) đúng 1 lần mỗi
# hệ trước khi xáo lại vòng mới, thay vì random độc lập từng video (có thể
# trùng liên tiếp nhiều lần).
_ELEMENT_CANONICAL = ["hoa", "tho", "kim", "thuy", "moc"]
_element_bag: list[str] = []


def _normalize_element_name(value: str | None) -> str:
    if value is None:
        return ""
    normalized = value.strip().lower().replace(" ", "")
    normalized = normalized.replace("thuỷ", "thuy").replace("thủy", "thuy").replace("thuy", "thuy")
    return normalized


def _ensure_complete_element_set(names: list[str]) -> list[str]:
    normalized = [_normalize_element_name(name) for name in names if _normalize_element_name(name)]
    complete = normalized.copy()
    for canonical in _ELEMENT_CANONICAL:
        if canonical not in complete:
            complete.append(canonical)
    return complete


def _draw_element(available_names: list[str], mode: str = "shuffle") -> str:
    global _element_bag
    normalized_available = _ensure_complete_element_set(available_names)

    # Nếu người dùng chỉ định cố định một hệ
    if mode in _ELEMENT_CANONICAL:
        return mode

    # Bỏ khỏi bag những phần tử không còn tồn tại trong picker hiện tại
    _element_bag = [e for e in _element_bag if e in normalized_available]
    if not _element_bag:
        _element_bag = normalized_available.copy()
        random.shuffle(_element_bag)
    return _element_bag.pop()

async def detect_react_state(react_button) -> bool:
    # data-wavee-react-enta-state luôn là "absent" bất kể đã react hay chưa —
    # KHÔNG dùng để xác định trạng thái. Giá trị lựa chọn thật nằm ở
    # data-wavee-react-mine (vd. "kim", "tho", "hoa", "thuy", "moc").
    try:
        mine = await react_button.get_attribute("data-wavee-react-mine")
        if mine and mine.strip():
            return True
    except Exception:
        pass
    return False

async def get_active_video_id(page: Page) -> str | None:
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

async def react_element_if_needed(page: Page, dry_run: bool = True, element_mode: str = "shuffle") -> tuple[bool, str]:
    """
    Thực hiện tương tác ngũ hành nếu video chưa react.
    Trả về (success: bool, status_message: str)
    """
    try:
        active_video_id = await get_active_video_id(page)
        logger.info(f"Active video section: {active_video_id}")

        # Tìm nút bấm mở bảng tương tác đúng trong section đang xem
        react_button = _react_button_locator(page, active_video_id)
        await react_button.wait_for(state="visible", timeout=5000)

        is_reacted = await detect_react_state(react_button)

        if is_reacted:
            logger.info("Reaction state: already-reacted. Skipping.")
            return False, "already_reacted"

        logger.info("Reaction state: not-reacted. Proceeding to react.")
        
        if dry_run:
            logger.info("[DRY-RUN] Will click React button and choose an element.")
            return True, "dry_run_success"
        else:
            await random_delay(0.5, 1.0)
            await react_button.click()
            logger.info("React button clicked. Waiting for picker to appear...")
            
            # Đợi bảng chọn hiện ra
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
                names = []
                for i in range(count):
                    raw_value = await elements.nth(i).get_attribute("data-wavee-element")
                    names.append(_normalize_element_name(raw_value))

                complete_names = _ensure_complete_element_set(names)
                element_name = _draw_element(complete_names, mode=element_mode)

                match_index = None
                for i in range(count):
                    raw_value = await elements.nth(i).get_attribute("data-wavee-element")
                    if _normalize_element_name(raw_value) == element_name:
                        match_index = i
                        break

                if match_index is None:
                    fallback_selector = f'button[data-wavee-element="{element_name}"]'
                    fallback_btn = page.locator(fallback_selector).first
                    if await fallback_btn.count() > 0:
                        await random_delay(0.5, 1.5)
                        await fallback_btn.click()
                        logger.info(f"Successfully reacted with: {element_name} via fallback selector")
                    else:
                        logger.warning(f"No fallback element found for {element_name}; picker count={count}, names={names}")
                else:
                    target_element_btn = elements.nth(match_index)
                    await random_delay(0.5, 1.5)
                    await target_element_btn.click()
                    logger.info(f"Successfully reacted with: {element_name}")
            else:
                logger.warning("Picker appeared but no elements found to click!")
                
            await random_delay(1, 2)
        
        return True, "reacted"
    except Exception as e:
        if await is_video_already_reacted(page):
            logger.info("Reaction state: already-reacted after retry check. Skipping.")
            return False, "already_reacted"

        logger.error(f"Failed to process React logic: {e}")
        try:
            import time
            import os
            os.makedirs("logs/screenshots", exist_ok=True)
            await page.screenshot(path=f"logs/screenshots/error_react_{int(time.time())}.png")
        except:
            pass
        return False, f"error: {e}"

async def scroll_to_next_video(page: Page) -> bool:
    try:
        logger.info("Scrolling to next video...")
        await page.keyboard.press("ArrowDown")
        await random_delay(1, 2)
        return True
    except Exception as e:
        logger.error(f"Failed to scroll to next video: {e}")
        return False
