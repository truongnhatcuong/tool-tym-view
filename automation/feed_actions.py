from playwright.async_api import Page
from utils.logger import logger
from utils.helpers import random_delay
from automation.actions import react_element_if_needed

async def switch_to_feed_tab(page: Page) -> bool:
    logger.info("Chuyển sang tab Bảng tin...")
    try:
        # Thử tìm tab Bảng tin bằng text
        tab_locators = [
            page.locator('button[data-tool="feed"]').first,
            page.locator('[data-tool="feed"]').first,
            page.locator('button:has-text("Bảng tin")').first,
            page.get_by_text("Bảng tin", exact=True).first,
            page.locator('a:has-text("Bảng tin")').first,
        ]
        
        for loc in tab_locators:
            if await loc.count() > 0:
                await loc.click(timeout=3000)
                logger.info("Đã bấm sang tab Bảng tin.")
                await page.wait_for_timeout(2000)
                return True
                
        logger.warning("Không tìm thấy nút tab Bảng tin, có thể đang mặc định ở tab Bảng tin.")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi chuyển sang tab Bảng tin: {e}")
        return False

async def scroll_to_top_feed(page: Page):
    """Cuộn lên đầu trang bảng tin để bắt đầu từ bài mới nhất."""
    try:
        result = await page.evaluate("""
            () => {
                // 1. Cuộn phần tử đầu trang (banner cover hoặc bài viết đầu tiên) vào tầm nhìn
                const topEl = document.querySelector('[data-circle-cover-band="true"]')
                           || document.querySelector('article[data-post="true"]')
                           || document.querySelector('article')
                           || document.querySelector('main');
                if (topEl) {
                    topEl.scrollIntoView({ behavior: 'instant', block: 'start' });
                }

                // 2. Reset window và html/body
                window.scrollTo({ top: 0, behavior: 'instant' });
                document.documentElement.scrollTop = 0;
                document.body.scrollTop = 0;

                // 3. Reset TẤT CẢ các container có scrollTop > 0
                let count = 0;
                const all = document.querySelectorAll('*');
                for (const el of all) {
                    try {
                        if (el.scrollTop > 0) {
                            el.scrollTop = 0;
                            count++;
                        }
                    } catch(e) {}
                }
                return 'Top element: ' + (topEl ? topEl.tagName : 'none') + ' | Đã reset ' + count + ' containers';
            }
        """)
        await page.wait_for_timeout(1200)
        logger.info(f"[scroll_to_top] {result}")
    except Exception as e:
        logger.warning(f"Không thể cuộn về đầu trang: {e}")






async def click_load_more_if_available(page: Page) -> bool:
    """Thử bấm nút 'Xem thêm' / 'Tải thêm'. Trả về True nếu đã bấm thành công."""
    # Selector từ DevTools: button[data-feed-loadmore="true"] / text 'Xem thêm'
    load_more_selectors = [
        'button[data-feed-loadmore="true"]',
        'button[data-circle-feed-loadmore="true"]',
        'button:has-text("Xem thêm")',
        'button:has-text("Tải thêm")',
        'button:has-text("Load more")',
        '[data-feed-loadmore]',
        '[data-circle-feed-loadmore]',
    ]
    for sel in load_more_selectors:
        try:
            btn = page.locator(sel)
            if await btn.count() > 0 and await btn.first.is_visible():
                await btn.first.scroll_into_view_if_needed()
                await btn.first.click(timeout=3000)
                logger.info("Đã bấm nút 'Xem thêm' để tải thêm bài viết.")
                await page.wait_for_timeout(2500)
                return True
        except Exception:
            continue
    return False


async def scroll_feed(page: Page):
    """Cuộn màn hình xuống hoặc bấm nút 'Xem thêm' để load thêm bài viết."""
    # Ưu tiên bấm nút "Xem thêm" nếu có
    clicked = await click_load_more_if_available(page)
    if clicked:
        return

    # Fallback: scroll thường nếu không có nút "Xem thêm"
    logger.info("Đang cuộn tìm bài viết tiếp theo...")
    await page.mouse.wheel(0, 800)
    await page.wait_for_timeout(1500)

