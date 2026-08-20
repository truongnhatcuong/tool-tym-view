import asyncio
from playwright.async_api import Page
from utils.logger import logger

async def ensure_login(page: Page):
    logger.info("Checking login state...")
    try:
        # Để tránh việc script chạy tuột đi và đóng trình duyệt khi bạn đang nhập,
        # chúng ta sẽ tạm dừng script tại đây để bạn đăng nhập thủ công.
        
        # Mở URL và đợi load
        await page.wait_for_load_state("networkidle")
        
        # In ra màn hình console yêu cầu người dùng
        print("\n" + "="*50)
        print("Please login manually in the browser.")
        print("Press ENTER in this terminal after login is completed...")
        print("="*50 + "\n")
        
        # Chờ người dùng nhấn Enter trong terminal (chạy trong luồng riêng để không block asyncio)
        await asyncio.to_thread(input, "")
        
        logger.info("Tiếp tục thực thi automation...")
    except Exception as e:
        logger.error(f"Error during login check: {e}")
