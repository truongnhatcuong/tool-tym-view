import json
import os
import uuid
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any

PROFILES_FILE_PATH = "profiles.json"


@dataclass
class ProxyConfig:
    """Cấu hình proxy cho từng profile trình duyệt."""
    server: str = ""       # Ví dụ: "http://proxy.example.com:8080" hoặc "socks5://..."
    username: str = ""
    password: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProxyConfig":
        return cls(
            server=data.get("server", ""),
            username=data.get("username", ""),
            password=data.get("password", ""),
        )

    def is_valid(self) -> bool:
        """Kiểm tra proxy có hợp lệ để sử dụng không."""
        return bool(self.server and self.server.startswith(("http://", "https://", "socks5://", "socks4://")))

    def to_playwright_proxy(self) -> Optional[Dict[str, str]]:
        """Chuyển đổi sang định dạng proxy của Playwright."""
        if not self.is_valid():
            return None
        proxy: Dict[str, str] = {"server": self.server}
        if self.username:
            proxy["username"] = self.username
        if self.password:
            proxy["password"] = self.password
        return proxy

    def display_str(self) -> str:
        """Chuỗi hiển thị ngắn gọn cho UI."""
        if not self.is_valid():
            return "Không dùng proxy"
        proto = self.server.split("://")[0].upper()
        host = self.server.split("://")[-1]
        auth = f" ({self.username})" if self.username else ""
        return f"{proto}: {host}{auth}"


@dataclass
class ProfileConfig:
    """Cấu hình đầy đủ cho một tài khoản/profile."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "Profile Mới"
    profile_dir: str = ""
    ucircle_url: str = "https://ucircle.net/app/c/"
    target_video_id: str = ""
    max_videos: int = 100
    proxy: Optional[ProxyConfig] = None
    enabled: bool = True
    notes: str = ""
    # Cài đặt chạy riêng cho profile
    react_only: bool = True
    element_mode: str = "shuffle"   # shuffle | hoa | tho | kim | thuy | moc
    target_type: str = "wavee"      # wavee | feed
    watch_min_seconds: int = 2
    watch_max_seconds: int = 5
    action_delay_min: int = 1
    action_delay_max: int = 3

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "id": self.id,
            "name": self.name,
            "profile_dir": self.profile_dir,
            "ucircle_url": self.ucircle_url,
            "target_video_id": self.target_video_id,
            "max_videos": self.max_videos,
            "proxy": self.proxy.to_dict() if self.proxy else None,
            "enabled": self.enabled,
            "notes": self.notes,
            "react_only": self.react_only,
            "element_mode": self.element_mode,
            "target_type": self.target_type,
            "watch_min_seconds": self.watch_min_seconds,
            "watch_max_seconds": self.watch_max_seconds,
            "action_delay_min": self.action_delay_min,
            "action_delay_max": self.action_delay_max,
        }
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProfileConfig":
        proxy_data = data.get("proxy")
        proxy = ProxyConfig.from_dict(proxy_data) if proxy_data else None
        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            name=data.get("name", "Profile Mới"),
            profile_dir=data.get("profile_dir", ""),
            ucircle_url=data.get("ucircle_url", "https://ucircle.net/app/c/"),
            target_video_id=data.get("target_video_id", ""),
            max_videos=data.get("max_videos", 100),
            proxy=proxy,
            enabled=data.get("enabled", True),
            notes=data.get("notes", ""),
            react_only=data.get("react_only", True),
            element_mode=data.get("element_mode", "shuffle"),
            target_type=data.get("target_type", "wavee"),
            watch_min_seconds=data.get("watch_min_seconds", 2),
            watch_max_seconds=data.get("watch_max_seconds", 5),
            action_delay_min=data.get("action_delay_min", 1),
            action_delay_max=data.get("action_delay_max", 3),
        )

    def get_display_url(self, max_len: int = 50) -> str:
        """URL rút gọn để hiển thị trên UI."""
        url = self.ucircle_url or ""
        return url[:max_len] + "..." if len(url) > max_len else url

    def get_proxy_display(self) -> str:
        if self.proxy and self.proxy.is_valid():
            return self.proxy.display_str()
        return "Không dùng proxy"


def load_profiles(file_path: str = PROFILES_FILE_PATH) -> List[ProfileConfig]:
    """Tải danh sách profiles từ file JSON."""
    if not os.path.exists(file_path):
        return []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return [ProfileConfig.from_dict(p) for p in data.get("profiles", [])]
    except Exception as e:
        print(f"Lỗi khi đọc file profiles '{file_path}': {e}")
        return []


def save_profiles(profiles: List[ProfileConfig], file_path: str = PROFILES_FILE_PATH) -> bool:
    """Lưu danh sách profiles vào file JSON."""
    try:
        data = {"profiles": [p.to_dict() for p in profiles]}
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Lỗi khi lưu file profiles '{file_path}': {e}")
        return False


def create_profile(name: str = "Profile Mới", profile_dir: str = "", auto_dir: bool = True) -> ProfileConfig:
    """Tạo profile mới với thư mục tự động (nếu auto_dir=True)."""
    profile = ProfileConfig(name=name)
    if auto_dir and not profile_dir:
        safe_name = "".join(c if c.isalnum() else "_" for c in name.lower())[:20]
        profile.profile_dir = f"./browser-profile/{safe_name}_{profile.id}"
    else:
        profile.profile_dir = profile_dir or f"./browser-profile/profile_{profile.id}"
    return profile


def delete_profile(profiles: List[ProfileConfig], profile_id: str) -> List[ProfileConfig]:
    """Xóa profile khỏi danh sách theo ID."""
    return [p for p in profiles if p.id != profile_id]


def get_enabled_profiles(profiles: List[ProfileConfig]) -> List[ProfileConfig]:
    """Lấy danh sách các profile đang được bật."""
    return [p for p in profiles if p.enabled]


def find_profile_by_id(profiles: List[ProfileConfig], profile_id: str) -> Optional[ProfileConfig]:
    """Tìm profile theo ID."""
    for p in profiles:
        if p.id == profile_id:
            return p
    return None


def update_profile(profiles: List[ProfileConfig], updated: ProfileConfig) -> List[ProfileConfig]:
    """Cập nhật một profile trong danh sách."""
    return [updated if p.id == updated.id else p for p in profiles]
