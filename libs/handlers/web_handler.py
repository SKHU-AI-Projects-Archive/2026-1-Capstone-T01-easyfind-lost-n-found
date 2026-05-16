import cv2
import time
import random
import threading
from flask import Flask, Response, render_template_string, jsonify
from flask_cors import CORS
from .base_handler import BaseHandler

# Global dictionary to store the latest encoded frame for each pipeline
latest_frames = {}
# Global list to store detection history (all abandoned track states 0-3)
detection_history = []
frame_lock = threading.Lock()
history_lock = threading.Lock()

app = Flask(__name__)
CORS(app)

# ... (INDEX_HTML remains same)

@app.route('/')
def index():
    with frame_lock:
        pipe_names = list(latest_frames.keys())
    return render_template_string(INDEX_HTML, pipe_names=pipe_names)

@app.route('/api/cameras')
def get_cameras():
    with frame_lock:
        return {"cameras": list(latest_frames.keys())}

@app.route('/api/detections')
def get_detections():
    with history_lock:
        # Return all collected track history (States 0-3)
        return jsonify(detection_history)

@app.route('/api/alerts')
def get_alerts():
    with history_lock:
        # Return only alerts (States 1: SEPARATED, 2: SUSPECTED, 3: LOST)
        alerts = [item for item in detection_history if item['state'] in ['SEPARATED', 'SUSPECTED', 'LOST']]
        return jsonify(alerts)

def generate_frames(pipe_name):
    # ... (generate_frames logic remains same)
    while True:
        with frame_lock:
            frame = latest_frames.get(pipe_name)
        
        if frame is None:
            time.sleep(0.1)
            continue
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        time.sleep(0.04)

@app.route('/video_feed/<pipe_name>')
def video_feed(pipe_name):
    return Response(generate_frames(pipe_name),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

class WebHandler(BaseHandler):
    _server_started = False
    _server_lock = threading.Lock()

    def __init__(self, config):
        super().__init__(config)
        self.port = config.get('port', 5000)
        self.view_w = config.get('view_width', 640)
        self.view_h = config.get('view_height', 480)
        self.show_info = config.get('show_info', True)
        self.draw_dets = config.get('draw_detections', True)
        self.draw_tracks = config.get('draw_tracks', True)
        
        with WebHandler._server_lock:
            if not WebHandler._server_started:
                threading.Thread(target=self._run_server, daemon=True).start()
                WebHandler._server_started = True

    def _run_server(self):
        import logging
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)
        print(f"[WebHandler] Dashboard available at http://localhost:{self.port}/")
        app.run(host='0.0.0.0', port=self.port, threaded=True, use_reloader=False)

    def handle(self, data, shm_reader):
        original_img = shm_reader.get(data['shm_meta'])
        pipe_name = data.get('pipe_name', 'Unknown')
        tracks_ab = data.get('tracks_ab', []) 

        if tracks_ab:
            self._update_history(pipe_name, tracks_ab)

        h_orig, w_orig = original_img.shape[:2]
        if self.view_w != w_orig or self.view_h != h_orig:
            frame = cv2.resize(original_img, (self.view_w, self.view_h))
        else:
            frame = original_img.copy()

        if self.show_info:
            cv2.putText(frame, f"{pipe_name} | F:{data.get('frame_id', 0)}", (20, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        if self.draw_dets:
            for det in data.get('detections', []):
                x1, y1, x2, y2 = self._to_pixel(det[:4])
                try:
                    cid = int(det[-1])
                except (ValueError, TypeError):
                    cid = hash(det[-1])
                color = self.class_color(cid)
                self.rectangle_dot(frame, x1, y1, x2, y2, color, 2)

        if self.draw_tracks:
            for trk in data.get('tracks', []):
                x1, y1, x2, y2 = self._to_pixel(trk[:4])
                try:
                    tid = int(trk[4])
                except (ValueError, TypeError):
                    tid = 0
                try:
                    cid = int(trk[5])
                except (ValueError, TypeError):
                    cid = hash(trk[5])
                
                color = self.class_color(cid)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(frame, f"ID:{tid}", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        ret, buffer = cv2.imencode('.jpg', frame)
        if ret:
            with frame_lock:
                latest_frames[pipe_name] = buffer.tobytes()

    def _update_history(self, pipe_name, tracks_ab):
        with history_lock:
            current_time = time.strftime("%Y-%m-%d %H:%M:%S")
            for trk in tracks_ab:
                # trk 구조: [x1, y1, x2, y2, track_id, class_name, state]
                # state: WITH_OWNER, SEPARATED, SUSPECTED, LOST
                state = trk[6]
                if state: # state가 존재할 때만 기록
                    track_id = trk[4]
                    # 중복 방지 및 상태 업데이트
                    found = False
                    for item in detection_history:
                        if item['track_id'] == track_id and item['pipe_name'] == pipe_name:
                            item['state'] = state
                            item['last_seen'] = current_time
                            found = True
                            break
                    if not found:
                        detection_history.append({
                            'id': len(detection_history) + 1,
                            'track_id': track_id,
                            'type': trk[5],
                            'pipe_name': pipe_name,
                            'state': state,
                            'first_seen': current_time,
                            'last_seen': current_time
                        })
            if len(detection_history) > 200: # 이력 보관 개수 상향
                detection_history.pop(0)

    def _to_pixel(self, bbox_norm):
        x1 = int(bbox_norm[0] * self.view_w)
        y1 = int(bbox_norm[1] * self.view_h)
        x2 = int(bbox_norm[2] * self.view_w)
        y2 = int(bbox_norm[3] * self.view_h)
        return x1, y1, x2, y2

    def class_color(self, class_id):
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

    def release(self):
        pass
