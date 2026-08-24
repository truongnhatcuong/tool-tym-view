class UCircleSelectors:
    WAVEE_TAB_BTN = 'button[data-tool="wavee"], [data-tool="wavee"], a[data-tool="wavee"]'
    WAVEE_VIDEO_CELL = 'button[data-wavee-grid-cell="true"], [data-wavee-grid-cell="true"]'

    # Selector cho nút react trên Bảng tin (feed posts)
    # Dựa trên HTML thực tế: button[data-nguhanh-main="true"]
    FEED_REACT_BTN = 'button[data-nguhanh-main="true"], button[aria-haspopup="menu"][data-react]'

    # Selector nút "Xem thêm" ở cuối danh sách bài viết
    # Attribute thực tế từ DevTools: data-feed-loadmore="true"
    FEED_LOAD_MORE_BTN = 'button[data-feed-loadmore="true"], button[data-circle-feed-loadmore="true"], [data-feed-loadmore]'

    # Picker ngũ hành sau khi click nút react — thực tế: div[data-nguhanh-tray="true"]
    FEED_REACT_PICKER = 'div[data-nguhanh-tray="true"]'

    # Selector cho nút bấm mở bảng Ngũ hành
    REACT_BTN = 'button[data-wavee-react="true"]'

    # Selector cho container chứa các nút Ngũ hành
    REACT_PICKER = 'div[data-wavee-picker="true"]'

    # Lấy ra 5 nút con (Hỏa, Thổ, Kim, Thủy, Mộc) bên trong picker (Loại trừ nút QOT)
    REACT_ELEMENTS = 'button[data-wavee-element]:not([data-wavee-element="qot"])'

    VIDEO_ELEMENT = 'video, [data-testid*="video"], [data-wavee-video-id]'

    @staticmethod
    def get_specific_video_selector(video_id: str) -> str:
        return (
            f'button[data-wavee-grid-cell="true"][data-wavee-video-id="{video_id}"], '
            f'section[data-wavee-video-id="{video_id}"], '
            f'div[data-wavee-video-id="{video_id}"], '
            f'[data-wavee-video-id="{video_id}"]'
        )
