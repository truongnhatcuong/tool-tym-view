import asyncio
import time
from typing import Optional, Callable, Dict, Any
from playwright.async_api import async_playwright
from config_manager import AppConfig, extract_url_details
from automation.browser import launch_browser
from automation.login import ensure_login
from automation.feed import switch_to_wavee_tab, click_specific_video
from automation.video import watch_video
from automation.actions import react_element_if_needed, scroll_to_next_video, is_video_already_reacted
from utils.logger import logger
from utils.helpers import random_delay

class AutomationEngine:
    def __init__(self, config: AppConfig):
        self.config = config
        self.is_running = False
        self.is_paused = False
        self._stop_requested = False
        self.stats = {
            "total": config.max_videos,
            "current": 0,
            "reacted": 0,
            "skipped": 0,
            "errors": 0,
            "start_time": 0.0,
            "elapsed_seconds": 0
        }
        
        # Callbacks cho GUI / CLI
        self.on_status_change: Optional[Callable[[str], None]] = None
        self.on_progress: Optional[Callable[[int, int, Dict[str, Any]], None]] = None
        self.on_log: Optional[Callable[[str, str], None]] = None
        self.on_finish: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None

    def _set_status(self, status: str):
        if self.on_status_change:
            try:
                self.on_status_change(status)
            except Exception:
                pass

    def _emit_progress(self):
        if self.stats["start_time"] > 0:
            self.stats["elapsed_seconds"] = int(time.time() - self.stats["start_time"])
        if self.on_progress:
            try:
                self.on_progress(self.stats["current"], self.stats["total"], self.stats)
            except Exception:
                pass

    def _emit_log(self, message: str, level: str = "INFO"):
        if self.on_log:
            try:
                self.on_log(message, level)
            except Exception:
                pass

    def request_stop(self):
        """Yêu cầu dừng tiến trình an toàn"""
        self._stop_requested = True
        self._set_status("Đang dừng...")
        self._emit_log("Nhận lệnh dừng từ người dùng. Đang đóng...", "WARNING")

    def request_pause(self):
        """Tạm dừng tiến trình"""
        self.is_paused = True
        self._set_status("Đã tạm dừng")
        self._emit_log("Tiến trình đã tạm dừng.", "WARNING")

    def request_resume(self):
        """Tiếp tục tiến trình sau khi tạm dừng"""
        self.is_paused = False
        self._set_status("Đang tiếp tục...")
        self._emit_log("Tiếp tục tiến trình.", "INFO")

    async def _check_control_flags(self) -> bool:
        """Kiểm tra cờ pause / stop. Trả về False nếu cần dừng."""
        if self._stop_requested:
            return False
        
        while self.is_paused and not self._stop_requested:
            await asyncio.sleep(0.5)
            
        return not self._stop_requested

    async def run(self):
        """Chạy toàn bộ luồng automation"""
        self.is_running = True
        self._stop_requested = False
        self.is_paused = False
        self.stats = {
            "total": self.config.max_videos,
            "current": 0,
            "reacted": 0,
            "skipped": 0,
            "errors": 0,
            "start_time": time.time(),
            "elapsed_seconds": 0
        }
        self._emit_progress()
        self._set_status("Đang khởi động trình duyệt...")
        
        # Bóc tách video ID nếu chưa có
        target_video_id = self.config.target_video_id
        if not target_video_id:
            url_info = extract_url_details(self.config.ucircle_url)
            target_video_id = url_info.get("video_id") or "d4f2b67c-317c-46fd-bbb7-c1bab3ed4740"

        browser = None
        try:
            async with async_playwright() as p:
                self._emit_log("Khởi động Playwright Chromium...", "INFO")
                browser = await launch_browser(
                    p, 
                    headless=self.config.headless, 
                    profile_dir=self.config.profile_dir
                )

                if not await self._check_control_flags():
                    return

                page = browser.pages[0] if browser.pages else await browser.new_page()

                self._set_status("Đang truy cập UCircle...")
                self._emit_log(f"Mở URL: {self.config.ucircle_url}", "INFO")
                logger.info(f"Opening UCircle URL: {self.config.ucircle_url}")
                await page.goto(self.config.ucircle_url)

                if not await self._check_control_flags():
                    return

                self._set_status("Kiểm tra đăng nhập...")
                await ensure_login(page)

                if not await self._check_control_flags():
                    return

                self._set_status("Chuyển sang tab Wavee...")
                success_tab = await switch_to_wavee_tab(page)
                if not success_tab:
                    msg = "Không thể chuyển sang tab Wavee."
                    self._emit_log(msg, "ERROR")
                    logger.error(msg)
                    if self.on_error:
                        self.on_error(msg)
                    return

                if not await self._check_control_flags():
                    return

                self._set_status(f"Mở video khởi đầu ({target_video_id[:8]}...)...")
                self._emit_log(f"Tìm và mở video mục tiêu: {target_video_id}", "INFO")
                success_video = await click_specific_video(page, target_video_id)

                if not success_video:
                    self._emit_log("Không tìm thấy video khởi đầu cụ thể, thử tiếp tục với video hiện có...", "WARNING")

                max_videos = self.config.max_videos
                for index in range(max_videos):
                    if not await self._check_control_flags():
                        self._emit_log("Tiến trình đã được dừng bởi người dùng.", "WARNING")
                        break

                    self.stats["current"] = index + 1
                    self._emit_progress()
                    self._set_status(f"Đang xử lý video {index + 1}/{max_videos}")
                    self._emit_log(f"--- Đang xử lý video {index + 1}/{max_videos} ---", "INFO")
                    logger.info(f"--- Processing video {index + 1}/{max_videos} ---")

                    try:
                        already_done = await is_video_already_reacted(page)
                        if already_done:
                            self.stats["skipped"] += 1
                            self._emit_log("Video đã được thả ngũ hành trước đó. Bỏ qua.", "INFO")
                            logger.info("Video already reacted. Skipping.")
                        else:
                            if self.config.react_only:
                                self._emit_log("Chế độ React ngay: Bỏ qua bước chờ xem, tương tác ngay.", "INFO")
                            else:
                                self._set_status(f"Đang xem video {index + 1}...")
                                self._emit_log(f"Đang xem video ({self.config.watch_min_seconds}s - {self.config.watch_max_seconds}s)...", "INFO")
                                await watch_video(page, self.config.watch_min_seconds, self.config.watch_max_seconds)

                            if not await self._check_control_flags():
                                break

                            self._set_status(f"Đang thả ngũ hành video {index + 1}...")
                            success, status_code = await react_element_if_needed(
                                page, 
                                dry_run=self.config.dry_run, 
                                element_mode=self.config.element_mode
                            )
                            
                            if success:
                                self.stats["reacted"] += 1
                                self._emit_log(f"Thả ngũ hành thành công ({status_code})!", "INFO")
                            elif status_code == "already_reacted":
                                self.stats["skipped"] += 1
                                self._emit_log("Video đã có reaction. Bỏ qua.", "INFO")
                            else:
                                self.stats["errors"] += 1
                                self._emit_log(f"Không thể thả ngũ hành: {status_code}", "WARNING")
                    except Exception as e:
                        self.stats["errors"] += 1
                        err_msg = f"Lỗi xử lý video {index + 1}: {e}"
                        self._emit_log(err_msg, "ERROR")
                        logger.error(err_msg)

                    self._emit_progress()

                    if index < max_videos - 1:
                        if not await self._check_control_flags():
                            break
                        self._set_status("Chuyển sang video tiếp theo...")
                        await scroll_to_next_video(page)
                        await random_delay(self.config.action_delay_min, self.config.action_delay_max)

                self._set_status("Hoàn thành phiên chạy!")
                self._emit_log(f"Hoàn thành phiên chạy! Tổng: {self.stats['current']}, Reacted: {self.stats['reacted']}, Skipped: {self.stats['skipped']}, Errors: {self.stats['errors']}", "INFO")
                logger.info("Session completed. Stopping automation.")
        except Exception as e:
            err = f"Lỗi nghiêm trọng trong quá trình chạy: {e}"
            self._emit_log(err, "ERROR")
            logger.error(err)
            if self.on_error:
                self.on_error(err)
        finally:
            self.is_running = False
            self.is_paused = False
            self._set_status("Đã dừng")
            if browser:
                try:
                    await browser.close()
                except Exception:
                    pass
            if self.on_finish:
                try:
                    self.on_finish(self.stats)
                except Exception:
                    pass
