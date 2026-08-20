# Build UCircle Video Interaction QA Tool

## Mục tiêu

Xây dựng một tool automation bằng **Python + Playwright** để kiểm thử luồng video trên UCircle tại URL:

`https://ucircle.net/app/c/7b944633-043c-445b-b516-aeeddb7bb7f9?v=d4f2b67c-317c-46fd-bbb7-c1bab3ed4740`

Tool dùng cho **QA/testing trên tài khoản được phép**, mô phỏng một người dùng thật ở mức chức năng:

1. Mở UCircle.
2. Đăng nhập thủ công nếu chưa đăng nhập.
3. Mở Circle/video feed được chỉ định.
4. Tìm video.
5. Click/mở video.
6. Theo dõi video trong khoảng thời gian cấu hình.
7. Phát hiện nút Like.
8. Click Like nếu video chưa được Like.
9. Chuyển sang video tiếp theo.
10. Ghi log toàn bộ quá trình.

## Công nghệ

- Python 3.11+
- Playwright
- asyncio
- pathlib
- json
- logging
- dataclasses
- dotenv

Không sử dụng Selenium.

## Kiến trúc project

Tạo project:

```text
ucircle-video-qa/
├── main.py
├── config.py
├── requirements.txt
├── .env
├── .gitignore
├── README.md
│
├── automation/
│   ├── __init__.py
│   ├── browser.py
│   ├── login.py
│   ├── feed.py
│   ├── video.py
│   └── actions.py
│
├── utils/
│   ├── __init__.py
│   ├── logger.py
│   ├── selectors.py
│   └── helpers.py
│
└── logs/
```

## Configuration

Tạo `.env`:

```env
UCIRCLE_URL=https://ucircle.net/app/c/7b944633-043c-445b-b516-aeeddb7bb7f9?v=d4f2b67c-317c-46fd-bbb7-c1bab3ed4740

HEADLESS=false

WATCH_MIN_SECONDS=5
WATCH_MAX_SECONDS=10

MAX_VIDEOS_PER_SESSION=10

ACTION_DELAY_MIN=1
ACTION_DELAY_MAX=3

PROFILE_DIR=./browser-profile
```

Không lưu password vào source code.

## Browser

Sử dụng Playwright Chromium.

Sử dụng persistent browser profile:

```python
browser = await chromium.launch_persistent_context(
    user_data_dir=PROFILE_DIR,
    headless=HEADLESS
)
```

Mục đích là để QA tester có thể đăng nhập thủ công một lần và session được giữ lại.

Không tự động nhập OTP.

Không bypass CAPTCHA.

Không bypass Cloudflare hoặc anti-bot.

Nếu gặp CAPTCHA/challenge thì:

```text
PAUSE AUTOMATION
↓
Thông báo cho người dùng
↓
Chờ người dùng xử lý thủ công
↓
Tiếp tục automation
```

## Login flow

Khi mở URL:

1. Kiểm tra xem người dùng đã đăng nhập chưa.
2. Nếu đã login → tiếp tục.
3. Nếu chưa login → hiển thị:

```text
Please login manually in the browser.
Press ENTER after login is completed.
```

Không lưu credentials.

## Video detection

Không hard-code selector quá nhiều.

Ưu tiên tìm element theo:

1. role
2. aria-label
3. text
4. data-testid
5. CSS selector cuối cùng

Tạo module:

```text
utils/selectors.py
```

Ví dụ:

```python
LIKE_SELECTORS = [
    '[aria-label*="Like"]',
    '[aria-label*="like"]',
    'button[data-testid*="like"]',
]

VIDEO_SELECTORS = [
    'video',
    '[data-testid*="video"]',
]
```

Nhưng trước khi sử dụng selector phải inspect DOM thực tế của UCircle và cập nhật selector cho đúng.

## Watch video

Khi tìm thấy video:

```text
VIDEO FOUND
↓
Open video
↓
Check video element
↓
Play
↓
Watch configured duration
↓
Check Like state
```

Thời gian xem:

```python
watch_seconds = random.uniform(
    WATCH_MIN_SECONDS,
    WATCH_MAX_SECONDS
)
```

Trong QA mode có thể sử dụng random delay để kiểm thử các trường hợp timing khác nhau.

Không sử dụng tốc độ hoặc tần suất nhằm tạo artificial engagement.

## Like logic

Trước khi click Like:

```text
CHECK CURRENT STATE
```

Nếu video đã Like:

```text
SKIP LIKE
```

Nếu chưa Like:

```text
CLICK LIKE
```

Sau khi click:

```text
VERIFY STATE CHANGED
```

Nếu state không thay đổi:

```text
LOG WARNING
```

Không click Like nhiều lần.

Không retry vô hạn.

Ví dụ:

```python
async def like_if_needed(page):
    like_button = await find_like_button(page)

    if not like_button:
        return False

    is_liked = await detect_like_state(like_button)

    if is_liked:
        logger.info("Already liked")
        return False

    await like_button.click()

    await verify_like_state(like_button)

    logger.info("Like action completed")

    return True
```

## Next video

Sau khi hoàn thành một video:

```text
WAIT
↓
FIND NEXT VIDEO
↓
SCROLL
↓
WAIT FOR VIDEO
↓
PROCESS
```

Không click liên tục.

Không spam.

Không chạy nhiều browser/account song song.

## Session limit

Có giới hạn:

```env
MAX_VIDEOS_PER_SESSION=10
```

Sau khi đạt giới hạn:

```text
Session completed.
Stopping automation.
```

## Logging

Log ra:

```text
logs/session.log
```

Format:

```text
2026-08-21 00:10:01 INFO  Browser started
2026-08-21 00:10:04 INFO  Login detected
2026-08-21 00:10:08 INFO  Video #1 detected
2026-08-21 00:10:15 INFO  Video watched: 7.2s
2026-08-21 00:10:16 INFO  Like state: not-liked
2026-08-21 00:10:17 INFO  Like clicked
2026-08-21 00:10:20 INFO  Moving to next video
```

## Error handling

Các lỗi cần xử lý:

- Login timeout
- Video không tìm thấy
- Like button không tìm thấy
- Video không play
- Page timeout
- Browser crash
- Network timeout
- Unexpected DOM change

Không retry vô hạn.

Mỗi action tối đa 2-3 retries.

## Screenshot debugging

Khi action thất bại:

```text
logs/screenshots/
```

Tự động chụp:

```python
await page.screenshot(
    path=f"logs/screenshots/error_{timestamp}.png"
)
```

## Dry-run mode

Thêm:

```env
DRY_RUN=true
```

Nếu:

```env
DRY_RUN=true
```

Tool sẽ:

- mở video
- watch video
- tìm Like button
- log rằng sẽ Like

nhưng **không click Like**.

Nếu:

```env
DRY_RUN=false
```

thì mới thực hiện click trong môi trường được phép kiểm thử.

## CLI

Hỗ trợ:

```bash
python main.py
```

và:

```bash
python main.py --dry-run
```

```bash
python main.py --videos 5
```

```bash
python main.py --watch-min 5 --watch-max 10
```

## Main flow

Implement flow:

```python
async def main():

    browser = await launch_browser()

    page = await open_ucircle(browser)

    await ensure_login(page)

    for index in range(MAX_VIDEOS_PER_SESSION):

        video = await find_video(page)

        if not video:
            logger.warning("Video not found")
            break

        await open_video(video)

        await play_video(video)

        await watch_video(
            min_seconds=WATCH_MIN_SECONDS,
            max_seconds=WATCH_MAX_SECONDS
        )

        if not DRY_RUN:
            await like_if_needed(page)

        await move_to_next_video(page)

    await browser.close()
```

## Important constraints

Tool này chỉ được thiết kế cho:

- QA/testing
- tài khoản mà người vận hành có quyền sử dụng
- môi trường staging/test
- kiểm thử UI/functionality

Không implement:

- CAPTCHA bypass
- Cloudflare bypass
- fingerprint spoofing
- proxy rotation
- account farming
- fake accounts
- mass likes
- artificial view generation
- spam engagement
- scraping dữ liệu người dùng
- lấy session/cookie của người khác
- bypass rate limits
- bypass platform security

Nếu UCircle có API chính thức cho testing hoặc automation thì ưu tiên API chính thức thay vì browser automation.

## README

README phải có:

1. Cài Python
2. Cài dependencies
3. Cài Playwright browser

```bash
pip install -r requirements.txt
playwright install chromium
```

4. Tạo `.env`
5. Chạy tool
6. Login thủ công lần đầu
7. Chạy dry-run
8. Xem logs
9. Troubleshooting

## Deliverables

Hãy tạo đầy đủ source code cho toàn bộ project.

Yêu cầu:

- code chạy được
- Type hints
- async/await chuẩn
- clean architecture
- logging rõ ràng
- exception handling
- config tập trung
- selector tách riêng
- không hard-code credentials
- không bypass security
- README đầy đủ

Trước khi code, hãy inspect cấu trúc DOM của trang UCircle ở URL được cung cấp và xác định selector thực tế cho:

- video
- play
- like
- liked state
- next video
- loading state

Nếu không thể xác định selector từ môi trường hiện tại, hãy tạo selector abstraction và đánh dấu rõ những selector cần QA tester xác nhận thủ công thay vì tự đoán.
