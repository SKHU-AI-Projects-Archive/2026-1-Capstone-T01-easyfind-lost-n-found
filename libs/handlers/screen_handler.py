import cv2
import time
import random
import numpy as np
from .base_handler import BaseHandler


class ScreenHandler(BaseHandler):
    def __init__(self, config):
        super().__init__(config)
        self.window_name = config.get('window_name', 'MOT System')
        self.view_w = config.get('view_width', 1280)
        self.view_h = config.get('view_height', 720)
        self.show_info = config.get('show_info', True)
        self.draw_dets = config.get('draw_detections', True)
        self.draw_tracks = config.get('draw_tracks', True)
        self.table_max_rows = config.get('table_max_rows', 8)
        self.table_scroll = 0
        self._window_ready = False
        self.table_window_name = self.window_name + ' - State Table'

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
        tracks = data.get('tracks', [])

        if self.show_info:
            cv2.putText(frame, f"{pipe_name} | F:{frame_id}", (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            timing = data.get('shm_meta', {}).get('timing', {})
            if timing:
                y_offset = 70
                for key, val in timing.items(): #각 모듈별 시간 시각화
                    cv2.putText(frame, f"{key}: {val*1000:.1f}ms", (20, y_offset),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
                    y_offset += 25
                total = sum(timing.values()) #전체프로세스 소요시간 시각화
                cv2.putText(frame, f"total: {total*1000:.1f}ms", (20, y_offset),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 255), 2)
                latency = time.time() - data.get('shm_meta', {}).get('start_time', time.time())
                cv2.putText(frame, f"latency: {latency*1000:.1f}ms", (20, y_offset + 25),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 150, 255), 2)

        if self.draw_dets:
            for det in detections:
                x1, y1, x2, y2 = self._to_pixel(det[:4])
                cid = int(det[-1])
                color = self.class_color(cid)
                self.rectangle_dot(frame, x1, y1, x2, y2, color, 1)
                #cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

        nearest_info = self._calc_nearest_person(tracks)

        if self.draw_tracks:
            for trk in tracks:
                x1, y1, x2, y2 = self._to_pixel(trk[:4])
                tid = int(trk[4])
                cid = trk[5]
                color = self.class_color(cid)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 1)
                cv2.putText(frame, f"ID:{tid}", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 1)

            self._draw_obj_state(frame, tracks)
            self._draw_nearest_person_line(frame, tracks, nearest_info)

        cv2.imshow(self.window_name, frame)
        self._draw_state_table(tracks, nearest_info)
        if not self._window_ready:
            cv2.setMouseCallback(self.window_name, self._on_mouse)
            cv2.setMouseCallback(self.table_window_name, self._on_mouse)
            self._window_ready = True

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
        cv2.destroyWindow(self.window_name)
        cv2.destroyWindow(self.table_window_name)

    def _draw_obj_state(self, frame, tracks):
        STATE_COLORS = {
            'SEPARATED' : (0, 255, 255),   # yellow
            'STATIC'    : (0, 255, 255),   # yellow
            'SUSPECTED' : (0, 165, 255),   # orange
            'LOST'      : (0, 0, 255),     # red
        }
        for trk in tracks:
            if len(trk) < 7:
                continue
            state = trk[6]
            if state not in STATE_COLORS:
                continue
            x1, y1, x2, y2 = self._to_pixel(trk[:4])
            tid = int(trk[4])
            color = STATE_COLORS[state]
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, f"ID:{tid} [{state}]", (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    def _calc_nearest_person(self, tracks):
        person_tracks = [t for t in tracks if t[5] == 'person']
        obj_tracks    = [t for t in tracks if len(t) >= 7 and t[5] != 'person']
        result = {}
        if not person_tracks:
            return result
        for trk in obj_tracks:
            obj_cx = (trk[0] + trk[2]) / 2
            obj_cy = (trk[1] + trk[3]) / 2
            nearest = min(person_tracks,
                          key=lambda p: ((p[0]+p[2])/2 - obj_cx)**2 + ((p[1]+p[3])/2 - obj_cy)**2)
            dist = (((nearest[0]+nearest[2])/2 - obj_cx)**2 + ((nearest[1]+nearest[3])/2 - obj_cy)**2) ** 0.5
            result[int(trk[4])] = (nearest, dist)
        return result

    def _draw_nearest_person_line(self, frame, tracks, nearest_info):
        for trk in tracks:
            if len(trk) < 7 or trk[5] == 'person':
                continue
            tid = int(trk[4])
            if tid not in nearest_info:
                continue
            nearest, _ = nearest_info[tid]
            ox, oy = self._to_pixel([(trk[0]+trk[2])/2, (trk[1]+trk[3])/2,
                                      (trk[0]+trk[2])/2, (trk[1]+trk[3])/2])[:2]
            px, py = self._to_pixel([(nearest[0]+nearest[2])/2, (nearest[1]+nearest[3])/2,
                                      (nearest[0]+nearest[2])/2, (nearest[1]+nearest[3])/2])[:2]
            cv2.line(frame, (ox, oy), (px, py), (200, 200, 200), 1, cv2.LINE_AA)

    def _on_mouse(self, event, *args, **_):
        flags = args[2] if len(args) > 2 else 0
        if event == cv2.EVENT_MOUSEWHEEL:
            if flags > 0:
                self.table_scroll = max(0, self.table_scroll - 1)
            else:
                self.table_scroll += 1

    def _draw_state_table(self, tracks, nearest_info):
        STATE_COLORS = {
            'WITH_OWNER' : (0, 255, 0),
            'STATIC'     : (0, 255, 255),
            'SEPARATED'  : (0, 255, 255),
            'SUSPECTED'  : (0, 165, 255),
            'LOST'       : (0, 0, 255),
            'UNASSIGNED' : (180, 180, 180),
        }

        row_h   = 20
        col_w   = [40, 80, 90, 55]
        padding = 6
        table_w = sum(col_w) + padding * 2
        table_h = row_h * (self.table_max_rows + 1) + padding * 2

        canvas = np.zeros((table_h, table_w, 3), dtype=np.uint8)
        canvas[:] = (30, 30, 30)

        obj_tracks = [t for t in tracks if len(t) >= 7 and t[5] != 'person']
        total = len(obj_tracks)

        if total > 0:
            self.table_scroll = max(0, min(self.table_scroll, max(0, total - self.table_max_rows)))
            visible = obj_tracks[self.table_scroll : self.table_scroll + self.table_max_rows]
        else:
            visible = []

        headers = ['ID', 'Class', 'State', 'Dist']
        for i, (header, _) in enumerate(zip(headers, col_w)):
            tx = padding + sum(col_w[:i])
            ty = padding + row_h - 4
            cv2.putText(canvas, header, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)

        if total > 0:
            scroll_info = f"{self.table_scroll + 1}-{min(self.table_scroll + self.table_max_rows, total)}/{total}"
            cv2.putText(canvas, scroll_info, (table_w - 55, padding + row_h - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.35, (150, 150, 150), 1)

        cv2.line(canvas, (0, row_h + padding), (table_w, row_h + padding), (100, 100, 100), 1)

        for r, trk in enumerate(visible):
            tid   = int(trk[4])
            cls   = str(trk[5])
            state = trk[6] if trk[6] else 'UNASSIGNED'
            color = STATE_COLORS.get(state, (200, 200, 200))

            dist_str = f"{nearest_info[tid][1]:.2f}" if tid in nearest_info else '-'

            ty = padding + row_h * (r + 2) - 4
            for i, (text, _) in enumerate(zip([str(tid), cls, state, dist_str], col_w)):
                tx = padding + sum(col_w[:i])
                cv2.putText(canvas, text, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

        cv2.imshow(self.table_window_name, canvas)

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
    def class_color(self, class_id):
        random.seed(class_id)
        color = (
            random.randint(0, 255),
            random.randint(0, 255),
            random.randint(0, 255)
        )
        return color 
    
    ''' 점선 그리는 함수 '''
    def rectangle_dot(self, frame, x1, y1, x2, y2, color, thickness=2):
        gap = 10
        # 위, 아래
        for x in range(x1, x2, gap):
            upStart = (x, y1)
            upEnd = (x + gap//2, y1)
            downStart = (x, y2)
            downEnd = (x + gap//2, y2)
            cv2.line(frame, upStart, upEnd, color, thickness)
            cv2.line(frame, downStart, downEnd, color, thickness)

        # 좌, 우
        for y in range(y1, y2, 10):
            lStart = (x1, y)
            lEnd = (x1, y + gap//2)
            rStart = (x2, y)
            rEnd = (x2, y + gap//2)
            cv2.line(frame, rStart, rEnd, color, thickness)
            cv2.line(frame, lStart, lEnd, color, thickness)