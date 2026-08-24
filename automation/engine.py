import asyncio
import time
from typing import Optional, Callable, Dict, Any
from playwright.async_api import async_playwright
from config_manager import AppConfig, extract_url_details
from automation.browser import launch_browser
from automation.login import ensure_login
from automation.feed import switch_to_wavee_tab, click_specific_video
from automation.feed_actions import switch_to_feed_tab, scroll_feed, scroll_to_top_feed, click_load_more_if_available
from automation.video import watch_video
from automation.actions import react_element_if_needed, scroll_to_next_video, is_video_already_reacted, _draw_element, _normalize_element_name
from utils.logger import logger
from utils.helpers import random_delay

class AutomationEngine:
    def __init__(self, config: AppConfig, proxy: Optional[Dict[str, str]] = None):
        """
        Args:
            config: Cấu hình chạy.
            proxy:  Proxy dạng Playwright dict ({"server": ..., "username": ..., "password": ...}).
                    None = không dùng proxy.
        """
        self.config = config
        self.proxy = proxy  # Proxy riêng cho engine này (từ ProfileConfig)
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
                if self.proxy:
                    self._emit_log(f"Proxy: {self.proxy.get('server', '')}", "INFO")
                browser = await launch_browser(
                    p,
                    headless=self.config.headless,
                    profile_dir=self.config.profile_dir,
                    proxy=self.proxy
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

                target_type = self.config.target_type
                if target_type == "feed":
                    await self._run_feed_mode(page, browser)
                else:
                    await self._run_wavee_mode(page, target_video_id, browser)

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
                    await browser.storage_state(path="session.json")
                    await browser.close()
                    if browser.browser:
                        await browser.browser.close()
                except Exception:
                    pass
            if self.on_finish:
                try:
                    self.on_finish(self.stats)
                except Exception:
                    pass

    async def _run_wavee_mode(self, page, target_video_id, browser):
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

    async def _run_feed_mode(self, page, browser):
        self._set_status("Chuyển sang tab Bảng tin...")
        success_tab = await switch_to_feed_tab(page)
        if not success_tab:
            msg = "Không thể chuyển sang tab Bảng tin."
            self._emit_log(msg, "ERROR")
            if self.on_error:
                self.on_error(msg)
            return

        max_posts = self.config.max_videos
        from utils.selectors import UCircleSelectors

        # Scroll lên đầu trang bắt đầu từ bài mới nhất
        self._set_status("Đang scroll về đầu trang bảng tin...")
        await scroll_to_top_feed(page)
        await random_delay(0.5, 1.0)

        self._emit_log(f"Bắt đầu lướt Bảng tin (mục tiêu {max_posts} bài)...", "INFO")

        processed_buttons = set()

        for index in range(max_posts):
            if not await self._check_control_flags():
                self._emit_log("Tiến trình đã được dừng bởi người dùng.", "WARNING")
                break

            self.stats["current"] = index + 1
            self._emit_progress()
            self._set_status(f"Đang tìm/xử lý bài viết {index + 1}/{max_posts}")

            # Tìm nút react chưa xử lý theo đúng thứ tự DOM (từ bài mới nhất trên cùng xuống dưới)
            target_button = None
            retries = 0
            while not target_button and retries < 10:
                if not await self._check_control_flags():
                    return

                # Cách 1 (Chuẩn nhất): Quét theo thứ tự các thẻ article từ trên xuống dưới (từ mới nhất đến cũ nhất)
                articles = await page.locator('article[data-post="true"], article[data-post-id], article').all()
                for art in articles:
                    try:
                        post_id = await art.get_attribute("data-post-id")
                        if not post_id:
                            post_id = await art.evaluate("el => el.getAttribute('data-post-id') || el.innerText.slice(0, 30)")
                        
                        if post_id and post_id not in processed_buttons:
                            react_btn = art.locator('button[data-nguhanh-main="true"], button[data-react]').first
                            if await react_btn.count() > 0:
                                target_button = react_btn
                                processed_buttons.add(post_id)
                                break
                    except Exception:
                        pass

                # Cách 2 (Fallback): Quét tất cả các nút react nếu không tìm thấy qua article
                if not target_button:
                    buttons = await page.locator(UCircleSelectors.FEED_REACT_BTN).all()
                    for btn in buttons:
                        try:
                            post_id = await btn.evaluate("b => { const art = b.closest('article'); return art ? art.getAttribute('data-post-id') : null; }")
                            if not post_id:
                                box = await btn.bounding_box()
                                if box:
                                    post_id = f"fallback_{round(box['x'])}_{round(box['y'])}"

                            if post_id and post_id not in processed_buttons:
                                target_button = btn
                                processed_buttons.add(post_id)
                                break
                        except Exception:
                            pass

                if not target_button:
                    self._set_status("Cuộn tìm bài viết mới...")
                    await scroll_feed(page)
                    retries += 1

            if not target_button:
                # Trước khi dừng, thử bấm "Xem thêm" một lần nữa
                self._emit_log("Không tìm thấy bài viết mới. Đang thử bấm 'Xem thêm'...", "WARNING")
                scrolled_to_bottom = False
                try:
                    # Scroll xuống cuối trang để load nút "Xem thêm"
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await page.wait_for_timeout(2000)
                    load_more_clicked = await click_load_more_if_available(page)
                    if load_more_clicked:
                        scrolled_to_bottom = True
                        await random_delay(1.5, 2.5)
                except Exception:
                    pass

                if not scrolled_to_bottom:
                    self._emit_log("Không tìm thấy bài viết mới nào sau nhiều lần cuộn. Kết thúc.", "WARNING")
                    break

                # Sau khi bấm Xem thêm, quét lại theo article
                articles_after = await page.locator('article[data-post="true"], article[data-post-id], article').all()
                for art in articles_after:
                    try:
                        post_id = await art.get_attribute("data-post-id")
                        if not post_id:
                            post_id = await art.evaluate("el => el.getAttribute('data-post-id') || el.innerText.slice(0, 30)")
                        
                        if post_id and post_id not in processed_buttons:
                            react_btn = art.locator('button[data-nguhanh-main="true"], button[data-react]').first
                            if await react_btn.count() > 0:
                                target_button = react_btn
                                processed_buttons.add(post_id)
                                break
                    except Exception:
                        pass

                if not target_button:
                    self._emit_log("Không có bài viết mới sau khi bấm 'Xem thêm'. Kết thúc.", "WARNING")
                    break

            try:
                await target_button.scroll_into_view_if_needed()
                await random_delay(1.0, 1.5)
                self._set_status(f"Đang kiểm tra/thả bài viết {index + 1}...")

                if self.config.dry_run:
                    self._emit_log("[DRY-RUN] Sẽ thả ngũ hành bài viết này.", "INFO")
                    self.stats["reacted"] += 1
                else:
                    # ────────────────────────────────────────────────────────
                    # BƯỚC 1: Click nút chính để mở tray ngũ hành
                    # Selector thực tế: button[data-nguhanh-main="true"]
                    # ────────────────────────────────────────────────────────
                    await target_button.click()
                    await random_delay(0.5, 0.8)

                    # ────────────────────────────────────────────────────────
                    # BƯỚC 2: Chờ tray xuất hiện
                    # Selector thực tế: div[data-nguhanh-tray="true"]
                    # ────────────────────────────────────────────────────────
                    tray_loc = page.locator('div[data-nguhanh-tray="true"]')
                    try:
                        await tray_loc.wait_for(state="visible", timeout=4000)
                    except Exception:
                        self._emit_log(f"Bài viết {index + 1}: Không mở được tray. Bỏ qua.", "WARNING")
                        self.stats["errors"] += 1
                        continue

                    # ────────────────────────────────────────────────────────
                    # BƯỚC 3: Đọc tất cả actors trong tray
                    # Selector: button[data-nguhanh-actor]
                    # Đã thả: aria-checked="true" hoặc data-nguhanh-actor-on="true"
                    # ────────────────────────────────────────────────────────
                    actor_btns = tray_loc.locator('button[data-nguhanh-actor]')
                    actor_count = await actor_btns.count()

                    if actor_count == 0:
                        # Không có selector actor → thả thẳng (chế độ cá nhân)
                        opt_btns = tray_loc.locator('button[data-nguhanh-opt]')
                        opt_count = await opt_btns.count()
                        if opt_count > 0:
                            opts = []
                            for oi in range(opt_count):
                                ob = opt_btns.nth(oi)
                                v = await ob.get_attribute("data-nguhanh-opt")
                                if v:
                                    opts.append(v)
                            chosen = _draw_element(opts, self.config.element_mode) if opts else None
                            if chosen:
                                try:
                                    await tray_loc.locator(f'button[data-nguhanh-opt="{chosen}"]').click(timeout=3000)
                                    self.stats["reacted"] += 1
                                    self._emit_log(f"Đã thả '{chosen}' cho bài viết {index + 1} (cá nhân).", "INFO")
                                except Exception as e:
                                    self._emit_log(f"Lỗi thả cá nhân: {e}", "WARNING")
                        else:
                            self._emit_log("Không tìm thấy nút reaction trong tray.", "WARNING")
                        continue

                    self._emit_log(f"Phát hiện {actor_count} tư cách cho bài viết {index + 1}.", "INFO")

                    # ────────────────────────────────────────────────────────
                    # BƯỚC 4: Lặp qua từng actor
                    # ────────────────────────────────────────────────────────
                    is_tray_open = True
                    for actor_idx in range(actor_count):
                        if not await self._check_control_flags():
                            break

                        # Mở lại khay nếu nó đã bị đóng
                        if not is_tray_open:
                            await target_button.click()
                            await random_delay(0.5, 0.8)
                            try:
                                await tray_loc.wait_for(state="visible", timeout=4000)
                            except Exception:
                                self._emit_log(f"Không mở được tray cho actor {actor_idx + 1}.", "WARNING")
                                break
                            is_tray_open = True

                        # Lấy lại button actor (sau khi mở lại tray)
                        actor_btn = tray_loc.locator('button[data-nguhanh-actor]').nth(actor_idx)
                        try:
                            actor_name = (await actor_btn.text_content() or f"Actor {actor_idx + 1}").strip()
                            actor_name = actor_name or await actor_btn.get_attribute("title") or f"Actor {actor_idx + 1}"
                        except Exception:
                            actor_name = f"Actor {actor_idx + 1}"

                        # (Đã loại bỏ logic kiểm tra sớm qua attribute của actor_btn vì UCircle dùng nó để đánh dấu tab đang chọn)

                        # ── Chọn actor này ────────────────────────────────
                        self._emit_log(f"Đang chọn tư cách: {actor_name} ({actor_idx + 1}/{actor_count})", "INFO")
                        try:
                            await actor_btn.scroll_into_view_if_needed()
                            await actor_btn.click()
                            await random_delay(0.3, 0.6)
                        except Exception as e:
                            self._emit_log(f"Lỗi khi click actor '{actor_name}': {e}", "WARNING")
                            continue

                        # Kiểm tra xem tư cách này đã thả ngũ hành chưa (bằng cách xem các tuỳ chọn ở dưới)
                        is_reacted = False
                        try:
                            opts = await tray_loc.locator('button[data-nguhanh-opt]').all()
                            for opt in opts:
                                aria_checked = await opt.get_attribute("aria-checked")
                                react_on = await opt.get_attribute("data-react-on")
                                class_name = await opt.get_attribute("class") or ""
                                if aria_checked == "true" or react_on == "true" or "On_" in class_name:
                                    is_reacted = True
                                    break
                        except Exception:
                            pass
                            
                        if is_reacted:
                            self._emit_log(f"Tư cách '{actor_name}' đã thả ngũ hành trước đó. Bỏ qua.", "INFO")
                            continue

                        # ── Đọc danh sách reaction options ────────────────
                        # Selector thực tế: button[data-nguhanh-opt="hoa/tho/kim/thuy/moc"]
                        opt_btns = tray_loc.locator('button[data-nguhanh-opt]')
                        opt_count = await opt_btns.count()
                        if opt_count == 0:
                            self._emit_log(f"Không tìm thấy nút ngũ hành cho '{actor_name}'.", "WARNING")
                            continue

                        opts = []
                        for oi in range(opt_count):
                            ob = opt_btns.nth(oi)
                            v = await ob.get_attribute("data-nguhanh-opt")
                            if v:
                                opts.append(v)

                        chosen = _draw_element(opts, self.config.element_mode) if opts else None
                        if not chosen:
                            self._emit_log(f"Không chọn được ngũ hành cho '{actor_name}'.", "WARNING")
                            continue

                        # ── Click reaction ────────────────────────────────
                        try:
                            opt_btn = tray_loc.locator(f'button[data-nguhanh-opt="{chosen}"]')
                            await opt_btn.scroll_into_view_if_needed()
                            await opt_btn.wait_for(state="visible", timeout=3000)
                            await opt_btn.click(timeout=3000)
                            self.stats["reacted"] += 1
                            self._emit_log(f"Đã thả '{chosen}' cho bài viết {index + 1} (Tư cách {actor_idx + 1}/{actor_count}: {actor_name}).", "INFO")
                            await random_delay(0.5, 1.0)
                            is_tray_open = False
                        except Exception as e:
                            self._emit_log(f"Lỗi thả '{chosen}' cho '{actor_name}': {e}", "WARNING")
                            self.stats["errors"] += 1

                    # Sau khi quét xong toàn bộ tư cách của bài viết này,
                    # Nếu khay vẫn đang mở (vì toàn bị bỏ qua) thì đóng lại để không dính lỗi tray ảo ở bài sau.
                    if is_tray_open:
                        try:
                            await target_button.click(force=True)
                            await random_delay(0.3, 0.5)
                        except Exception:
                            pass
                            
            except Exception as e:
                self.stats["errors"] += 1
                self._emit_log(f"Lỗi khi xử lý bài viết {index + 1}: {e}", "ERROR")

            await random_delay(self.config.action_delay_min, self.config.action_delay_max)

