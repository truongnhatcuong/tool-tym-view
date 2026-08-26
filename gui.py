import os
import sys
import time
import asyncio
import threading
import subprocess
from datetime import datetime
from typing import Optional, Dict, Any, List

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
from profile_manager import (
    ProfileConfig,
    ProxyConfig,
    load_profiles,
    save_profiles,
    create_profile,
    delete_profile,
    update_profile,
    get_enabled_profiles,
)
from automation.engine import AutomationEngine
from automation.batch_engine import BatchEngine
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
        self.geometry("1100x780")
        self.minsize(960, 700)

        # Cấu hình hiện tại
        self.config = load_config()
        self.profiles: List[ProfileConfig] = load_profiles()
        self.engine: Optional[AutomationEngine] = None
        self.batch_engine: Optional[BatchEngine] = None
        self.worker_thread: Optional[threading.Thread] = None
        self.is_running = False
        self.auto_scroll_log = True
        self.start_timestamp = 0.0

        # UI Components Setup
        self._setup_ui()
        self._load_config_to_ui()
        self._refresh_screenshots_list()
        self._refresh_profile_list()

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
            text="Tự động tương tác Ngũ Hành & Video Feed Wavee | Multi-Profile & Batch Run",
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
        self.tab_settings = self.tabview.add("⚙️ Cấu Hình & Profile")
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
            text="▶ Bắt Đầu Chạy (Tất Cả Profile Bật)",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#10b981",
            hover_color="#059669",
            text_color="#ffffff",
            height=38,
            command=self._on_batch_start
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
            command=self._on_batch_stop
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
        self.tab_settings.grid_rowconfigure(0, weight=1)  # settings_scroll ở row=0 → cần weight ở đây

        # Scrollable container for settings + profiles
        self.settings_scroll = ctk.CTkScrollableFrame(self.tab_settings, fg_color="transparent")
        self.settings_scroll.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        self.settings_scroll.grid_columnconfigure(0, weight=1)

        # Section 1: Profile Manager (lên đầu)
        self._build_profiles_section(self.settings_scroll)

        # Section 3: Advanced & Global Options
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
    # PROFILE MANAGER SECTION (embedded in Settings Tab)
    # -------------------------------------------------------------
    def _build_profiles_section(self, parent):
        """Xây dựng phần Quản lý Profile bên trong tab Cấu Hình."""
        # Section separator label
        sep = ctk.CTkLabel(
            parent,
            text="👤 4. Quản Lý Profile (Tài Khoản)",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#e2e8f0"
        )
        sep.grid(row=0, column=0, padx=20, pady=(12, 4), sticky="w")

        outer = ctk.CTkFrame(parent, fg_color=("#0f172a", "#0f172a"), corner_radius=8)
        outer.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
        outer.grid_columnconfigure(0, weight=1)
        outer.grid_rowconfigure(1, weight=1)

        # ── Top Toolbar ──────────────────────────────────────────
        toolbar = ctk.CTkFrame(outer, fg_color=("#1e293b", "#1e293b"), height=50)
        toolbar.grid(row=0, column=0, padx=0, pady=(0, 0), sticky="ew")
        toolbar.grid_columnconfigure(5, weight=1)

        self.btn_add_profile = ctk.CTkButton(
            toolbar, text="➕ Thêm Profile",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#10b981", hover_color="#059669",
            height=32, width=120,
            command=self._on_add_profile
        )
        self.btn_add_profile.grid(row=0, column=0, padx=(10, 5), pady=8)

        self.btn_edit_profile = ctk.CTkButton(
            toolbar, text="✏️ Sửa",
            font=ctk.CTkFont(size=12),
            fg_color="#0284c7", hover_color="#0369a1",
            height=32, width=80,
            state="disabled",
            command=self._on_edit_profile
        )
        self.btn_edit_profile.grid(row=0, column=1, padx=5, pady=8)

        self.btn_delete_profile = ctk.CTkButton(
            toolbar, text="🗑️ Xóa",
            font=ctk.CTkFont(size=12),
            fg_color="#ef4444", hover_color="#dc2626",
            height=32, width=80,
            state="disabled",
            command=self._on_delete_profile
        )
        self.btn_delete_profile.grid(row=0, column=2, padx=5, pady=8)

        self.btn_first_login = ctk.CTkButton(
            toolbar, text="🔑 Đăng Nhập Lần Đầu",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#8b5cf6", hover_color="#7c3aed",
            height=32, width=150,
            command=self._on_first_login
        )
        self.btn_first_login.grid(row=0, column=3, padx=5, pady=8)

        self.btn_logout_session = ctk.CTkButton(
            toolbar, text="🚪 Đăng Xuất Session",
            font=ctk.CTkFont(size=12),
            fg_color="#ef4444", hover_color="#dc2626",
            height=32, width=140,
            command=self._on_logout_session
        )
        self.btn_logout_session.grid(row=0, column=4, padx=5, pady=8)

        self.btn_login_profile = ctk.CTkButton(
            toolbar, text="🌐 Đăng Nhập Profile",
            font=ctk.CTkFont(size=12),
            fg_color="#334155", hover_color="#475569",
            height=32, width=140,
            state="disabled",
            command=self._on_login_profile
        )
        self.btn_login_profile.grid(row=0, column=5, padx=5, pady=8)

        # ── Profile List ──────────────────────────────────────────
        self.profiles_scroll = ctk.CTkFrame(
            outer,
            fg_color=("#0a0f1e", "#0a0f1e"),
            corner_radius=8
        )
        self.profiles_scroll.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        self.profiles_scroll.grid_columnconfigure(0, weight=1)

        # Column Headers
        self._build_profile_list_header()

        # ── Batch Progress Panel ────────────────────────────────────
        self.batch_progress_frame = ctk.CTkFrame(
            outer, fg_color=("#0f172a", "#0f172a"), corner_radius=8, height=100
        )
        self.batch_progress_frame.grid(row=2, column=0, padx=5, pady=(0, 5), sticky="ew")
        self.batch_progress_frame.grid_columnconfigure(0, weight=1)
        self.batch_progress_frame.grid_propagate(False)

        self._build_batch_progress_panel()

        # Tracking selected profile
        self._selected_profile_id: Optional[str] = None
        self._profile_row_frames: Dict[str, ctk.CTkFrame] = {}

    # Keep old _build_profiles_tab as no-op to avoid errors if referenced
    def _build_profiles_tab(self):
        pass




    def _build_profile_list_header(self):
        """Xây dựng hàng tiêu đề cột cho bảng profile."""
        header = ctk.CTkFrame(self.profiles_scroll, fg_color=("#1e293b", "#1e293b"), corner_radius=6)
        header.grid(row=0, column=0, padx=5, pady=(5, 2), sticky="ew")
        header.grid_columnconfigure(2, weight=1)
        header.grid_columnconfigure(3, weight=1)

        cols = [
            ("Bật", 40), ("Tên Profile", 150), ("URL / Video ID", 0),
            ("Thư mục Profile", 0), ("Videos", 70), ("Proxy", 120), ("Ghi chú", 120)
        ]
        for i, (col_name, col_w) in enumerate(cols):
            kwargs = {"weight": 1} if col_w == 0 else {}
            if col_w:
                header.grid_columnconfigure(i, minsize=col_w)
            lbl = ctk.CTkLabel(
                header, text=col_name,
                font=ctk.CTkFont(size=10, weight="bold"),
                text_color="#64748b"
            )
            lbl.grid(row=0, column=i, padx=8, pady=6, sticky="w")

    def _build_batch_progress_panel(self):
        """Xây dựng panel hiển thị tiến độ Batch Run."""
        # Row 0: label + profile counter
        lbl_batch = ctk.CTkLabel(
            self.batch_progress_frame,
            text="⚡ BATCH RUN TIẾN ĐỘ",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#a855f7"
        )
        lbl_batch.grid(row=0, column=0, padx=15, pady=(8, 2), sticky="w")

        self.lbl_batch_profile_counter = ctk.CTkLabel(
            self.batch_progress_frame,
            text="Chưa chạy",
            font=ctk.CTkFont(size=11),
            text_color="#cbd5e1"
        )
        self.lbl_batch_profile_counter.grid(row=0, column=1, padx=10, pady=(8, 2), sticky="w")

        self.lbl_batch_stats = ctk.CTkLabel(
            self.batch_progress_frame,
            text="Reacted: 0  |  Skipped: 0  |  Lỗi: 0",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8"
        )
        self.lbl_batch_stats.grid(row=0, column=2, padx=10, pady=(8, 2), sticky="w")

        # Row 1: Progress bars
        pbar_frame = ctk.CTkFrame(self.batch_progress_frame, fg_color="transparent")
        pbar_frame.grid(row=1, column=0, columnspan=3, padx=15, pady=(2, 8), sticky="ew")
        pbar_frame.grid_columnconfigure(1, weight=1)
        pbar_frame.grid_columnconfigure(3, weight=1)

        ctk.CTkLabel(pbar_frame, text="Profile:", font=ctk.CTkFont(size=10), text_color="#64748b").grid(row=0, column=0, padx=(0, 5))
        self.batch_profile_bar = ctk.CTkProgressBar(pbar_frame, height=8, progress_color="#a855f7")
        self.batch_profile_bar.set(0)
        self.batch_profile_bar.grid(row=0, column=1, sticky="ew", padx=(0, 20))

        ctk.CTkLabel(pbar_frame, text="Video:", font=ctk.CTkFont(size=10), text_color="#64748b").grid(row=0, column=2, padx=(0, 5))
        self.batch_video_bar = ctk.CTkProgressBar(pbar_frame, height=8, progress_color="#38bdf8")
        self.batch_video_bar.set(0)
        self.batch_video_bar.grid(row=0, column=3, sticky="ew")

    # ── Profile List Rendering ──────────────────────────────────────
    def _refresh_profile_list(self):
        """Vẽ lại toàn bộ danh sách profile."""
        # Xóa tất cả các hàng cũ (trừ header ở row 0)
        for widget in self.profiles_scroll.winfo_children():
            info = widget.grid_info()
            if info.get("row", 0) > 0:
                widget.destroy()

        self._profile_row_frames = {}

        if not self.profiles:
            empty_lbl = ctk.CTkLabel(
                self.profiles_scroll,
                text="Chưa có profile nào. Nhấn '➕ Thêm Profile' để tạo tài khoản mới.",
                font=ctk.CTkFont(size=12),
                text_color="#64748b"
            )
            empty_lbl.grid(row=1, column=0, padx=20, pady=30)
            return

        for idx, profile in enumerate(self.profiles):
            self._render_profile_row(idx + 1, profile)

    def _render_profile_row(self, row_idx: int, profile: ProfileConfig):
        """Vẽ một hàng profile trong bảng danh sách."""
        bg = "#1e293b" if row_idx % 2 == 0 else "#0f172a"
        row = ctk.CTkFrame(self.profiles_scroll, fg_color=(bg, bg), corner_radius=6)
        row.grid(row=row_idx, column=0, padx=5, pady=2, sticky="ew")
        row.grid_columnconfigure(2, weight=1)
        row.grid_columnconfigure(3, weight=1)

        self._profile_row_frames[profile.id] = row

        # Col 0: Enable/Disable switch
        sw_var = ctk.BooleanVar(value=profile.enabled)
        sw = ctk.CTkSwitch(
            row, text="", width=46, height=22,
            progress_color="#10b981",
            variable=sw_var,
            command=lambda p=profile, v=sw_var: self._on_toggle_profile(p, v)
        )
        if profile.enabled:
            sw.select()
        else:
            sw.deselect()
        sw.grid(row=0, column=0, padx=(10, 5), pady=8)

        # Col 1: Name
        lbl_name = ctk.CTkLabel(
            row, text=profile.name,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#e2e8f0", anchor="w", width=145
        )
        lbl_name.grid(row=0, column=1, padx=5, pady=8, sticky="w")

        # Col 2: URL (truncated)
        url_short = profile.ucircle_url
        if len(url_short) > 45:
            url_short = url_short[:42] + "..."
        vid_short = profile.target_video_id[:16] + "..." if len(profile.target_video_id) > 16 else profile.target_video_id
        lbl_url = ctk.CTkLabel(
            row, text=f"{url_short}\n📹 {vid_short}",
            font=ctk.CTkFont(size=10),
            text_color="#94a3b8", anchor="w", justify="left"
        )
        lbl_url.grid(row=0, column=2, padx=5, pady=4, sticky="w")

        # Col 3: Profile dir
        dir_short = profile.profile_dir
        if len(dir_short) > 35:
            dir_short = "..." + dir_short[-32:]
        lbl_dir = ctk.CTkLabel(
            row, text=dir_short,
            font=ctk.CTkFont(size=10),
            text_color="#64748b", anchor="w"
        )
        lbl_dir.grid(row=0, column=3, padx=5, pady=8, sticky="w")

        # Col 4: Max videos
        lbl_videos = ctk.CTkLabel(
            row, text=str(profile.max_videos),
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#f59e0b", width=65
        )
        lbl_videos.grid(row=0, column=4, padx=5, pady=8)

        # Col 5: Proxy status
        proxy_text = profile.get_proxy_display() if profile.proxy and profile.proxy.is_valid() else "—"
        proxy_color = "#10b981" if profile.proxy and profile.proxy.is_valid() else "#64748b"
        lbl_proxy = ctk.CTkLabel(
            row, text=proxy_text,
            font=ctk.CTkFont(size=10),
            text_color=proxy_color, width=115
        )
        lbl_proxy.grid(row=0, column=5, padx=5, pady=8)

        # Col 6: Notes
        notes_short = (profile.notes[:20] + "...") if len(profile.notes) > 20 else profile.notes
        lbl_notes = ctk.CTkLabel(
            row, text=notes_short or "—",
            font=ctk.CTkFont(size=10),
            text_color="#64748b", width=115
        )
        lbl_notes.grid(row=0, column=6, padx=5, pady=8)

        # Click row to select
        for widget in (row, lbl_name, lbl_url, lbl_dir, lbl_videos, lbl_proxy, lbl_notes):
            widget.bind("<Button-1>", lambda e, pid=profile.id: self._select_profile(pid))

    def _select_profile(self, profile_id: str):
        """Chọn một profile trong danh sách."""
        # Bỏ highlight cũ
        if self._selected_profile_id and self._selected_profile_id in self._profile_row_frames:
            old_frame = self._profile_row_frames[self._selected_profile_id]
            try:
                old_frame.configure(border_width=0)
            except Exception:
                pass

        self._selected_profile_id = profile_id
        # Highlight mới
        if profile_id in self._profile_row_frames:
            self._profile_row_frames[profile_id].configure(border_width=2, border_color="#0284c7")

        # Bật các nút hành động
        self.btn_edit_profile.configure(state="normal")
        self.btn_delete_profile.configure(state="normal")
        self.btn_login_profile.configure(state="normal")

    def _on_toggle_profile(self, profile: ProfileConfig, var: ctk.BooleanVar):
        """Bật/tắt profile trong danh sách."""
        profile.enabled = var.get()
        save_profiles(self.profiles)

    # ── Profile CRUD ────────────────────────────────────────────────
    def _on_add_profile(self):
        new_p = create_profile(name=f"Profile {len(self.profiles) + 1}")
        self._show_profile_dialog(new_p, is_new=True)

    def _on_edit_profile(self):
        if not self._selected_profile_id:
            return
        profile = next((p for p in self.profiles if p.id == self._selected_profile_id), None)
        if profile:
            self._show_profile_dialog(profile, is_new=False)

    def _on_delete_profile(self):
        if not self._selected_profile_id:
            return
        profile = next((p for p in self.profiles if p.id == self._selected_profile_id), None)
        if not profile:
            return
        # Xác nhận xóa
        dialog = ctk.CTkToplevel(self)
        dialog.title("Xác Nhận Xóa")
        dialog.geometry("400x160")
        dialog.grab_set()
        dialog.resizable(False, False)

        ctk.CTkLabel(
            dialog,
            text=f"Bạn có chắc muốn xóa profile\n「{profile.name}」?",
            font=ctk.CTkFont(size=13),
            text_color="#e2e8f0"
        ).pack(pady=(20, 10))

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=10)

        def do_delete():
            self.profiles = delete_profile(self.profiles, profile.id)
            save_profiles(self.profiles)
            self._selected_profile_id = None
            self.btn_edit_profile.configure(state="disabled")
            self.btn_delete_profile.configure(state="disabled")
            self.btn_login_profile.configure(state="disabled")
            self._refresh_profile_list()
            self._append_log(f"Đã xóa profile: [{profile.name}]", "WARNING")
            dialog.destroy()

        ctk.CTkButton(btn_frame, text="🗑️ Xóa", fg_color="#ef4444", hover_color="#dc2626",
                      width=100, command=do_delete).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Hủy", fg_color="#334155", hover_color="#475569",
                      width=100, command=dialog.destroy).pack(side="left", padx=10)

    def _on_first_login(self):
        """Mở trình duyệt để người dùng đăng nhập lần đầu tiên.
        Tự động lưu real-time cookies + localStorage (uc-core-auth) vào session.json."""
        def run_browser():
            self._append_log("🔑 Đang mở trình duyệt để đăng nhập lần đầu...", "INFO")

            async def _launch():
                import json, os
                async with async_playwright() as p:
                    browser = await launch_browser(p, headless=False, profile_dir=None)
                    page = browser.pages[0] if browser.pages else await browser.new_page()
                    await page.goto("https://ucircle.net/auth/login")
                    self._append_log(
                        "Trình duyệt đã mở. Bạn hãy tiến hành đăng nhập. Tool sẽ tự động lưu session khi bạn đăng nhập thành công!",
                        "INFO"
                    )

                    # Vòng lặp lưu real-time session WHILE page is open
                    try:
                        while len(browser.pages) > 0:
                            try:
                                await browser.storage_state(path="session.json")
                            except Exception:
                                pass
                            await asyncio.sleep(2)
                    except Exception:
                        pass

                    try:
                        await browser.close()
                        if hasattr(browser, "browser") and browser.browser:
                            await browser.browser.close()
                    except Exception:
                        pass

                    if os.path.exists("session.json"):
                        try:
                            with open("session.json", "r", encoding="utf-8") as f:
                                st = json.load(f)
                            has_auth = any(
                                item.get("name") == "uc-core-auth"
                                for orig in st.get("origins", [])
                                for item in orig.get("localStorage", [])
                            )
                            if has_auth:
                                self._append_log(
                                    "✓ Đăng nhập thành công! Session đã được lưu vào session.json. Bây giờ bạn có thể chạy đa luồng thoải mái!",
                                    "INFO"
                                )
                            else:
                                self._append_log(
                                    "⚠ Trình duyệt đã đóng. Vui lòng đảm bảo bạn đã đăng nhập thành công trước khi đóng.",
                                    "WARNING"
                                )
                        except Exception:
                            pass

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(_launch())
            except Exception as e:
                self._append_log(f"Lỗi mở trình duyệt đăng nhập: {e}", "ERROR")
            finally:
                loop.close()

        threading.Thread(target=run_browser, daemon=True).start()

    def _on_logout_session(self):
        """Xóa session.json và các dữ liệu session cũ để người dùng đăng nhập tài khoản khác từ đầu."""
        import os, shutil
        try:
            if os.path.exists("session.json"):
                os.remove("session.json")

            if os.path.exists("./browser-profile"):
                try:
                    shutil.rmtree("./browser-profile")
                except Exception:
                    pass

            self._append_log(
                "🚪 Đã đăng xuất session thành công! session.json và cache cũ đã xóa. Bạn có thể nhấn '🔑 Đăng Nhập Lần Đầu' để đăng nhập tài khoản mới.",
                "INFO"
            )
        except Exception as e:
            self._append_log(f"Lỗi khi đăng xuất: {e}", "ERROR")

    def _on_login_profile(self):
        """Mở browser riêng cho profile được chọn để đăng nhập thủ công."""
        if not self._selected_profile_id:
            return
        profile = next((p for p in self.profiles if p.id == self._selected_profile_id), None)
        if not profile:
            return

        def run_browser():
            self._append_log(f"Đang mở trình duyệt cho profile [{profile.name}]...", "INFO")
            proxy = profile.proxy.to_playwright_proxy() if profile.proxy and profile.proxy.is_valid() else None

            async def _launch():
                async with async_playwright() as p:
                    browser = await launch_browser(
                        p, headless=False,
                        profile_dir=profile.profile_dir,
                        proxy=proxy
                    )
                    page = browser.pages[0] if browser.pages else await browser.new_page()

                    url = profile.ucircle_url or "https://ucircle.net"
                    await page.goto(url)
                    self._append_log(
                        f"[{profile.name}] Đã mở trình duyệt. Hãy đăng nhập rồi đóng cửa sổ.",
                        "INFO"
                    )
                    try:
                        while len(browser.pages) > 0:
                            try:
                                await browser.storage_state(path="session.json")
                            except Exception:
                                pass
                            await asyncio.sleep(2)
                    except Exception:
                        pass

                    try:
                        await browser.storage_state(path="session.json")
                        await browser.close()
                        if hasattr(browser, "browser") and browser.browser:
                            await browser.browser.close()
                    except Exception:
                        pass

                    self._append_log(f"[{profile.name}] Trình duyệt đã đóng. Session đã được lưu thành công!", "INFO")

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(_launch())
            except Exception as e:
                self._append_log(f"Lỗi mở trình duyệt [{profile.name}]: {e}", "ERROR")
            finally:
                loop.close()

        threading.Thread(target=run_browser, daemon=True).start()


    # ── Profile Dialog (Add / Edit) ──────────────────────────────────
    def _show_profile_dialog(self, profile: ProfileConfig, is_new: bool = True):
        """Hiển thị dialog form để thêm hoặc sửa thông tin profile."""
        dialog = ctk.CTkToplevel(self)
        title_str = "➕ Thêm Profile Mới" if is_new else f"✏️ Sửa Profile: {profile.name}"
        dialog.title(title_str)
        dialog.geometry("660x680")
        dialog.grab_set()
        dialog.resizable(True, True)

        # Scrollable form
        scroll = ctk.CTkScrollableFrame(dialog, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=15, pady=10)
        scroll.grid_columnconfigure(1, weight=1)

        def make_label(row, text):
            ctk.CTkLabel(scroll, text=text, font=ctk.CTkFont(size=12),
                         text_color="#94a3b8", anchor="e").grid(
                row=row, column=0, padx=(5, 10), pady=6, sticky="e")

        def make_entry(row, default="", placeholder="", width=None):
            e = ctk.CTkEntry(scroll, font=ctk.CTkFont(size=12),
                             height=32, placeholder_text=placeholder)
            if width:
                e.configure(width=width)
            e.grid(row=row, column=1, padx=(0, 10), pady=6, sticky="ew")
            if default:
                e.insert(0, default)
            return e

        # ── Section: Thông tin cơ bản ────────────────────────────
        ctk.CTkLabel(scroll, text="— Thông Tin Cơ Bản —",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color="#38bdf8").grid(row=0, column=0, columnspan=2, pady=(5, 2), sticky="w", padx=5)

        make_label(1, "Tên Profile:")
        e_name = make_entry(1, profile.name, "Ví dụ: Tài khoản 1")

        make_label(2, "Ghi chú:")
        e_notes = make_entry(2, profile.notes, "Ghi chú tùy ý...")

        # ── Section: UCircle URL ─────────────────────────────────
        ctk.CTkLabel(scroll, text="— UCircle URL & Video ─",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color="#38bdf8").grid(row=3, column=0, columnspan=2, pady=(10, 2), sticky="w", padx=5)

        make_label(4, "URL UCircle:")
        e_url = make_entry(4, profile.ucircle_url,
                           "https://ucircle.net/app/c/...?v=...")

        make_label(6, "Số Video Tối Đa:")
        e_max = make_entry(6, str(profile.max_videos), "100")

        # ── Section: Chế Độ Chạy ─────────────────────────────────
        ctk.CTkLabel(scroll, text="— Chế Độ Chạy & Thời Gian —",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color="#38bdf8").grid(row=7, column=0, columnspan=2, pady=(10, 2), sticky="w", padx=5)

        make_label(8, "Mục tiêu:")
        seg_target = ctk.CTkSegmentedButton(
            scroll,
            values=["🎥 Video Ngắn (Wavee)", "🏠 Wavee Cá Nhân (Profile)", "📰 Bảng Tin (Feed)"],
            font=ctk.CTkFont(size=11)
        )
        _target_display_map = {
            "feed": "📰 Bảng Tin (Feed)",
            "my_wavee": "🏠 Wavee Cá Nhân (Profile)",
            "wavee": "🎥 Video Ngắn (Wavee)",
        }
        seg_target.set(_target_display_map.get(profile.target_type, "🎥 Video Ngắn (Wavee)"))
        seg_target.grid(row=8, column=1, padx=(0, 10), pady=6, sticky="ew")

        make_label(9, "Chế độ:")
        seg_react_mode = ctk.CTkSegmentedButton(
            scroll,
            values=["⚡ Chỉ Thả Ngũ Hành (Nhanh)", "👁 Xem Video rồi Thả"],
            font=ctk.CTkFont(size=11)
        )
        seg_react_mode.set("⚡ Chỉ Thả Ngũ Hành (Nhanh)" if profile.react_only else "👁 Xem Video rồi Thả")
        seg_react_mode.grid(row=9, column=1, padx=(0, 10), pady=6, sticky="ew")

        make_label(10, "Ngũ Hành:")
        elem_map = {
            "shuffle": "🎲Ngẫu nhiên (Shuffle)",
            "hoa": "🔥Hỏa (hoa)",
            "tho": "🏔️Thổ (tho)",
            "kim": "⚔️Kim (kim)",
            "thuy": "💧Thủy (thuy)",
            "moc": "🌲Mộc (moc)"
        }
        elem_rev = {v: k for k, v in elem_map.items()}
        combo_elem = ctk.CTkComboBox(
            scroll,
            values=list(elem_map.values()),
            font=ctk.CTkFont(size=11)
        )
        combo_elem.set(elem_map.get(profile.element_mode, elem_map["shuffle"]))
        combo_elem.grid(row=10, column=1, padx=(0, 10), pady=6, sticky="w")

        make_label(11, "Thời gian xem (s):")
        watch_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        watch_frame.grid(row=11, column=1, padx=(0, 10), pady=6, sticky="w")
        e_watch_min = ctk.CTkEntry(watch_frame, width=60, height=32, font=ctk.CTkFont(size=12))
        e_watch_min.insert(0, str(profile.watch_min_seconds))
        e_watch_min.grid(row=0, column=0, padx=(0, 5))
        ctk.CTkLabel(watch_frame, text="đến", font=ctk.CTkFont(size=12)).grid(row=0, column=1, padx=5)
        e_watch_max = ctk.CTkEntry(watch_frame, width=60, height=32, font=ctk.CTkFont(size=12))
        e_watch_max.insert(0, str(profile.watch_max_seconds))
        e_watch_max.grid(row=0, column=2, padx=(5, 0))

        make_label(12, "Độ trễ (s):")
        delay_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        delay_frame.grid(row=12, column=1, padx=(0, 10), pady=6, sticky="w")
        e_delay_min = ctk.CTkEntry(delay_frame, width=60, height=32, font=ctk.CTkFont(size=12))
        e_delay_min.insert(0, str(profile.action_delay_min))
        e_delay_min.grid(row=0, column=0, padx=(0, 5))
        ctk.CTkLabel(delay_frame, text="đến", font=ctk.CTkFont(size=12)).grid(row=0, column=1, padx=5)
        e_delay_max = ctk.CTkEntry(delay_frame, width=60, height=32, font=ctk.CTkFont(size=12))
        e_delay_max.insert(0, str(profile.action_delay_max))
        e_delay_max.grid(row=0, column=2, padx=(5, 0))

        # ── Section: Profile Directory ───────────────────────────
        ctk.CTkLabel(scroll, text="— Thư Mục Profile (Browser Session) —",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color="#38bdf8").grid(row=13, column=0, columnspan=2, pady=(10, 2), sticky="w", padx=5)

        make_label(14, "Thư mục Profile:")
        dir_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        dir_frame.grid(row=14, column=1, padx=(0, 10), pady=6, sticky="ew")
        dir_frame.grid_columnconfigure(0, weight=1)

        e_dir = ctk.CTkEntry(dir_frame, font=ctk.CTkFont(size=12), height=32,
                             placeholder_text="./browser-profile/profile_name")
        e_dir.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        if profile.profile_dir:
            e_dir.insert(0, profile.profile_dir)

        def _auto_dir():
            name = e_name.get().strip() or "profile"
            safe = "".join(c if c.isalnum() else "_" for c in name.lower())[:20]
            e_dir.delete(0, "end")
            e_dir.insert(0, f"./browser-profile/{safe}_{profile.id}")
        ctk.CTkButton(dir_frame, text="Tự động", width=70, height=32,
                      fg_color="#334155", hover_color="#475569",
                      command=_auto_dir).grid(row=0, column=1)

        # ── Bottom Buttons ───────────────────────────────────────
        btn_frame = ctk.CTkFrame(dialog, fg_color=("#0f172a", "#0f172a"), height=55)
        btn_frame.pack(fill="x", padx=15, pady=(0, 10))

        lbl_err = ctk.CTkLabel(btn_frame, text="", font=ctk.CTkFont(size=11),
                               text_color="#ef4444")
        lbl_err.pack(side="left", padx=15, pady=10)

        def do_save():
            # Lấy giá trị từ form
            name_val = e_name.get().strip()
            if not name_val:
                lbl_err.configure(text="⚠ Tên profile không được để trống!")
                return

            url_val = e_url.get().strip()
            vid_val = extract_url_details(url_val).get("video_id") or ""
            try:
                max_v = int(e_max.get().strip() or "100")
            except ValueError:
                max_v = 100

            dir_val = e_dir.get().strip()
            if not dir_val:
                safe = "".join(c if c.isalnum() else "_" for c in name_val.lower())[:20]
                dir_val = f"./browser-profile/{safe}_{profile.id}"

            # Cập nhật profile object
            profile.name = name_val
            profile.notes = e_notes.get().strip()
            profile.ucircle_url = url_val
            profile.target_video_id = vid_val
            profile.max_videos = max_v
            profile.profile_dir = dir_val
            profile.proxy = None
            _target_value_map = {
                "📰 Bảng Tin (Feed)": "feed",
                "🏠 Wavee Cá Nhân (Profile)": "my_wavee",
                "🎥 Video Ngắn (Wavee)": "wavee",
            }
            profile.target_type = _target_value_map.get(seg_target.get(), "wavee")
            profile.react_only = (seg_react_mode.get() == "⚡ Chỉ Thả Ngũ Hành (Nhanh)")
            profile.element_mode = elem_rev.get(combo_elem.get(), "shuffle")
            try:
                profile.watch_min_seconds = int(e_watch_min.get().strip() or "2")
                profile.watch_max_seconds = int(e_watch_max.get().strip() or "5")
                profile.action_delay_min = int(e_delay_min.get().strip() or "1")
                profile.action_delay_max = int(e_delay_max.get().strip() or "3")
            except ValueError:
                pass

            if is_new:
                self.profiles.append(profile)
                self._append_log(f"Đã thêm profile mới: [{profile.name}]", "INFO")
            else:
                self.profiles = update_profile(self.profiles, profile)
                self._append_log(f"Đã cập nhật profile: [{profile.name}]", "INFO")

            save_profiles(self.profiles)
            self._refresh_profile_list()
            dialog.destroy()

        ctk.CTkButton(
            btn_frame, text="💾 Lưu Profile",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#0284c7", hover_color="#0369a1",
            height=36, width=130, command=do_save
        ).pack(side="right", padx=(5, 15), pady=8)

        ctk.CTkButton(
            btn_frame, text="Hủy",
            font=ctk.CTkFont(size=12),
            fg_color="#334155", hover_color="#475569",
            height=36, width=80, command=dialog.destroy
        ).pack(side="right", padx=5, pady=8)

    # ── Batch Run ───────────────────────────────────────────────────
    def _on_batch_start(self):
        """Bắt đầu Batch Run với tất cả profile đang bật."""
        if self.is_running:
            self._append_log("Đang có phiên chạy. Vui lòng dừng trước khi chạy Batch.", "WARNING")
            return

        enabled = get_enabled_profiles(self.profiles)
        if not enabled:
            self._append_log("Không có profile nào đang bật. Hãy bật ít nhất 1 profile.", "WARNING")
            return

        # Lấy cấu hình gốc từ UI
        base_cfg = self._get_ui_config()
        errors = validate_config(base_cfg)
        # Bỏ qua lỗi URL vì mỗi profile có URL riêng
        errors = [e for e in errors if "URL" not in e]
        if errors:
            self._append_log("Cấu hình cơ sở có lỗi: " + "; ".join(errors), "ERROR")
            return

        self.is_running = True
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.btn_pause.configure(state="disabled")
        self._update_status_badge("⚡ BATCH RUN", "#4c1d95", "#a855f7")

        self._append_log(f"══ Bắt đầu Batch Run: {len(enabled)} profile ══", "INFO")

        self.batch_engine = BatchEngine(base_cfg, enabled)
        self.batch_engine.on_log = lambda msg, lvl: self._append_log(msg, lvl)
        self.batch_engine.on_batch_progress = lambda stats: self.after(0, self._update_batch_progress_ui, stats)
        self.batch_engine.on_profile_start = lambda p, i, t: self._append_log(
            f"▶ [{i}/{t}] Bắt đầu profile: {p.name}", "INFO"
        )
        self.batch_engine.on_profile_finish = lambda p, st: self._append_log(
            f"✓ Hoàn thành profile: {p.name}", "INFO"
        )
        self.batch_engine.on_batch_finish = self._on_batch_finished

        self.worker_thread = threading.Thread(target=self._run_batch_thread, daemon=True)
        self.worker_thread.start()

    def _run_batch_thread(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.batch_engine.run())
        finally:
            loop.close()

    def _on_batch_stop(self):
        if self.batch_engine and self.is_running:
            self.btn_stop.configure(state="disabled")
            self._update_status_badge("● ĐANG DỪNG BATCH...", "#7f1d1d", "#ef4444")
            self.batch_engine.request_stop()

    def _on_batch_finished(self, stats: Dict[str, Any]):
        def handle():
            self.is_running = False
            self.btn_start.configure(state="normal")
            self.btn_stop.configure(state="disabled")
            self.btn_pause.configure(state="disabled")
            self._update_status_badge("● HOÀN THÀNH", "#064e3b", "#10b981")
            self._append_log(
                f"🏁 Batch kết thúc: {stats.get('completed_profiles', 0)}/{stats.get('total_profiles', 0)} profile | "
                f"Tổng Reacted: {stats.get('total_reacted', 0)} | "
                f"Skipped: {stats.get('total_skipped', 0)}",
                "INFO"
            )
        self.after(0, handle)

    def _update_batch_progress_ui(self, stats: Dict[str, Any]):
        """Cập nhật Batch Progress Panel trên UI."""
        total_p = stats.get("total_profiles", 1)
        current_p = stats.get("current_profile_index", 0)
        name = stats.get("current_profile_name", "—")
        reacted = stats.get("total_reacted", 0)
        skipped = stats.get("total_skipped", 0)
        errors = stats.get("total_errors", 0)

        vid_cur = stats.get("current_profile_video_current", 0)
        vid_tot = stats.get("current_profile_video_total", 1)

        self.lbl_batch_profile_counter.configure(
            text=f"Profile {current_p}/{total_p}: {name}"
        )
        self.lbl_batch_stats.configure(
            text=f"Tổng Reacted: {reacted}  |  Skipped: {skipped}  |  Lỗi: {errors}"
        )
        self.batch_profile_bar.set(current_p / max(total_p, 1))
        self.batch_video_bar.set(vid_cur / max(vid_tot, 1))

    # -------------------------------------------------------------
    # HELPER LOGIC: CONFIG & UI BINDING
    # -------------------------------------------------------------
    def _load_config_to_ui(self):
        """Đưa toàn bộ dữ liệu cấu hình vào UI Controls"""
        cfg = self.config

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

    def _get_ui_config(self) -> AppConfig:
        """Lấy cấu hình hiện tại từ các trường trên giao diện"""
        return AppConfig(
            headless=bool(self.sw_headless.get()),
            dry_run=bool(self.sw_dry_run.get()),
            profile_dir=self.entry_profile_dir.get().strip() or "./browser-profile",
        )


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
                    try:
                        while len(browser.pages) > 0:
                            await asyncio.sleep(1)
                    except Exception:
                        pass
                    
                    try:
                        # Luôn lưu master session.json khi đóng để tất cả luồng dùng chung
                        await browser.storage_state(path="session.json")
                        await browser.close()
                        if hasattr(browser, "browser") and browser.browser:
                            await browser.browser.close()
                    except Exception:
                        pass
            
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
