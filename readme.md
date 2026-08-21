# UCircle Video Interaction QA & Auto React Tool

Công cụ tự động hóa kiểm thử tương tác video và thả ngũ hành trên UCircle Wavee Feed, phát triển bằng **Python + Playwright + CustomTkinter**.

---

## 🌟 Tính năng nổi bật

1. **Giao diện đồ họa hiện đại (Modern Dark GUI)**:
   - Bảng điều khiển thời gian thực: Thống kê số video đã duyệt, đã thả ngũ hành, đã bỏ qua, thời gian chạy.
   - Nút điều khiển thông minh: **Bắt đầu**, **Tạm dừng**, **Dừng lại an toàn**, **Mở trình duyệt đăng nhập thủ công**.
   - Cửa sổ Live Log đổi màu theo cấp độ (INFO xanh lá, WARNING vàng, ERROR đỏ) kèm nút Xuất log và Xóa log.
   - Tab quản lý và xem nhanh ảnh chụp sự cố (Screenshots viewer).

2. **Hệ thống Quản lý Cấu hình Tối ưu (`config_manager.py`)**:
   - **Tự động nhận diện URL & Video ID**: Khi dán link UCircle bất kỳ (ví dụ `https://ucircle.net/app/c/...?...v=...`), hệ thống tự động bóc tách Video ID mục tiêu mà không cần chỉnh sửa thủ công.
   - **Lưu trữ JSON an toàn (`config.json`)** với cơ chế xác thực dữ liệu (Validation) chống nhập sai thông số.
   - **Cấu hình mẫu 1-click (Presets)**:
     - ⚡ **Siêu Tốc (Fast React)**: Bỏ qua bước chờ xem, tương tác ngũ hành ngay lập tức.
     - 🛡️ **An Toàn (Human-like)**: Xem video 3-7s, delay 2-4s ngẫu nhiên, mô phỏng người dùng thật.
     - 🔍 **Kiểm Thử (Dry-Run)**: Duyệt video và ghi log kiểm tra luồng nhưng không bấm nút thật.
   - **Lựa chọn Ngũ Hành linh hoạt**: Xáo bài đều 5 hệ (Shuffle bag) hoặc chọn cố định (Hỏa, Thổ, Kim, Thủy, Mộc).

---

## 🚀 Hướng dẫn Khởi chạy

### 1. Cài đặt môi trường
Đảm bảo đã cài đặt Python 3.10+ trên máy tính, sau đó chạy lệnh cài dependencies:

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Khởi chạy Giao diện Đồ họa (GUI)
- **Cách 1**: Nhấp đúp chuột vào file `run_gui.bat` trên Windows.
- **Cách 2**: Chạy lệnh qua terminal:
  ```bash
  python gui.py
  ```
  *(hoặc `python main.py --gui`)*

### 3. Khởi chạy Chế độ Dòng Lệnh (CLI)
- **Cách 1**: Nhấp đúp chuột vào file `run_cli.bat`.
- **Cách 2**: Chạy lệnh tùy biến tham số:
  ```bash
  # Chạy theo cấu hình lưu trong config.json
  python main.py

  # Chạy thử kiểm tra luồng (Dry-run)
  python main.py --dry-run

  # Chạy với số lượng video và thời gian xem tùy chỉnh
  python main.py --videos 50 --watch-min 3 --watch-max 8 --watch-video

  # Chạy ẩn trình duyệt (Headless)
  python main.py --headless
  ```

---

## 📂 Cấu trúc Thư mục

```text
tool-tym-view/
├── run_gui.bat             # File khởi chạy giao diện nhanh cho Windows
├── run_cli.bat             # File khởi chạy dòng lệnh nhanh cho Windows
├── gui.py                  # Giao diện đồ họa CustomTkinter hiện đại
├── main.py                 # Điểm vào chính hỗ trợ cả GUI và CLI
├── config_manager.py       # Quản lý cấu hình, validation, smart URL parsing & presets
├── config.py               # Tương thích ngược cấu hình
├── config.json             # File lưu cấu hình người dùng (tự động tạo)
├── requirements.txt        # Danh sách thư viện cần thiết
│
├── automation/             # Lõi tự động hóa
│   ├── __init__.py
│   ├── engine.py           # Bộ điều phối luồng có hỗ trợ pause/stop/callbacks
│   ├── browser.py          # Khởi động trình duyệt Playwright
│   ├── login.py            # Kiểm tra và hỗ trợ đăng nhập
│   ├── feed.py             # Xử lý tab Wavee và mở video
│   ├── video.py            # Xử lý thời gian xem video
│   └── actions.py          # Tương tác ngũ hành và cuộn video
│
├── utils/                  # Tiện ích bổ trợ
│   ├── __init__.py
│   ├── logger.py           # Ghi log ra file và console
│   ├── selectors.py        # Quản lý selector UCircle
│   └── helpers.py          # Hàm delay ngẫu nhiên
│
├── browser-profile/        # Lưu trữ phiên đăng nhập trình duyệt (persistent context)
└── logs/                   # Thư mục chứa session.log và ảnh chụp lỗi screenshots/
```

---

## 💡 Lưu ý khi Sử dụng
1. **Đăng nhập lần đầu**: Bạn có thể nhấn nút `🌐 Mở Trình Duyệt Đăng Nhập` trên giao diện để đăng nhập tài khoản UCircle một lần, session sẽ được lưu tự động trong thư mục `browser-profile`.
2. **Dừng an toàn**: Trong quá trình chạy, bạn có thể nhấn `⏸ Tạm Dừng` hoặc `⏹ Dừng Lại` bất cứ lúc nào, tool sẽ hoàn tất an toàn và đóng trình duyệt sạch sẽ mà không gây treo tiến trình.
