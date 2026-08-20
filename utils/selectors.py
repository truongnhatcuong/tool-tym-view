class UCircleSelectors:
    WAVEE_TAB_BTN = 'button[data-tool="wavee"]'
    WAVEE_VIDEO_CELL = 'button[data-wavee-grid-cell="true"]'
    
    # Selector cho nút bấm mở bảng Ngũ hành
    REACT_BTN = 'button[data-wavee-react="true"]'
    
    # Selector cho container chứa các nút Ngũ hành
    REACT_PICKER = 'div[data-wavee-picker="true"]'
    
    # Lấy ra 5 nút con (Hỏa, Thổ, Kim, Thủy, Mộc) bên trong picker (Loại trừ nút QOT)
    REACT_ELEMENTS = 'button[data-wavee-element]:not([data-wavee-element="qot"])'
    
    VIDEO_ELEMENT = 'video, [data-testid*="video"]'
    
    @staticmethod
    def get_specific_video_selector(video_id: str) -> str:
        return f'button[data-wavee-grid-cell="true"][data-wavee-video-id="{video_id}"]'
