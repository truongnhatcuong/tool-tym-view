import os
import sys
import time
import asyncio
import threading
import subprocess
from datetime import datetime
from typing import Optional, Dict, Any

import customtkinter as ctk
from PIL import Image, ImageTk

from config_manager import (
    AppConfig, 
    load_config, 
    save_config, 
    validate_config, 
    extract_url_details, 
    get_presets
)
from automation.engine import AutomationEngine
from automation.browser import launch_browser
from playwright.async_api import async_playwright
from utils.logger import logger

# Cài đặt giao diện tối hiện đại
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class UCircleAutomationGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("UCircle Video Interaction QA Tool - Auto React Pro")
        self.geometry("1020x760")
        self.minsize(920, 680)

        # Cấu hình hiện tại
        self.config = load_config()
        self.engine: Optional[AutomationEngine] = None
        self.worker_thread: Optional[threading.Thread] = None
        self.is_running = False
        self.auto_scroll_log = True
        self.start_timestamp = 0.0

        # UI Components Setup
        self._setup_ui()
        self._load_config_to_ui()
        self._refresh_screenshots_list()

        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _setup_ui(self):
        # Grid layout configuration
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # 1. Header Bar
        self.header_frame = ctk.CTkFrame(self, height=65, corner_radius=0, fg_color=("#1e293b", "#0f172a"))
        self.header_frame.grid(row=0, column=0, sticky="ew")
        self.header_frame.grid_columnconfigure(1, weight=1)

        # Logo / Title in Header
        self.title_label = ctk.CTkLabel(
            self.header_frame,
            text="✨ UCIRCLE QA AUTOMATION",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#38bdf8"
        )
        self.title_label.grid(row=0, column=0, padx=(20, 10), pady=15, sticky="w")

        self.subtitle_label = ctk.CTkLabel(
            self.header_frame,
            text="Tự động tương tác Ngũ Hành & Video Feed Wavee",
            font=ctk.CTkFont(size=12),
            text_color="#94a3b8"
        )
        self.subtitle_label.grid(row=0, column=1, padx=0, pady=15, sticky="w")

        # Global Status Badge
        self.status_badge = ctk.CTkLabel(
            self.header_frame,
            text="● SẴN SÀNG",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#10b981",
            fg_color="#064e3b",
            corner_radius=12,
            padx=12,
            pady=4
        )
        self.status_badge.grid(row=0, column=2, padx=20, pady=15, sticky="e")

        # 2. Main Tabview
        self.tabview = ctk.CTkTabview(
            self,
            corner_radius=10,
            fg_color=("#1e293b", "#1e293b"),
            segmented_button_selected_color="#0284c7",
            segmented_button_selected_hover_color="#0369a1"
        )
        self.tabview.grid(row=1, column=0, padx=15, pady=(5, 10), sticky="nsew")

        self.tab_dashboard = self.tabview.add("🚀 Bảng Điều Khiển")
        self.tab_settings = self.tabview.add("⚙️ Cài Đặt Cấu Hình")
        self.tab_history = self.tabview.add("🖼️ Lịch Sử & Ảnh Lỗi")

        # Build each tab
        self._build_dashboard_tab()
        self._build_settings_tab()
        self._build_history_tab()

    # -------------------------------------------------------------
    # TAB 1: BẢNG ĐIỀU KHIỂN (DASHBOARD)
    # -------------------------------------------------------------
    def _build_dashboard_tab(self):
        self.tab_dashboard.grid_columnconfigure(0, weight=1)
        self.tab_dashboard.grid_rowconfigure(2, weight=1)

        # 1. Metric Cards Frame
        self.metrics_frame = ctk.CTkFrame(self.tab_dashboard, fg_color="transparent")
        self.metrics_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        for i in range(4):
            self.metrics_frame.grid_columnconfigure(i, weight=1)

        # Card 1: Total Processed
        self.card_total = self._create_metric_card(
            self.metrics_frame, 0, "📹 VIDEO ĐÃ DUYỆT", "0 / 0", "#38bdf8"
        )
        # Card 2: Reacted
        self.card_reacted = self._create_metric_card(
            self.metrics_frame, 1, "💖 ĐÃ THẢ NGŨ HÀNH", "0", "#10b981"
        )
        # Card 3: Skipped
        self.card_skipped = self._create_metric_card(
            self.metrics_frame, 2, "⏭️ ĐÃ BỎ QUA (CŨ)", "0", "#f59e0b"
        )
        # Card 4: Runtime / Errors
        self.card_time = self._create_metric_card(
            self.metrics_frame, 3, "⏱️ THỜI GIAN CHẠY", "00:00:00", "#a855f7"
        )

        # 2. Control Toolbar & Progress Frame
        self.ctrl_frame = ctk.CTkFrame(self.tab_dashboard, fg_color=("#0f172a", "#0f172a"), corner_radius=8)
        self.ctrl_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        self.ctrl_frame.grid_columnconfigure(4, weight=1)

        # Buttons
        self.btn_start = ctk.CTkButton(
            self.ctrl_frame,
            text="▶ Bắt Đầu Chạy",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#10b981",
            hover_color="#059669",
            text_color="#ffffff",
            height=38,
            command=self._on_start_clicked
        )
        self.btn_start.grid(row=0, column=0, padx=(15, 8), pady=12)

        self.btn_pause = ctk.CTkButton(
            self.ctrl_frame,
            text="⏸ Tạm Dừng",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#f59e0b",
            hover_color="#d97706",
            text_color="#ffffff",
            height=38,
            state="disabled",
            command=self._on_pause_clicked
        )
        self.btn_pause.grid(row=0, column=1, padx=8, pady=12)

        self.btn_stop = ctk.CTkButton(
            self.ctrl_frame,
            text="⏹ Dừng Lại",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#ef4444",
            hover_color="#dc2626",
            text_color="#ffffff",
            height=38,
            state="disabled",
            command=self._on_stop_clicked
        )
        self.btn_stop.grid(row=0, column=2, padx=8, pady=12)

        self.btn_open_browser = ctk.CTkButton(
            self.ctrl_frame,
            text="🌐 Mở Trình Duyệt Đăng Nhập",
            font=ctk.CTkFont(size=12),
            fg_color="#334155",
            hover_color="#475569",
            height=38,
            command=self._open_browser_manual
        )
        self.btn_open_browser.grid(row=0, column=3, padx=8, pady=12)

        # Progress and sub-status
        self.progress_container = ctk.CTkFrame(self.ctrl_frame, fg_color="transparent")
        self.progress_container.grid(row=0, column=4, padx=(15, 15), pady=8, sticky="ew")
        self.progress_container.grid_columnconfigure(0, weight=1)

        self.lbl_progress_status = ctk.CTkLabel(
            self.progress_container,
            text="Chưa chạy",
            font=ctk.CTkFont(size=11),
            text_color="#cbd5e1",
            anchor="w"
        )
        self.lbl_progress_status.grid(row=0, column=0, sticky="w")

        self.progress_bar = ctk.CTkProgressBar(self.progress_container, height=10, progress_color="#38bdf8")
        self.progress_bar.set(0)
        self.progress_bar.grid(row=1, column=0, pady=(2, 0), sticky="ew")

        # 3. Live Console / Log Box
        self.log_frame = ctk.CTkFrame(self.tab_dashboard, fg_color=("#0f172a", "#0f172a"), corner_radius=8)
        self.log_frame.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="nsew")
        self.log_frame.grid_columnconfigure(0, weight=1)
        self.log_frame.grid_rowconfigure(1, weight=1)

        # Log toolbar
        self.log_toolbar = ctk.CTkFrame(self.log_frame, fg_color="transparent", height=30)
        self.log_toolbar.grid(row=0, column=0, padx=10, pady=(8, 4), sticky="ew")
        self.log_toolbar.grid_columnconfigure(0, weight=1)

        self.lbl_log_title = ctk.CTkLabel(
            self.log_toolbar,
            text="📋 Nhật Ký Hoạt Động Thời Gian Thực (Live Logs)",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#94a3b8"
        )
        self.lbl_log_title.grid(row=0, column=0, sticky="w")

        self.chk_autoscroll = ctk.CTkCheckBox(
            self.log_toolbar,
            text="Tự động cuộn",
            font=ctk.CTkFont(size=11),
            checkbox_width=18,
            checkbox_height=18,
            command=self._toggle_autoscroll
        )
        self.chk_autoscroll.select()
        self.chk_autoscroll.grid(row=0, column=1, padx=(0, 10))

        self.btn_clear_log = ctk.CTkButton(
            self.log_toolbar,
            text="🧹 Xóa Log",
            width=75,
            height=24,
            font=ctk.CTkFont(size=11),
            fg_color="#334155",
            hover_color="#475569",
            command=self._clear_logs
        )
        self.btn_clear_log.grid(row=0, column=2, padx=(0, 5))

        self.btn_export_log = ctk.CTkButton(
            self.log_toolbar,
            text="💾 Xuất Log",
            width=75,
            height=24,
            font=ctk.CTkFont(size=11),
            fg_color="#334155",
            hover_color="#475569",
            command=self._export_logs
        )
        self.btn_export_log.grid(row=0, column=3)

        # Log Textbox
        self.txt_log = ctk.CTkTextbox(
            self.log_frame,
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color="#e2e8f0",
            fg_color="#020617",
            corner_radius=6,
            wrap="char"
        )
        self.txt_log.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")

    def _create_metric_card(self, parent, col, title, initial_val, accent_color):
        card = ctk.CTkFrame(parent, fg_color=("#0f172a", "#0f172a"), corner_radius=8)
        card.grid(row=0, column=col, padx=5, pady=0, sticky="ew")
        card.grid_columnconfigure(0, weight=1)

        lbl_t = ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=10, weight="bold"), text_color="#94a3b8")
        lbl_t.grid(row=0, column=0, padx=10, pady=(8, 0), sticky="w")

        lbl_v = ctk.CTkLabel(card, text=initial_val, font=ctk.CTkFont(size=18, weight="bold"), text_color=accent_color)
        lbl_v.grid(row=1, column=0, padx=10, pady=(0, 8), sticky="w")
        return lbl_v

    # -------------------------------------------------------------
    # TAB 2: CÀI ĐẶT CẤU HÌNH (SETTINGS)
    # -------------------------------------------------------------
    def _build_settings_tab(self):
        self.tab_settings.grid_columnconfigure(0, weight=1)
        self.tab_settings.grid_rowconfigure(0, weight=1)

        # Scrollable container for settings
        self.settings_scroll = ctk.CTkScrollableFrame(self.tab_settings, fg_color="transparent")
        self.settings_scroll.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        self.settings_scroll.grid_columnconfigure(0, weight=1)

        # Section 1: Presets Quick Bar
        self._build_presets_section(self.settings_scroll)

        # Section 2: URL & Video Configuration
        self._build_url_section(self.settings_scroll)

        # Section 3: Interaction & Timing Options
        self._build_timing_section(self.settings_scroll)

        # Section 4: Advanced & Profile Options
        self._build_advanced_section(self.settings_scroll)

        # Bottom Save / Reset Action Bar
        self.action_bar = ctk.CTkFrame(self.tab_settings, fg_color=("#0f172a", "#0f172a"), height=50)
        self.action_bar.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        self.action_bar.grid_columnconfigure(0, weight=1)

        self.btn_save_config = ctk.CTkButton(
            self.action_bar,
            text="💾 Lưu Cấu Hình",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#0284c7",
            hover_color="#0369a1",
            height=36,
            command=self._save_ui_to_config
        )
        self.btn_save_config.grid(row=0, column=1, padx=(0, 10), pady=8)

        self.btn_reset_default = ctk.CTkButton(
            self.action_bar,
            text="🔄 Khôi Phục Mặc Định",
            font=ctk.CTkFont(size=12),
            fg_color="#334155",
            hover_color="#475569",
            height=36,
            command=self._reset_to_default_config
        )
        self.btn_reset_default.grid(row=0, column=2, padx=10, pady=8)

    def _build_presets_section(self, parent):
        frame = ctk.CTkFrame(parent, fg_color=("#0f172a", "#0f172a"), corner_radius=8)
        frame.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        frame.grid_columnconfigure(3, weight=1)

        lbl = ctk.CTkLabel(
            frame, 
            text="⚡ Cấu Hình Nhanh (Presets):", 
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#38bdf8"
        )
        lbl.grid(row=0, column=0, padx=15, pady=10, sticky="w")

        btn_fast = ctk.CTkButton(
            frame,
            text="⚡ Siêu Tốc (Fast React)",
            font=ctk.CTkFont(size=11),
            fg_color="#1e293b",
            hover_color="#334155",
            border_width=1,
            border_color="#38bdf8",
            command=lambda: self._apply_preset("fast")
        )
        btn_fast.grid(row=0, column=1, padx=5, pady=10)

        btn_safe = ctk.CTkButton(
            frame,
            text="🛡️ An Toàn (Mô phỏng thật)",
            font=ctk.CTkFont(size=11),
            fg_color="#1e293b",
            hover_color="#334155",
            border_width=1,
            border_color="#10b981",
            command=lambda: self._apply_preset("safe")
        )
        btn_safe.grid(row=0, column=2, padx=5, pady=10)

        btn_dry = ctk.CTkButton(
            frame,
            text="🔍 Kiểm Thử (Dry-Run)",
            font=ctk.CTkFont(size=11),
            fg_color="#1e293b",
            hover_color="#334155",
            border_width=1,
            border_color="#f59e0b",
            command=lambda: self._apply_preset("dry_run")
        )
        btn_dry.grid(row=0, column=3, padx=5, pady=10, sticky="w")

    def _build_url_section(self, parent):
        frame = ctk.CTkFrame(parent, fg_color=("#0f172a", "#0f172a"), corner_radius=8)
        frame.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        frame.grid_columnconfigure(1, weight=1)

        lbl_sec = ctk.CTkLabel(
            frame,
            text="📍 1. Đường Dẫn UCircle & Video Feed",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#e2e8f0"
        )
        lbl_sec.grid(row=0, column=0, columnspan=2, padx=15, pady=(12, 8), sticky="w")

        # URL Field
        lbl_url = ctk.CTkLabel(frame, text="URL Feed / Circle:", font=ctk.CTkFont(size=12), text_color="#94a3b8")
        lbl_url.grid(row=1, column=0, padx=(15, 10), pady=6, sticky="w")

        self.entry_url = ctk.CTkEntry(
            frame,
            placeholder_text="https://ucircle.net/app/c/...?...v=...",
            font=ctk.CTkFont(size=12),
            height=34
        )
        self.entry_url.grid(row=1, column=1, padx=(0, 15), pady=6, sticky="ew")
        self.entry_url.bind("<KeyRelease>", self._on_url_changed)

        # Extracted Target Video ID
        lbl_vid = ctk.CTkLabel(frame, text="Video ID Mục Tiêu:", font=ctk.CTkFont(size=12), text_color="#94a3b8")
        lbl_vid.grid(row=2, column=0, padx=(15, 10), pady=(0, 12), sticky="w")

        self.entry_video_id = ctk.CTkEntry(
            frame,
            placeholder_text="Tự động bóc tách từ URL (hoặc nhập thủ công)",
            font=ctk.CTkFont(size=12),
            height=34
        )
        self.entry_video_id.grid(row=2, column=1, padx=(0, 15), pady=(0, 12), sticky="ew")

    def _build_timing_section(self, parent):
        frame = ctk.CTkFrame(parent, fg_color=("#0f172a", "#0f172a"), corner_radius=8)
        frame.grid(row=2, column=0, padx=5, pady=5, sticky="ew")
        frame.grid_columnconfigure(1, weight=1)

        lbl_sec = ctk.CTkLabel(
            frame,
            text="⚡ 2. Chế Độ Tương Tác & Thời Gian",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#e2e8f0"
        )
        lbl_sec.grid(row=0, column=0, columnspan=2, padx=15, pady=(12, 8), sticky="w")

        # Mode Selection: React only vs Watch then React
        lbl_mode = ctk.CTkLabel(frame, text="Chế độ chạy:", font=ctk.CTkFont(size=12), text_color="#94a3b8")
        lbl_mode.grid(row=1, column=0, padx=(15, 10), pady=6, sticky="w")

        self.seg_react_mode = ctk.CTkSegmentedButton(
            frame,
            values=["Chỉ Thả Ngũ Hành (Nhanh)", "Xem Video rồi Thả Ngũ Hành"],
            font=ctk.CTkFont(size=12),
            selected_color="#0284c7",
            selected_hover_color="#0369a1",
            command=self._on_react_mode_toggle
        )
        self.seg_react_mode.grid(row=1, column=1, padx=(0, 15), pady=6, sticky="w")

        # Element Selection
        lbl_elem = ctk.CTkLabel(frame, text="Ngũ Hành Lựa Chọn:", font=ctk.CTkFont(size=12), text_color="#94a3b8")
        lbl_elem.grid(row=2, column=0, padx=(15, 10), pady=6, sticky="w")

        self.combo_element = ctk.CTkComboBox(
            frame,
            values=[
                "🎲 Ngẫu nhiên 5 hệ (Shuffle bag)",
                "🔥 Hệ Hỏa (hoa)",
                "🏔️ Hệ Thổ (tho)",
                "⚔️ Hệ Kim (kim)",
                "💧 Hệ Thủy (thuy)",
                "🌲 Hệ Mộc (moc)"
            ],
            font=ctk.CTkFont(size=12),
            height=32,
            width=260
        )
        self.combo_element.grid(row=2, column=1, padx=(0, 15), pady=6, sticky="w")

        # Max Videos
        lbl_max = ctk.CTkLabel(frame, text="Số lượng video tối đa:", font=ctk.CTkFont(size=12), text_color="#94a3b8")
        lbl_max.grid(row=3, column=0, padx=(15, 10), pady=6, sticky="w")

        self.entry_max_videos = ctk.CTkEntry(frame, width=120, height=32, font=ctk.CTkFont(size=12))
        self.entry_max_videos.grid(row=3, column=1, padx=(0, 15), pady=6, sticky="w")

        # Watch Time Range Frame
        self.lbl_watch_time = ctk.CTkLabel(
            frame, text="Thời gian xem (giây):", font=ctk.CTkFont(size=12), text_color="#94a3b8"
        )
        self.lbl_watch_time.grid(row=4, column=0, padx=(15, 10), pady=6, sticky="w")

        self.frame_watch = ctk.CTkFrame(frame, fg_color="transparent")
        self.frame_watch.grid(row=4, column=1, padx=(0, 15), pady=6, sticky="w")

        self.entry_watch_min = ctk.CTkEntry(self.frame_watch, width=60, height=32, font=ctk.CTkFont(size=12))
        self.entry_watch_min.grid(row=0, column=0, padx=(0, 5))
        ctk.CTkLabel(self.frame_watch, text="đến", font=ctk.CTkFont(size=12)).grid(row=0, column=1, padx=5)
        self.entry_watch_max = ctk.CTkEntry(self.frame_watch, width=60, height=32, font=ctk.CTkFont(size=12))
        self.entry_watch_max.grid(row=0, column=2, padx=(5, 0))

        # Delay Range Frame
        lbl_delay = ctk.CTkLabel(frame, text="Độ trễ chuyển video (s):", font=ctk.CTkFont(size=12), text_color="#94a3b8")
        lbl_delay.grid(row=5, column=0, padx=(15, 10), pady=(6, 12), sticky="w")

        self.frame_delay = ctk.CTkFrame(frame, fg_color="transparent")
        self.frame_delay.grid(row=5, column=1, padx=(0, 15), pady=(6, 12), sticky="w")

        self.entry_delay_min = ctk.CTkEntry(self.frame_delay, width=60, height=32, font=ctk.CTkFont(size=12))
        self.entry_delay_min.grid(row=0, column=0, padx=(0, 5))
        ctk.CTkLabel(self.frame_delay, text="đến", font=ctk.CTkFont(size=12)).grid(row=0, column=1, padx=5)
        self.entry_delay_max = ctk.CTkEntry(self.frame_delay, width=60, height=32, font=ctk.CTkFont(size=12))
        self.entry_delay_max.grid(row=0, column=2, padx=(5, 0))

    def _build_advanced_section(self, parent):
        frame = ctk.CTkFrame(parent, fg_color=("#0f172a", "#0f172a"), corner_radius=8)
        frame.grid(row=3, column=0, padx=5, pady=5, sticky="ew")
        frame.grid_columnconfigure(1, weight=1)

        lbl_sec = ctk.CTkLabel(
            frame,
            text="🛡️ 3. Tùy Chọn Nâng Cao & Hồ Sơ Trình Duyệt",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#e2e8f0"
        )
        lbl_sec.grid(row=0, column=0, columnspan=2, padx=15, pady=(12, 8), sticky="w")

        # Switches Frame
        self.switches_frame = ctk.CTkFrame(frame, fg_color="transparent")
        self.switches_frame.grid(row=1, column=0, columnspan=2, padx=15, pady=6, sticky="w")

        self.sw_dry_run = ctk.CTkSwitch(
            self.switches_frame,
            text="Chế độ Dry-Run (Chỉ kiểm thử, không thả ngũ hành thật)",
            font=ctk.CTkFont(size=12),
            progress_color="#f59e0b"
        )
        self.sw_dry_run.grid(row=0, column=0, padx=(0, 20), pady=4)

        self.sw_headless = ctk.CTkSwitch(
            self.switches_frame,
            text="Chế độ Headless (Ẩn giao diện Chromium)",
            font=ctk.CTkFont(size=12),
            progress_color="#0284c7"
        )
        self.sw_headless.grid(row=0, column=1, padx=10, pady=4)

        # Profile Directory
        lbl_prof = ctk.CTkLabel(frame, text="Thư mục Profile:", font=ctk.CTkFont(size=12), text_color="#94a3b8")
        lbl_prof.grid(row=2, column=0, padx=(15, 10), pady=(6, 12), sticky="w")

        self.prof_container = ctk.CTkFrame(frame, fg_color="transparent")
        self.prof_container.grid(row=2, column=1, padx=(0, 15), pady=(6, 12), sticky="ew")
        self.prof_container.grid_columnconfigure(0, weight=1)

        self.entry_profile_dir = ctk.CTkEntry(self.prof_container, font=ctk.CTkFont(size=12), height=32)
        self.entry_profile_dir.grid(row=0, column=0, padx=(0, 8), sticky="ew")

        self.btn_open_profile_dir = ctk.CTkButton(
            self.prof_container,
            text="📁 Mở Thư Mục",
            width=100,
            height=32,
            font=ctk.CTkFont(size=11),
            fg_color="#334155",
            hover_color="#475569",
            command=self._open_profile_folder
        )
        self.btn_open_profile_dir.grid(row=0, column=1)

    # -------------------------------------------------------------
    # TAB 3: LỊCH SỬ & ẢNH LỖI (HISTORY & SCREENSHOTS)
    # -------------------------------------------------------------
    def _build_history_tab(self):
        self.tab_history.grid_columnconfigure(0, weight=1)
        self.tab_history.grid_rowconfigure(1, weight=1)

        # Toolbar
        self.hist_toolbar = ctk.CTkFrame(self.tab_history, fg_color=("#0f172a", "#0f172a"), height=40)
        self.hist_toolbar.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        self.hist_toolbar.grid_columnconfigure(0, weight=1)

        lbl_title = ctk.CTkLabel(
            self.hist_toolbar,
            text="📸 Danh Sách Ảnh Chụp Sự Cố (Error Screenshots)",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#94a3b8"
        )
        lbl_title.grid(row=0, column=0, padx=15, pady=8, sticky="w")

        btn_refresh = ctk.CTkButton(
            self.hist_toolbar,
            text="🔄 Làm Mới",
            width=80,
            height=28,
            font=ctk.CTkFont(size=11),
            fg_color="#334155",
            hover_color="#475569",
            command=self._refresh_screenshots_list
        )
        btn_refresh.grid(row=0, column=1, padx=5, pady=8)

        btn_open_shots = ctk.CTkButton(
            self.hist_toolbar,
            text="📁 Mở Thư Mục Screenshots",
            width=150,
            height=28,
            font=ctk.CTkFont(size=11),
            fg_color="#334155",
            hover_color="#475569",
            command=self._open_screenshots_folder
        )
        btn_open_shots.grid(row=0, column=2, padx=5, pady=8)

        btn_open_logs = ctk.CTkButton(
            self.hist_toolbar,
            text="📄 Mở File Log",
            width=100,
            height=28,
            font=ctk.CTkFont(size=11),
            fg_color="#334155",
            hover_color="#475569",
            command=self._open_log_file
        )
        btn_open_logs.grid(row=0, column=3, padx=(5, 10), pady=8)

        # Screenshots Scrollable List
        self.screenshots_scroll = ctk.CTkScrollableFrame(self.tab_history, fg_color=("#0f172a", "#0f172a"))
        self.screenshots_scroll.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
        self.screenshots_scroll.grid_columnconfigure(0, weight=1)

    # -------------------------------------------------------------
    # HELPER LOGIC: CONFIG & UI BINDING
    # -------------------------------------------------------------
    def _load_config_to_ui(self):
        """Đưa toàn bộ dữ liệu cấu hình vào UI Controls"""
        cfg = self.config
        self.entry_url.delete(0, "end")
        self.entry_url.insert(0, cfg.ucircle_url)

        self.entry_video_id.delete(0, "end")
        self.entry_video_id.insert(0, cfg.target_video_id or "")

        if cfg.react_only:
            self.seg_react_mode.set("Chỉ Thả Ngũ Hành (Nhanh)")
        else:
            self.seg_react_mode.set("Xem Video rồi Thả Ngũ Hành")

        # Element combo
        elem_map = {
            "shuffle": "🎲 Ngẫu nhiên 5 hệ (Shuffle bag)",
            "hoa": "🔥 Hệ Hỏa (hoa)",
            "tho": "🏔️ Hệ Thổ (tho)",
            "kim": "⚔️ Hệ Kim (kim)",
            "thuy": "💧 Hệ Thủy (thuy)",
            "moc": "🌲 Hệ Mộc (moc)"
        }
        self.combo_element.set(elem_map.get(cfg.element_mode, elem_map["shuffle"]))

        self.entry_max_videos.delete(0, "end")
        self.entry_max_videos.insert(0, str(cfg.max_videos))

        self.entry_watch_min.delete(0, "end")
        self.entry_watch_min.insert(0, str(cfg.watch_min_seconds))

        self.entry_watch_max.delete(0, "end")
        self.entry_watch_max.insert(0, str(cfg.watch_max_seconds))

        self.entry_delay_min.delete(0, "end")
        self.entry_delay_min.insert(0, str(cfg.action_delay_min))

        self.entry_delay_max.delete(0, "end")
        self.entry_delay_max.insert(0, str(cfg.action_delay_max))

        if cfg.dry_run:
            self.sw_dry_run.select()
        else:
            self.sw_dry_run.deselect()

        if cfg.headless:
            self.sw_headless.select()
        else:
            self.sw_headless.deselect()

        self.entry_profile_dir.delete(0, "end")
        self.entry_profile_dir.insert(0, cfg.profile_dir)

        self._on_react_mode_toggle(self.seg_react_mode.get())

    def _get_ui_config(self) -> AppConfig:
        """Lấy cấu hình hiện tại từ các trường trên giao diện"""
        elem_val = self.combo_element.get()
        elem_mode = "shuffle"
        if "hoa" in elem_val.lower():
            elem_mode = "hoa"
        elif "tho" in elem_val.lower():
            elem_mode = "tho"
        elif "kim" in elem_val.lower():
            elem_mode = "kim"
        elif "thuy" in elem_val.lower():
            elem_mode = "thuy"
        elif "moc" in elem_val.lower():
            elem_mode = "moc"

        try:
            max_v = int(self.entry_max_videos.get().strip())
        except ValueError:
            max_v = 1000

        try:
            w_min = int(self.entry_watch_min.get().strip())
        except ValueError:
            w_min = 2

        try:
            w_max = int(self.entry_watch_max.get().strip())
        except ValueError:
            w_max = 3

        try:
            d_min = int(self.entry_delay_min.get().strip())
        except ValueError:
            d_min = 1

        try:
            d_max = int(self.entry_delay_max.get().strip())
        except ValueError:
            d_max = 3

        return AppConfig(
            ucircle_url=self.entry_url.get().strip(),
            target_video_id=self.entry_video_id.get().strip(),
            react_only=(self.seg_react_mode.get() == "Chỉ Thả Ngũ Hành (Nhanh)"),
            watch_min_seconds=w_min,
            watch_max_seconds=w_max,
            action_delay_min=d_min,
            action_delay_max=d_max,
            max_videos=max_v,
            headless=bool(self.sw_headless.get()),
            dry_run=bool(self.sw_dry_run.get()),
            profile_dir=self.entry_profile_dir.get().strip() or "./browser-profile",
            element_mode=elem_mode
        )

    def _on_url_changed(self, event=None):
        """Khi người dùng dán hoặc gõ URL, tự động trích xuất Video ID"""
        raw_url = self.entry_url.get().strip()
        details = extract_url_details(raw_url)
        if details["video_id"]:
            self.entry_video_id.delete(0, "end")
            self.entry_video_id.insert(0, details["video_id"])

    def _on_react_mode_toggle(self, value):
        """Bật/tắt các ô thời gian xem video tùy theo chế độ"""
        if value == "Chỉ Thả Ngũ Hành (Nhanh)":
            self.entry_watch_min.configure(state="disabled", fg_color="#1e293b")
            self.entry_watch_max.configure(state="disabled", fg_color="#1e293b")
            self.lbl_watch_time.configure(text_color="#64748b")
        else:
            self.entry_watch_min.configure(state="normal", fg_color="#0f172a")
            self.entry_watch_max.configure(state="normal", fg_color="#0f172a")
            self.lbl_watch_time.configure(text_color="#94a3b8")

    def _apply_preset(self, preset_name: str):
        presets = get_presets()
        if preset_name in presets:
            preset = presets[preset_name]
            # Giữ lại URL và profile_dir hiện tại
            preset.ucircle_url = self.entry_url.get().strip()
            preset.target_video_id = self.entry_video_id.get().strip()
            preset.profile_dir = self.entry_profile_dir.get().strip()
            self.config = preset
            self._load_config_to_ui()
            self._append_log(f"Đã áp dụng cấu hình Preset: [{preset_name.upper()}]", "INFO")

    def _save_ui_to_config(self):
        new_cfg = self._get_ui_config()
        errors = validate_config(new_cfg)
        if errors:
            err_text = "\n• " + "\n• ".join(errors)
            self._append_log(f"Lỗi kiểm tra cấu hình:{err_text}", "ERROR")
            return

        self.config = new_cfg
        if save_config(self.config):
            self._append_log("Đã lưu cấu hình thành công vào file 'config.json'!", "INFO")
        else:
            self._append_log("Lỗi khi lưu cấu hình vào file 'config.json'.", "ERROR")

    def _reset_to_default_config(self):
        self.config = AppConfig()
        url_info = extract_url_details(self.config.ucircle_url)
        if url_info["video_id"]:
            self.config.target_video_id = url_info["video_id"]
        save_config(self.config)
        self._load_config_to_ui()
        self._append_log("Đã khôi phục cấu hình về mặc định!", "INFO")

    # -------------------------------------------------------------
    # LOGGING & UI UPDATES (THREAD-SAFE)
    # -------------------------------------------------------------
    def _append_log(self, text: str, level: str = "INFO"):
        self.after(0, self._do_append_log, text, level)

    def _do_append_log(self, text: str, level: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = f"[{timestamp}] [{level}] "
        full_line = f"{prefix}{text}\n"

        self.txt_log.insert("end", full_line)
        if self.auto_scroll_log:
            self.txt_log.see("end")

    def _clear_logs(self):
        self.txt_log.delete("1.0", "end")

    def _export_logs(self):
        try:
            os.makedirs("logs", exist_ok=True)
            export_path = f"logs/export_{int(time.time())}.txt"
            content = self.txt_log.get("1.0", "end")
            with open(export_path, "w", encoding="utf-8") as f:
                f.write(content)
            self._append_log(f"Đã xuất log ra file: {export_path}", "INFO")
        except Exception as e:
            self._append_log(f"Không thể xuất file log: {e}", "ERROR")

    def _toggle_autoscroll(self):
        self.auto_scroll_log = bool(self.chk_autoscroll.get())

    def _update_status_badge(self, text: str, bg_color: str, fg_color: str):
        self.after(0, lambda: self.status_badge.configure(text=text, fg_color=bg_color, text_color=fg_color))

    def _update_progress_ui(self, current: int, total: int, stats: Dict[str, Any]):
        def update():
            # Update metrics cards
            self.card_total.configure(text=f"{current} / {total}")
            self.card_reacted.configure(text=str(stats.get("reacted", 0)))
            self.card_skipped.configure(text=str(stats.get("skipped", 0)))

            elapsed = stats.get("elapsed_seconds", 0)
            hours, remainder = divmod(elapsed, 3600)
            mins, secs = divmod(remainder, 60)
            self.card_time.configure(text=f"{hours:02d}:{mins:02d}:{secs:02d}")

            # Progress bar
            progress_ratio = (current / total) if total > 0 else 0
            self.progress_bar.set(progress_ratio)
            percent = int(progress_ratio * 100)
            self.lbl_progress_status.configure(text=f"Tiến độ: {current}/{total} ({percent}%)")

        self.after(0, update)

    # -------------------------------------------------------------
    # RUNNER CONTROL (START / PAUSE / STOP)
    # -------------------------------------------------------------
    def _on_start_clicked(self):
        # Lấy và kiểm tra cấu hình mới nhất từ UI
        current_cfg = self._get_ui_config()
        errors = validate_config(current_cfg)
        if errors:
            self._append_log("Không thể bắt đầu. Vui lòng sửa các lỗi cấu hình:\n• " + "\n• ".join(errors), "ERROR")
            self.tabview.set("⚙️ Cài Đặt Cấu Hình")
            return

        self.config = current_cfg
        save_config(self.config)

        # Chuyển trạng thái UI sang Đang chạy
        self.is_running = True
        self.btn_start.configure(state="disabled")
        self.btn_pause.configure(state="normal", text="⏸ Tạm Dừng")
        self.btn_stop.configure(state="normal")
        self.btn_open_browser.configure(state="disabled")
        self._update_status_badge("● ĐANG CHẠY", "#0369a1", "#38bdf8")

        # Khởi tạo engine
        self.engine = AutomationEngine(self.config)
        self.engine.on_log = lambda msg, lvl: self._append_log(msg, lvl)
        self.engine.on_status_change = lambda status: self.after(0, lambda: self.lbl_progress_status.configure(text=status))
        self.engine.on_progress = lambda cur, tot, st: self._update_progress_ui(cur, tot, st)
        self.engine.on_finish = self._on_engine_finished
        self.engine.on_error = lambda err: self._append_log(f"Lỗi: {err}", "ERROR")

        # Khởi động thread nền
        self.worker_thread = threading.Thread(target=self._run_engine_thread, daemon=True)
        self.worker_thread.start()

    def _run_engine_thread(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.engine.run())
        finally:
            loop.close()

    def _on_pause_clicked(self):
        if not self.engine:
            return

        if not self.engine.is_paused:
            self.engine.request_pause()
            self.btn_pause.configure(text="▶ Tiếp Tục", fg_color="#10b981", hover_color="#059669")
            self._update_status_badge("● TẠM DỪNG", "#78350f", "#f59e0b")
        else:
            self.engine.request_resume()
            self.btn_pause.configure(text="⏸ Tạm Dừng", fg_color="#f59e0b", hover_color="#d97706")
            self._update_status_badge("● ĐANG CHẠY", "#0369a1", "#38bdf8")

    def _on_stop_clicked(self):
        if self.engine and self.is_running:
            self.btn_stop.configure(state="disabled")
            self._update_status_badge("● ĐANG DỪNG...", "#7f1d1d", "#ef4444")
            self.engine.request_stop()

    def _on_engine_finished(self, stats: Dict[str, Any]):
        def handle_finish():
            self.is_running = False
            self.btn_start.configure(state="normal")
            self.btn_pause.configure(state="disabled", text="⏸ Tạm Dừng", fg_color="#f59e0b")
            self.btn_stop.configure(state="disabled")
            self.btn_open_browser.configure(state="normal")
            self._update_status_badge("● HOÀN THÀNH", "#064e3b", "#10b981")
            self._refresh_screenshots_list()
        self.after(0, handle_finish)

    def _open_browser_manual(self):
        """Mở browser profile độc lập để người dùng đăng nhập thủ công"""
        def run_browser():
            self._append_log("Đang mở trình duyệt để đăng nhập thủ công...", "INFO")
            async def _launch():
                async with async_playwright() as p:
                    browser = await launch_browser(p, headless=False, profile_dir=self.config.profile_dir)
                    page = browser.pages[0] if browser.pages else await browser.new_page()
                    await page.goto(self.config.ucircle_url)
                    self._append_log("Trình duyệt đã mở. Bạn hãy đăng nhập, sau đó đóng trình duyệt khi hoàn tất.", "INFO")
                    # Chờ browser đóng
                    while browser.is_connected():
                        await asyncio.sleep(1)
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(_launch())
            except Exception as e:
                self._append_log(f"Lỗi mở trình duyệt thủ công: {e}", "ERROR")
            finally:
                loop.close()

        threading.Thread(target=run_browser, daemon=True).start()

    # -------------------------------------------------------------
    # SCREENSHOTS & DIRECTORY UTILS
    # -------------------------------------------------------------
    def _refresh_screenshots_list(self):
        for widget in self.screenshots_scroll.winfo_children():
            widget.destroy()

        shots_dir = "logs/screenshots"
        if not os.path.exists(shots_dir):
            os.makedirs(shots_dir, exist_ok=True)

        files = sorted(
            [f for f in os.listdir(shots_dir) if f.endswith(".png") or f.endswith(".jpg")],
            reverse=True
        )

        if not files:
            lbl = ctk.CTkLabel(
                self.screenshots_scroll,
                text="Chưa có ảnh chụp sự cố nào. Hệ thống hoạt động tốt!",
                font=ctk.CTkFont(size=12),
                text_color="#94a3b8"
            )
            lbl.grid(row=0, column=0, padx=20, pady=20)
            return

        for idx, filename in enumerate(files[:30]):
            filepath = os.path.join(shots_dir, filename)
            row_frame = ctk.CTkFrame(self.screenshots_scroll, fg_color=("#1e293b", "#1e293b"), corner_radius=6)
            row_frame.grid(row=idx, column=0, padx=5, pady=4, sticky="ew")
            row_frame.grid_columnconfigure(1, weight=1)

            lbl_f = ctk.CTkLabel(row_frame, text=f"📷 {filename}", font=ctk.CTkFont(size=12), text_color="#e2e8f0")
            lbl_f.grid(row=0, column=0, padx=10, pady=8, sticky="w")

            btn_view = ctk.CTkButton(
                row_frame,
                text="Xem Ảnh",
                width=80,
                height=26,
                font=ctk.CTkFont(size=11),
                fg_color="#0284c7",
                hover_color="#0369a1",
                command=lambda p=filepath: self._open_file(p)
            )
            btn_view.grid(row=0, column=2, padx=10, pady=8)

    def _open_file(self, filepath: str):
        if os.path.exists(filepath):
            if sys.platform == "win32":
                os.startfile(os.path.abspath(filepath))
            else:
                subprocess.Popen(["xdg-open", filepath])

    def _open_screenshots_folder(self):
        shots_dir = os.path.abspath("logs/screenshots")
        os.makedirs(shots_dir, exist_ok=True)
        self._open_file(shots_dir)

    def _open_profile_folder(self):
        prof_dir = os.path.abspath(self.entry_profile_dir.get().strip() or "./browser-profile")
        os.makedirs(prof_dir, exist_ok=True)
        self._open_file(prof_dir)

    def _open_log_file(self):
        log_path = os.path.abspath("logs/session.log")
        if not os.path.exists(log_path):
            os.makedirs("logs", exist_ok=True)
            with open(log_path, "w", encoding="utf-8") as f:
                f.write("Log initialized.\n")
        self._open_file(log_path)

    def _on_close(self):
        if self.is_running and self.engine:
            self.engine.request_stop()
        self.destroy()


def main():
    os.makedirs("logs/screenshots", exist_ok=True)
    app = UCircleAutomationGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
