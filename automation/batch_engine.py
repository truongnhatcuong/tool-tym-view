import asyncio
import time
from typing import Optional, Callable, List, Dict, Any

from config_manager import AppConfig
from profile_manager import ProfileConfig
from automation.engine import AutomationEngine
from utils.logger import logger


class BatchEngine:
    """
    Bộ máy chạy tuần tự nhiều profile (Batch Run).
    Mỗi profile sẽ khởi động trình duyệt riêng, chạy đúng số video
    được cấu hình trong profile đó, rồi đóng lại trước khi chuyển
    sang profile tiếp theo.
    """

    def __init__(self, base_config: AppConfig, profiles: List[ProfileConfig]):
        """
        Args:
            base_config: Cấu hình gốc (react_only, element_mode, timing...) dùng chung.
            profiles:    Danh sách profile cần chạy đồng thời.
        """
        self.base_config = base_config
        self.profiles = profiles
        self._stop_requested = False
        self.is_running = False
        self._engines: List[AutomationEngine] = []

        self.stats: Dict[str, Any] = {
            "total_profiles": len(profiles),
            "current_profile_index": 0,
            "completed_profiles": 0,
            "total_reacted": 0,
            "total_skipped": 0,
            "total_errors": 0,
            "start_time": 0.0,
            "elapsed_seconds": 0,
            "current_profile_name": "",
            "current_profile_video_current": 0,
            "current_profile_video_total": 0,
        }

        # Callbacks cho GUI
        self.on_log: Optional[Callable[[str, str], None]] = None
        self.on_profile_start: Optional[Callable[[ProfileConfig, int, int], None]] = None
        self.on_profile_finish: Optional[Callable[[ProfileConfig, Dict[str, Any]], None]] = None
        self.on_batch_finish: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_batch_progress: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_video_progress: Optional[Callable[[int, int, Dict[str, Any]], None]] = None

    # ------------------------------------------------------------------
    # Control
    # ------------------------------------------------------------------

    def request_stop(self):
        """Yêu cầu dừng Batch an toàn. Các profile đang chạy sẽ được kết thúc sạch."""
        self._stop_requested = True
        for engine in self._engines:
            engine.request_stop()
        self._emit_log("Nhận lệnh dừng Batch. Đang dừng các profile hiện tại...", "WARNING")

    def request_pause(self):
        """Tạm dừng các profile đang chạy."""
        for engine in self._engines:
            engine.request_pause()

    def request_resume(self):
        """Tiếp tục các profile đang bị tạm dừng."""
        for engine in self._engines:
            engine.request_resume()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _emit_log(self, message: str, level: str = "INFO"):
        logger.info(f"[BATCH] {message}")
        if self.on_log:
            try:
                self.on_log(f"[BATCH] {message}", level)
            except Exception:
                pass

    def _emit_batch_progress(self):
        if self.stats["start_time"] > 0:
            self.stats["elapsed_seconds"] = int(time.time() - self.stats["start_time"])
        if self.on_batch_progress:
            try:
                self.on_batch_progress(dict(self.stats))
            except Exception:
                pass

    def _build_engine_config(self, profile: ProfileConfig) -> AppConfig:
        """
        Xây dựng AppConfig cho một profile cụ thể:
        - URL, Video ID, max_videos lấy từ profile.
        - Timing, element_mode, headless, dry_run lấy từ base_config.
        """
        return AppConfig(
            ucircle_url=profile.ucircle_url or self.base_config.ucircle_url,
            target_video_id=profile.target_video_id or self.base_config.target_video_id,
            react_only=self.base_config.react_only,
            watch_min_seconds=self.base_config.watch_min_seconds,
            watch_max_seconds=self.base_config.watch_max_seconds,
            action_delay_min=self.base_config.action_delay_min,
            action_delay_max=self.base_config.action_delay_max,
            max_videos=profile.max_videos,
            headless=self.base_config.headless,
            dry_run=self.base_config.dry_run,
            profile_dir=profile.profile_dir or self.base_config.profile_dir,
            element_mode=self.base_config.element_mode,
            target_type=profile.target_type,
        )

    # ------------------------------------------------------------------
    # Main run loop
    # ------------------------------------------------------------------

    async def _run_single_profile(self, idx: int, profile: ProfileConfig):
        """Chạy một profile cụ thể."""
        if self._stop_requested:
            return

        separator = "─" * 50
        self._emit_log(separator, "INFO")
        self._emit_log(
            f"[{idx + 1}/{len(self.profiles)}] Bắt đầu Profile: [{profile.name}]", "INFO"
        )
        self._emit_log(f"[{profile.name}] URL: {profile.get_display_url()}", "INFO")
        self._emit_log(f"[{profile.name}] Video mục tiêu: {profile.max_videos}", "INFO")
        self._emit_log(f"[{profile.name}] Proxy: {profile.get_proxy_display()}", "INFO")
        self._emit_log(separator, "INFO")

        if self.on_profile_start:
            try:
                self.on_profile_start(profile, idx + 1, len(self.profiles))
            except Exception:
                pass

        cfg = self._build_engine_config(profile)

        proxy_playwright = None
        if profile.proxy and profile.proxy.is_valid():
            proxy_playwright = profile.proxy.to_playwright_proxy()
            self._emit_log(f"[{profile.name}] → Proxy đã thiết lập: {profile.proxy.display_str()}", "INFO")

        engine = AutomationEngine(cfg, proxy=proxy_playwright)
        self._engines.append(engine)

        engine.on_log = lambda msg, lvl: self._emit_log(f"[{profile.name}] {msg}", lvl)
        engine.on_progress = lambda cur, tot, st: self._on_engine_progress(cur, tot, st)

        try:
            await engine.run()

            profile_stats = engine.stats
            self.stats["total_reacted"] += profile_stats.get("reacted", 0)
            self.stats["total_skipped"] += profile_stats.get("skipped", 0)
            self.stats["total_errors"] += profile_stats.get("errors", 0)
            self.stats["completed_profiles"] += 1

            self._emit_log(
                f"✓ Profile [{profile.name}] hoàn thành — "
                f"Reacted: {profile_stats.get('reacted', 0)}, "
                f"Skipped: {profile_stats.get('skipped', 0)}, "
                f"Lỗi: {profile_stats.get('errors', 0)}",
                "INFO"
            )

            if self.on_profile_finish:
                try:
                    self.on_profile_finish(profile, profile_stats)
                except Exception:
                    pass

        except Exception as e:
            self._emit_log(f"✗ Lỗi nghiêm trọng khi chạy profile [{profile.name}]: {e}", "ERROR")
            self.stats["total_errors"] += 1

        self._emit_batch_progress()

    async def run(self):
        """Chạy ĐỒNG THỜI (concurrently) tất cả profiles trong danh sách."""
        self.is_running = True
        self._stop_requested = False
        self._engines = []

        self.stats["start_time"] = time.time()
        self.stats["total_profiles"] = len(self.profiles)
        self.stats["current_profile_index"] = 0
        self.stats["completed_profiles"] = 0
        self.stats["total_reacted"] = 0
        self.stats["total_skipped"] = 0
        self.stats["total_errors"] = 0

        self._emit_log(f"══════════════════════════════════════════════════", "INFO")
        self._emit_log(f"BẮT ĐẦU BATCH RUN (ĐA LUỒNG): {len(self.profiles)} profile", "INFO")
        self._emit_log(f"══════════════════════════════════════════════════", "INFO")
        self._emit_batch_progress()

        # Tạo danh sách các task để chạy đồng thời
        tasks = []
        for idx, profile in enumerate(self.profiles):
            tasks.append(self._run_single_profile(idx, profile))

        # Đợi tất cả các profile chạy xong
        if tasks:
            await asyncio.gather(*tasks)

        # Kết thúc Batch
        self.is_running = False
        self._engines = []

        self._emit_log("══════════════════════════════════════════════════", "INFO")
        self._emit_log(
            f"🏁 BATCH RUN HOÀN THÀNH! "
            f"Profile: {self.stats['completed_profiles']}/{self.stats['total_profiles']} | "
            f"Tổng Reacted: {self.stats['total_reacted']} | "
            f"Skipped: {self.stats['total_skipped']} | "
            f"Lỗi: {self.stats['total_errors']}",
            "INFO"
        )
        self._emit_log("══════════════════════════════════════════════════", "INFO")

        self._emit_batch_progress()

        if self.on_batch_finish:
            try:
                self.on_batch_finish(dict(self.stats))
            except Exception:
                pass

    def _on_engine_progress(self, current: int, total: int, stats: Dict[str, Any]):
        """Cập nhật tiến độ video của profile đang chạy."""
        self.stats["current_profile_video_current"] = current
        self.stats["current_profile_video_total"] = total
        self._emit_batch_progress()
        if self.on_video_progress:
            try:
                self.on_video_progress(current, total, stats)
            except Exception:
                pass
