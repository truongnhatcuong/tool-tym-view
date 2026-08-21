from config_manager import load_config

# Tải cấu hình mới nhất từ file config.json
_current_cfg = load_config()

UCIRCLE_URL = _current_cfg.ucircle_url
HEADLESS = _current_cfg.headless
WATCH_MIN_SECONDS = _current_cfg.watch_min_seconds
WATCH_MAX_SECONDS = _current_cfg.watch_max_seconds
MAX_VIDEOS_PER_SESSION = _current_cfg.max_videos
ACTION_DELAY_MIN = _current_cfg.action_delay_min
ACTION_DELAY_MAX = _current_cfg.action_delay_max
PROFILE_DIR = _current_cfg.profile_dir
DRY_RUN = _current_cfg.dry_run
REACT_ONLY = _current_cfg.react_only
TARGET_VIDEO_ID = _current_cfg.target_video_id
ELEMENT_MODE = _current_cfg.element_mode
