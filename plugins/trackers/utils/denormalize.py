def denormalize_detections(detection_result, height, width):
    """
    정규화된 detection_result를 실제 픽셀 좌표로 변환합니다.
    
    Args:
        detection_result: [[x1, y1, x2, y2, conf, cls], ...] (정규화된 상태)
        width: 원본 이미지의 가로 너비 (w)
        height: 원본 이미지의 세로 높이 (h)
        
    Returns:
        denorm_result: [[dx1, dy1, dx2, dy2, conf, cls], ...] (픽셀 좌표 상태)
    """
    denorm_result = []
    
    for res in detection_result:
        x1, y1, x2, y2, conf, cls = res
        
        # 1. 정규화된 값에 가로/세로 크기 곱하기
        # 2. 픽셀 좌표이므로 정수형(int)으로 변환 (필요에 따라 선택)
        dx1 = x1 * width
        dy1 = y1 * height
        dx2 = x2 * width
        dy2 = y2 * height
        
        denorm_result.append([dx1, dy1, dx2, dy2, conf, int(cls)])
        
    return denorm_result

# --- 사용 예시 ---
# h, w = img.shape[:2]
# real_coords = denormalize_detections(detection_result, w, h)