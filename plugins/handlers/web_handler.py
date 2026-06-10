import os
import re
import csv
import cv2
import time
import uuid
import random
import threading
from datetime import datetime
from pathlib import Path
from flask import Flask, Response, render_template_string, jsonify, request, send_from_directory
from flask_cors import CORS
from .base_handler import BaseHandler

# ── 실시간(live) 공유 상태 ────────────────────────────────
latest_frames = {}            # {pipe_name: jpeg_bytes}
detection_history = []        # abandoned track 상태 이력
frame_lock = threading.Lock()
history_lock = threading.Lock()
metadata_lock = threading.Lock()

latest_metadata = {
    "pipelines": {},
    "summary": {"suspected": 0, "confirmed": 0},
    "history": []
}

# ── 소급 검색(search) 공유 상태 ───────────────────────────
# 검색 결과는 별도 포트/프로세스가 아니라 이 단일 Flask(:5000)에서 노출된다.
# SearchExecutor → result_queue(kind='search') → Aggregator → WebHandler.handle_search → search_results
search_results = {}           # {job_id: {status, progress, total, hits, groups, ...}}
search_lock = threading.Lock()
_search_ctx = None            # {'job_q', 'pause', 'stop', 'root', 'thumb_root'}

app = Flask(__name__)
CORS(app)


# ── 프롬프트 언어 처리 ────────────────────────────────────
def _has_korean(text):
    return bool(re.search(r'[가-힣]', text or ''))


def normalize_prompt(prompt):
    """검색 프롬프트를 YOLOWorld가 쓰는 영어로 정규화한다.
    영어 등 비한글은 그대로, 한글이면 번역을 시도하고 실패 시 원문을 유지한다."""
    prompt = (prompt or '').strip()
    if not prompt:
        return 'object'
    if not _has_korean(prompt):
        return prompt
    try:
        from deep_translator import GoogleTranslator
        out = GoogleTranslator(source='ko', target='en').translate(prompt)
        return out or prompt
    except Exception as e:
        print(f"[Search] translate failed ({e}); using raw prompt '{prompt}'")
        return prompt


def group_hits(hits, interval):
    """검출된 프레임(hit)들을 연속 구간으로 병합한다.
    간격이 interval*3을 넘으면 새 구간으로 분리 → '이때부터 이때까지' 타임라인."""
    if not hits:
        return []
    hits = sorted(hits, key=lambda h: h['ts'])
    gap = max(interval, 1.0) * 3
    groups, cur = [], None
    for h in hits:
        if cur is None or h['ts'] - cur['end_ts'] > gap:
            if cur:
                groups.append(cur)
            cur = {'start_ts': h['ts'], 'end_ts': h['ts'], 'count': 1,
                   'peak_conf': h['conf'], 'peak_thumb': h['thumb']}
        else:
            cur['end_ts'] = h['ts']
            cur['count'] += 1
            if h['conf'] > cur['peak_conf']:
                cur['peak_conf'] = h['conf']
                cur['peak_thumb'] = h['thumb']
    if cur:
        groups.append(cur)
    return groups


# ── 실시간 라우트 ─────────────────────────────────────────
INDEX_HTML = """
<!DOCTYPE html><html><head><title>Video Stream</title></head>
<body><h1>Multi-Pipeline Video Stream</h1>
{% for name in pipe_names %}<h3>{{ name }}</h3><img src="/video_feed/{{ name }}" width="1280">{% endfor %}
</body></html>
"""


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
        return jsonify(detection_history)


@app.route('/api/alerts')
def get_alerts():
    with history_lock:
        alerts = [i for i in detection_history if i['state'] in ['SUSPECTED', 'LOST']]
        return jsonify(alerts)


def generate_frames(pipe_name):
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


@app.route('/api/status')
def get_status():
    with history_lock:
        per_cam = {}
        for item in detection_history:
            cam = item.get('pipe_name')
            state = item.get('state')
            if cam not in per_cam:
                per_cam[cam] = {'SUSPECTED' : 0, 'LOST' : 0}
            if state == 'SUSPECTED':
                per_cam[cam]['SUSPECTED'] += 1
            if state == 'LOST':
                per_cam[cam]['LOST'] += 1
    with metadata_lock:
        latest_metadata['pipelines'] = per_cam
        latest_metadata['summary']['suspected'] = sum(v.get('SUSPECTED', 0) for v in per_cam.values())
        latest_metadata['summary']['confirmed'] = sum(v.get('LOST', 0) for v in per_cam.values())
        return jsonify(latest_metadata)


# ── 소급 검색 라우트 ──────────────────────────────────────
@app.route('/api/search', methods=['POST'])
def api_search():
    """검색 잡 생성. body: {cam, start_ts, end_ts, prompt, interval_sec}. (ts=epoch초)"""
    if _search_ctx is None:
        return jsonify({"status": "error", "message": "search engine not available"}), 503
    body = request.get_json(silent=True) or {}
    cam = body.get('cam') or body.get('location')
    try:
        start_ts = float(body['start_ts'])
        end_ts = float(body['end_ts'])
    except (KeyError, TypeError, ValueError):
        return jsonify({"status": "error", "message": "start_ts/end_ts (epoch) required"}), 400
    if not cam:
        return jsonify({"status": "error", "message": "cam required"}), 400

    interval = float(body.get('interval_sec', 0) or 0)
    prompt = normalize_prompt(body.get('prompt', ''))
    job_id = uuid.uuid4().hex[:12]

    with search_lock:
        search_results[job_id] = {
            "status": "queued", "progress": 0.0, "total": 0,
            "hits": [], "groups": [], "prompt": prompt,
            "cam": cam, "interval": interval, "done": False,
        }
    _search_ctx['job_q'].put({
        'job_id': job_id, 'root': _search_ctx.get('root', 'archives'),
        'cam': cam, 'start_ts': start_ts, 'end_ts': end_ts,
        'prompt': prompt, 'interval_sec': interval,
    })
    return jsonify({"status": "success", "job_id": job_id, "prompt": prompt})


@app.route('/api/archive_cams')
def api_archive_cams():
    """아카이브가 존재하는 카메라(=검색 가능 대상) 목록."""
    root = Path((_search_ctx or {}).get('root', 'archives'))
    cams = sorted(d.name for d in root.iterdir() if d.is_dir()) if root.exists() else []
    return jsonify({"cams": cams})


@app.route('/api/search/<job_id>', methods=['GET'])
def api_search_status(job_id):
    with search_lock:
        entry = search_results.get(job_id)
        if not entry:
            return jsonify({"status": "error", "message": "unknown job"}), 404
        # 진행 중에도 현재까지의 hit으로 구간을 실시간 계산 → 발견 즉시 표시
        resp = dict(entry)
        resp['groups'] = group_hits(entry.get('hits', []), entry.get('interval', 0))
    return jsonify(resp)


@app.route('/api/search/<job_id>/<action>', methods=['POST'])
def api_search_control(job_id, action):
    """검색 중지/일시정지/재개. 단일 상주 워커이므로 전역 이벤트로 제어."""
    if _search_ctx is None:
        return jsonify({"status": "error"}), 503
    if action == 'stop':
        _search_ctx['stop'].set()
    elif action == 'pause':
        _search_ctx['pause'].set()
    elif action == 'resume':
        _search_ctx['pause'].clear()
    else:
        return jsonify({"status": "error", "message": "bad action"}), 400
    return jsonify({"status": "success", "action": action})


@app.route('/search_thumb/<job_id>/<name>')
def search_thumb(job_id, name):
    thumb_root = (_search_ctx or {}).get('thumb_root', 'search_results')
    directory = os.path.abspath(os.path.join(thumb_root, job_id))
    return send_from_directory(directory, name)


@app.route('/api/obj_img/<pipename>/<obj_id>')
def get_obj_img(pipename, obj_id):
    date_str = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    directory = Path('data/obj-imgs') / pipename / date_str
    return send_from_directory(str(directory.resolve()), f'{obj_id}.jpg')



@app.route('/api/log_search')
def api_log_search():
    start_str = request.args.get('start')
    end_str = request.args.get('end')
    cam_filter = request.args.get('cam', '')
    if not start_str:
        return jsonify({"status": "error", "message": "start required"}), 400
    try:
        start_dt = datetime.strptime(start_str, '%Y-%m-%d %H:%M:%S')
        end_dt = datetime.strptime(end_str, '%Y-%m-%d %H:%M:%S') if end_str else datetime.now()
    except ValueError:
        return jsonify({"status": "error", "message": "invalid datetime format (YYYY-MM-DD HH:MM:SS)"}), 400

    logs_root = Path('data/logs')
    results = []
    if not logs_root.exists():
        return jsonify([])

    # {(pipename, obj_id): best_entry} — LOST가 SUSPECTED보다 우선
    best = {}
    state_priority = {'LOST': 1, 'SUSPECTED': 0}

    for pipename_dir in sorted(logs_root.iterdir()):
        if not pipename_dir.is_dir():
            continue
        if cam_filter and pipename_dir.name != cam_filter:
            continue
        for date_dir in sorted(pipename_dir.iterdir()):
            if not date_dir.is_dir():
                continue
            csv_path = date_dir / 'info.csv'
            if not csv_path.exists():
                continue
            with open(csv_path, 'r', encoding='utf-8') as f:
                for row in csv.DictReader(f):
                    try:
                        row_dt = datetime.strptime(row['time'], '%Y-%m-%d %H:%M:%S')
                    except (ValueError, KeyError):
                        continue
                    if not (start_dt <= row_dt <= end_dt):
                        continue
                    key = (pipename_dir.name, row['obj_id'])
                    state = row.get('state', 'SUSPECTED')
                    entry = {
                        'obj_id': row['obj_id'],
                        'class': row['class'],
                        'time': row['time'],
                        'state': state,
                        'pipename': pipename_dir.name,
                    }
                    existing = best.get(key)
                    if existing is None or state_priority.get(state, 0) > state_priority.get(existing['state'], 0):
                        best[key] = entry

    results = sorted(best.values(), key=lambda x: x['time'])
    return jsonify(results)


@app.route('/api/scene_img/<pipename>/<obj_id>')
def get_scene_img(pipename, obj_id):
    scenes_root = Path('data/scenes') / pipename
    if not scenes_root.exists():
        return jsonify({"error": "not found"}), 404
    for date_dir in sorted(scenes_root.iterdir()):
        if not date_dir.is_dir():
            continue
        for hour_dir in sorted(date_dir.iterdir()):
            if not hour_dir.is_dir():
                continue
            img_path = hour_dir / f'{obj_id}.jpg'
            if img_path.exists():
                return send_from_directory(str(hour_dir.resolve()), f'{obj_id}.jpg')
    return jsonify({"error": "not found"}), 404


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
        self.draw_person = config.get('draw_person', False)

        with WebHandler._server_lock:
            if not WebHandler._server_started:
                threading.Thread(target=self._run_server, daemon=True).start()
                WebHandler._server_started = True

    def set_search_context(self, ctx):
        """Aggregator가 검색 제어 핸들(job_q/pause/stop/root)을 주입한다."""
        global _search_ctx
        _search_ctx = ctx
        print("[WebHandler] Search context attached.")

    def _run_server(self):
        import logging
        logging.getLogger('werkzeug').setLevel(logging.ERROR)
        print(f"[WebHandler] Dashboard available at http://localhost:{self.port}/")
        app.run(host='0.0.0.0', port=self.port, threaded=True, use_reloader=False)

    # ── 검색 결과 수집 (kind='search') ──
    def handle_search(self, data):
        job_id = data.get('job_id')
        if not job_id:
            return
        with search_lock:
            entry = search_results.setdefault(job_id, {
                "status": "running", "progress": 0.0, "total": 0,
                "hits": [], "groups": [], "done": False, "interval": 0,
            })
            if data.get('hit'):
                entry['hits'].append({'ts': data['ts'], 'conf': data['conf'],
                                      'thumb': data['thumb'], 'bbox': data.get('bbox')})
            if 'status' in data:
                entry['status'] = data['status']
            if 'progress' in data:
                entry['progress'] = data['progress']
            if 'total' in data:
                entry['total'] = data['total']
            if data.get('error'):
                entry['error'] = data['error']
            if data.get('done'):
                entry['done'] = True
                # groups는 GET 조회 시 실시간 계산하므로 여기서 별도 계산 불필요

    # ── 실시간 프레임 처리 (kind='live') ──
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
                self.rectangle_dot(frame, x1, y1, x2, y2, self.class_color(cid), 1)

        if self.draw_tracks:
            for trk in data.get('tracks_ab', data.get('tracks', [])):
                x1, y1, x2, y2 = self._to_pixel(trk[:4])
                try:
                    tid = int(trk[4])
                except (ValueError, TypeError):
                    tid = 0
                try:
                    cid = int(trk[5])
                except (ValueError, TypeError):
                    cid = trk[5]
                
                if not self.draw_person and cid == 'person':
                    continue

                state = trk[6] if len(trk) > 6 else None
                color = self.class_color(cid, state)
                label = f"ID:{tid}" if not state else f"ID:{tid} {state}"
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 1)
                cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.3, color, 1)

        ret, buffer = cv2.imencode('.jpg', frame)
        if ret:
            with frame_lock:
                latest_frames[pipe_name] = buffer.tobytes()

    def _update_history(self, pipe_name, tracks_ab):
        with history_lock:
            current_time = time.strftime("%Y-%m-%d %H:%M:%S")
            for trk in tracks_ab:
                state = trk[6]
                if state:
                    track_id = trk[4]
                    found = False
                    for item in detection_history:
                        if item['track_id'] == track_id and item['pipe_name'] == pipe_name:
                            item['state'] = state
                            item['last_seen'] = current_time
                            found = True
                            break
                    if not found:
                        detection_history.append({
                            'id': len(detection_history) + 1, 'track_id': track_id,
                            'type': trk[5], 'pipe_name': pipe_name, 'state': state,
                            'first_seen': current_time, 'last_seen': current_time
                        })
            if len(detection_history) > 200:
                detection_history.pop(0)

    def _to_pixel(self, bbox_norm):
        return (int(bbox_norm[0] * self.view_w), int(bbox_norm[1] * self.view_h),
                int(bbox_norm[2] * self.view_w), int(bbox_norm[3] * self.view_h))

    def class_color(self, class_id, state=None):
        if state == 'SUSPECTED':
            return (0, 165, 255)
        if state == 'LOST':
            return (0, 0, 255)
        random.seed(class_id)
        return (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))

    def rectangle_dot(self, frame, x1, y1, x2, y2, color, thickness=2):
        gap = 10
        for x in range(x1, x2, gap):
            cv2.line(frame, (x, y1), (x + gap // 2, y1), color, thickness)
            cv2.line(frame, (x, y2), (x + gap // 2, y2), color, thickness)
        for y in range(y1, y2, 10):
            cv2.line(frame, (x2, y), (x2, y + gap // 2), color, thickness)
            cv2.line(frame, (x1, y), (x1, y + gap // 2), color, thickness)

    def release(self):
        pass
