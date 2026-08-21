import asyncio
import argparse
import sys
import os
from config_manager import load_config, save_config, AppConfig, extract_url_details
from automation.engine import AutomationEngine
from utils.logger import logger

def parse_args():
    parser = argparse.ArgumentParser(description="UCircle Video QA & Auto React Tool")
    parser.add_argument("--gui", action="store_true", help="Launch Graphical User Interface")
    parser.add_argument("--url", type=str, default=None, help="UCircle URL")
    parser.add_argument("--video-id", type=str, default=None, help="Target Video ID to start")
    parser.add_argument("--dry-run", action="store_true", help="Run without clicking React button")
    parser.add_argument("--videos", type=int, default=None, help="Max videos per session")
    parser.add_argument("--watch-min", type=int, default=None, help="Min watch time (seconds)")
    parser.add_argument("--watch-max", type=int, default=None, help="Max watch time (seconds)")
    parser.add_argument("--watch-video", action="store_true", help="Watch video before reacting (default is react-only)")
    parser.add_argument("--element", type=str, default=None, choices=["shuffle", "hoa", "tho", "kim", "thuy", "moc"], help="Element choice mode")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    return parser.parse_args()

async def run_cli(cfg: AppConfig):
    engine = AutomationEngine(cfg)
    
    def log_handler(msg, lvl):
        print(f"[{lvl}] {msg}")
    
    engine.on_log = log_handler
    engine.on_status_change = lambda status: print(f">> Trạng thái: {status}")
    
    await engine.run()

def main():
    os.makedirs("logs/screenshots", exist_ok=True)
    args = parse_args()

    # Nếu người dùng muốn mở GUI hoặc cờ --gui
    if args.gui:
        import gui
        gui.main()
        return

    # Tải cấu hình từ config.json
    cfg = load_config()

    # Ghi đè bởi CLI arguments nếu có
    if args.url:
        cfg.ucircle_url = args.url
        extracted = extract_url_details(args.url)
        if extracted["video_id"] and not args.video_id:
            cfg.target_video_id = extracted["video_id"]
            
    if args.video_id:
        cfg.target_video_id = args.video_id
    if args.dry_run:
        cfg.dry_run = True
    if args.videos is not None:
        cfg.max_videos = args.videos
    if args.watch_min is not None:
        cfg.watch_min_seconds = args.watch_min
    if args.watch_max is not None:
        cfg.watch_max_seconds = args.watch_max
    if args.watch_video:
        cfg.react_only = False
    if args.element:
        cfg.element_mode = args.element
    if args.headless:
        cfg.headless = True

    # Lưu lại cấu hình mới nhất
    save_config(cfg)

    print("=" * 60)
    print("🚀 BẮT ĐẦU UCIRCLE QA AUTOMATION (CLI MODE)")
    print(f"• URL: {cfg.ucircle_url}")
    print(f"• Video ID mục tiêu: {cfg.target_video_id}")
    print(f"• Chế độ React: {'Chỉ thả ngũ hành (Nhanh)' if cfg.react_only else f'Xem ({cfg.watch_min_seconds}s-{cfg.watch_max_seconds}s) rồi thả'}")
    print(f"• Ngũ hành: {cfg.element_mode}")
    print(f"• Số lượng video: {cfg.max_videos}")
    print(f"• Dry Run: {cfg.dry_run} | Headless: {cfg.headless}")
    print("=" * 60)

    try:
        asyncio.run(run_cli(cfg))
    except KeyboardInterrupt:
        print("\n[!] Đã nhận tín hiệu hủy từ bàn phím (Ctrl+C). Đang thoát...")

if __name__ == "__main__":
    main()
