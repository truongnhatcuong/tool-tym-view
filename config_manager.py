import json
import os
import re
from dataclasses import dataclass, asdict
from urllib.parse import urlparse, parse_qs
from typing import Optional, Dict, Any, List

CONFIG_FILE_PATH = "config.json"

@dataclass
class AppConfig:
    ucircle_url: str = "https://ucircle.net/app/c/e3500793-72a2-4c0e-b7b0-4d865eddcbe3?v=f99fabf5-a27d-45be-84d1-f39d43f1412e"
    target_video_id: str = "f99fabf5-a27d-45be-84d1-f39d43f1412e"
    react_only: bool = True
    watch_min_seconds: int = 2
    watch_max_seconds: int = 3
    action_delay_min: int = 1
    action_delay_max: int = 3
    max_videos: int = 1000
    headless: bool = False
    dry_run: bool = False
    profile_dir: str = "./browser-profile"
    element_mode: str = "shuffle"  # "shuffle", "hoa", "tho", "kim", "thuy", "moc"
    target_type: str = "wavee"      # "wavee" | "feed"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppConfig":
        valid_keys = cls.__dataclass_fields__.keys()
        filtered_data = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered_data)


def extract_url_details(raw_url: str) -> Dict[str, Optional[str]]:
    """
    Tự động bóc tách thông tin từ URL UCircle:
    - Circle ID: từ đường dẫn /app/c/<circle_id>
    - Video ID: từ query parameter ?v=<video_id>
    """
    if not raw_url or not isinstance(raw_url, str):
        return {"clean_url": "", "video_id": None, "circle_id": None}

    raw_url = raw_url.strip()
    try:
        parsed = urlparse(raw_url)
        query_params = parse_qs(parsed.query)
        video_id = query_params.get("v", [None])[0]

        circle_id = None
        match = re.search(r"/app/c/([a-zA-Z0-9\-]+)", parsed.path)
        if match:
            circle_id = match.group(1)

        return {
            "clean_url": raw_url,
            "video_id": video_id,
            "circle_id": circle_id
        }
    except Exception:
        return {"clean_url": raw_url, "video_id": None, "circle_id": None}


def get_presets() -> Dict[str, AppConfig]:
    """Cung cấp các mẫu cấu hình tối ưu sẵn 1-click"""
    return {
        "fast": AppConfig(
            react_only=True,
            watch_min_seconds=1,
            watch_max_seconds=2,
            action_delay_min=1,
            action_delay_max=2,
            max_videos=1000,
            headless=False,
            dry_run=False,
            element_mode="shuffle"
        ),
        "safe": AppConfig(
            react_only=False,
            watch_min_seconds=3,
            watch_max_seconds=7,
            action_delay_min=2,
            action_delay_max=4,
            max_videos=500,
            headless=False,
            dry_run=False,
            element_mode="shuffle"
        ),
        "dry_run": AppConfig(
            react_only=False,
            watch_min_seconds=2,
            watch_max_seconds=4,
            action_delay_min=1,
            action_delay_max=2,
            max_videos=20,
            headless=False,
            dry_run=True,
            element_mode="shuffle"
        )
    }


def validate_config(cfg: AppConfig) -> List[str]:
    """Kiểm tra tính hợp lệ của cấu hình và trả về danh sách cảnh báo/lỗi nếu có"""
    errors = []
    if not cfg.ucircle_url or not cfg.ucircle_url.startswith("http"):
        errors.append("URL UCircle không hợp lệ (phải bắt đầu bằng http:// hoặc https://).")
    
    if cfg.max_videos <= 0:
        errors.append("Số lượng video tối đa phải lớn hơn 0.")

    if cfg.watch_min_seconds < 0:
        errors.append("Thời gian xem tối thiểu không được âm.")

    if cfg.watch_min_seconds > cfg.watch_max_seconds:
        errors.append("Thời gian xem tối thiểu không thể lớn hơn thời gian xem tối đa.")

    if cfg.action_delay_min < 0:
        errors.append("Độ trễ tối thiểu không được âm.")

    if cfg.action_delay_min > cfg.action_delay_max:
        errors.append("Độ trễ tối thiểu không thể lớn hơn độ trễ tối đa.")

    return errors


def load_config(file_path: str = CONFIG_FILE_PATH) -> AppConfig:
    """Tải cấu hình từ file JSON, nếu chưa có sẽ tạo file mặc định"""
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                config = AppConfig.from_dict(data)
                # Tự động trích xuất target_video_id nếu config chưa có hoặc chưa khớp với URL
                url_info = extract_url_details(config.ucircle_url)
                if url_info["video_id"] and not config.target_video_id:
                    config.target_video_id = url_info["video_id"]
                return config
        except Exception as e:
            print(f"Lỗi khi đọc file config '{file_path}': {e}. Sử dụng cấu hình mặc định.")
    
    # Tạo cấu hình mặc định
    default_config = AppConfig()
    url_info = extract_url_details(default_config.ucircle_url)
    if url_info["video_id"]:
        default_config.target_video_id = url_info["video_id"]
    save_config(default_config, file_path)
    return default_config


def save_config(cfg: AppConfig, file_path: str = CONFIG_FILE_PATH) -> bool:
    """Lưu cấu hình vào file JSON"""
    try:
        # Nếu target_video_id trống, thử bóc tách từ ucircle_url
        if not cfg.target_video_id:
            url_info = extract_url_details(cfg.ucircle_url)
            if url_info["video_id"]:
                cfg.target_video_id = url_info["video_id"]

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(cfg.to_dict(), f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Lỗi khi lưu file config '{file_path}': {e}")
        return False
