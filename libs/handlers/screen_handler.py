import cv2
import time
import random
from .base_handler import BaseHandler

class ScreenHandler(BaseHandler):
    def __init__(self, config):
        super().__init__(config)
        self.base_window_name = config.get('window_name', 'MOT System')
        self.view_w = config.get('view_width', 1280)
        self.view_h = config.get('view_height', 960)
        self.show_info = config.get('show_info', True)
        self.draw_dets = config.get('draw_detections', True)
        self.draw_tracks = config.get('draw_tracks', True)
        # handle cv2 windows using set()
        self.windows = set()

    def handle(self, data, shm_reader):
        original_img = shm_reader.get(data['shm_meta'])

        h_orig, w_orig = original_img.shape[:2]
        if self.view_w != w_orig or self.view_h != h_orig:
            frame = cv2.resize(original_img, (self.view_w, self.view_h))
        else:
            frame = original_img.copy()

        pipe_name = data.get('pipe_name', 'Unknown')
        frame_id = data.get('frame_id', 0)
        detections = data.get('detections', [])
        tracks = data.get('tracks_ab', [])

        # Use pipe_name as window name to create separate windows
        win_name = f"[{pipe_name}] Monitoring"
        if win_name not in self.windows:
            cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(win_name, self.view_w, self.view_h)
            self.windows.add(win_name)

        if self.show_info:
            cv2.putText(frame, f"{pipe_name} | F:{frame_id}", (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            timing = data.get('shm_meta', {}).get('timing', {})
            if timing:
                y_offset = 70
                for key, val in timing.items():
                    cv2.putText(frame, f"{key}: {val*1000:.1f}ms", (20, y_offset),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
                    y_offset += 25
                total = sum(timing.values())
                cv2.putText(frame, f"total: {total*1000:.1f}ms", (20, y_offset),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 255), 2)
                latency = time.time() - data.get('shm_meta', {}).get('start_time', time.time())
                cv2.putText(frame, f"latency: {latency*1000:.1f}ms", (20, y_offset + 25),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 150, 255), 2)

        if self.draw_dets:
            for det in detections:
                x1, y1, x2, y2 = self._to_pixel(det[:4])
                # Ensure cid is an int even if detector returns a string
                try:
                    cid = int(det[-1])
                except (ValueError, TypeError):
                    cid = hash(det[-1])
                color = self.class_color(cid, None)
                self.rectangle_dot(frame, x1, y1, x2, y2, color, 2)

        if self.draw_tracks:
            for trk in tracks:
                x1, y1, x2, y2 = self._to_pixel(trk[:4])
                # trk[4] is track_id, trk[5] is class_id/name
                try:
                    tid = int(trk[4])
                except (ValueError, TypeError):
                    tid = 0
                
                try:
                    cid = int(trk[5])
                except (ValueError, TypeError):
                    cid = hash(trk[5])
                
                state = trk[6] if len(trk) > 6 else None
                color = self.class_color(cid, state)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(frame, f"ID:{tid}", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        cv2.imshow(win_name, frame)

    def _to_pixel(self, bbox_norm, clip=True):
        x1 = int(bbox_norm[0] * self.view_w)
        y1 = int(bbox_norm[1] * self.view_h)
        x2 = int(bbox_norm[2] * self.view_w)
        y2 = int(bbox_norm[3] * self.view_h)

        if clip:
            x1 = max(0, min(x1, self.view_w))
            y1 = max(0, min(y1, self.view_h))
            x2 = max(0, min(x2, self.view_w))
            y2 = max(0, min(y2, self.view_h))
        return x1, y1, x2, y2

    def release(self):
        for win in self.windows:
            cv2.destroyWindow(win)

    ''' 
        track_id별로 랜덤한 컬러 지정 
        (단 시드는 고정)
        => track_id를 seed로 이용
    '''
    '''def track_color(self, track_id):
        random.seed(track_id)
        color = (
            random.randint(0, 255),
            random.randint(0, 255),
            random.randint(0, 255)
        )
        return color'''
    
    ''' class_id를 seed로 하여 클래스별 랜덤한 색을 가지게함 '''
    def class_color(self, class_id, state):

        if state == 'SUSPECTED' or state == 'LOST':
            if state == 'SUSPECTED':
                color = (0, 165, 255)

            elif state == 'LOST':
                color = (0, 0, 255)

        else:
            random.seed(class_id)
            color = (
                random.randint(0, 255),
                random.randint(0, 255),
                random.randint(0, 255)
            )
        return color 
    
    def rectangle_dot(self, frame, x1, y1, x2, y2, color, thickness=2):
        gap = 10
        for x in range(x1, x2, gap):
            upStart = (x, y1)
            upEnd = (x + gap//2, y1)
            downStart = (x, y2)
            downEnd = (x + gap//2, y2)
            cv2.line(frame, upStart, upEnd, color, thickness)
            cv2.line(frame, downStart, downEnd, color, thickness)

        for y in range(y1, y2, 10):
            lStart = (x1, y)
            lEnd = (x1, y + gap//2)
            rStart = (x2, y)
            rEnd = (x2, y + gap//2)
            cv2.line(frame, rStart, rEnd, color, thickness)
            cv2.line(frame, lStart, lEnd, color, thickness)