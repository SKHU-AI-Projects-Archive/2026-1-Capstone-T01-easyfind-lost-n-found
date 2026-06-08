import multiprocessing as mp
import time
from pathlib import Path
import cv2
from core.shared_mem import SharedMemoryReader
from plugins.detectors import build_detector
from plugins.trackers import build_tracker
from plugins.abandoned import build_abandoned


class PipelineExecutor(mp.Process):
    """source → detector → (tracker) → (abandoned) → output 파이프라인 실행기.

    tracker/abandoned는 config에 있을 때만 생성한다 (검색 파이프라인은 detector만 사용).
    입력 meta에 'search' 정보가 실려 오면 소급 검색 모드로 동작한다:
      - detector(YOLOWorld)의 프롬프트를 set_classes로 교체(모델은 상주, 재로딩 0)
      - 검출 결과를 kind='search'로 result_queue에 전송 → WebHandler가 수집/노출
    별도 SearchExecutor 없이 기존 executor가 archive_source 파이프라인을 그대로 구동한다.
    """

    def __init__(self, config, input_queue, result_queue, shm_name):
        super().__init__()
        self.config = config
        self.name_tag = config.get('name', 'UnknownPipeline')
        self.input_queue = input_queue
        self.result_queue = result_queue
        self.shm_name = shm_name
        self.thumb_root = config.get('thumb_root', 'search_results')
        self.running = mp.Event()
        self.running.set()
        self._cur_prompt = None

    def run(self):
        print(f"[{self.name_tag}] PID: {self.pid} initializing models...")
        try:
            # 모델을 먼저 빌드한다 (GPU 로딩 동안 SourceStreamer가 SharedMemory를 준비)
            detector = build_detector(self.config['detector'])
            tracker = build_tracker(self.config['tracker']) if self.config.get('tracker') else None
            abandoned = None
            if self.config.get('abandoned'):
                self.config['abandoned']['name'] = self.name_tag
                abandoned = build_abandoned(self.config['abandoned'])

            print(f"[{self.name_tag}] PID: {self.pid} connecting to {self.shm_name}")
            reader = SharedMemoryReader(self.shm_name, max_retries=300)
            print(f"[{self.name_tag}] PID: {self.pid} Initialized "
                  f"(tracker={'Y' if tracker else 'N'}, abandoned={'Y' if abandoned else 'N'}).")
        except Exception as e:
            print(f"[{self.name_tag}] Build Failed: {e}")
            return

        try:
            while self.running.is_set():
                meta = self.input_queue.get()
                if meta is None:
                    break
                img = reader.get(meta)

                if 'search' in meta:
                    self._handle_search(meta, img, detector)
                else:
                    self._handle_live(meta, img, detector, tracker, abandoned)
        except Exception as e:
            print(f"[{self.name_tag}] Runtime Error: {e}")
        finally:
            reader.close()
            if abandoned is not None:
                abandoned.close()
            print(f"[{self.name_tag}] Stopped.")

    def _handle_live(self, meta, img, detector, tracker, abandoned):
        t0 = time.time()
        dets = detector.detect(img)
        meta['timing']['detector'] = time.time() - t0

        if tracker is not None:
            t0 = time.time()
            tracks = tracker.update(dets, img)
            meta['timing']['tracker'] = time.time() - t0
        else:
            tracks = dets

        abandoned_tracks = []
        if abandoned is not None:
            abandoned_tracks = abandoned.update(meta['frame_id'], tracks, img)

        self.result_queue.put({
            'pipe_name': self.name_tag,
            'frame_id': meta['frame_id'],
            'detections': dets,
            'tracks': tracks,
            'tracks_ab': abandoned_tracks,
            'shm_meta': meta,
            'shm_name': self.shm_name,
        })

    def _handle_search(self, meta, img, detector):
        s = meta['search']
        job_id = s['job_id']

        # 공급 종료 신호 프레임
        if s.get('done'):
            self.result_queue.put({'kind': 'search', 'job_id': job_id,
                                   'status': 'done', 'done': True, 'progress': 1.0})
            self._cur_prompt = None
            return

        prompt = s.get('prompt') or 'object'
        if prompt != self._cur_prompt:
            detector.model.set_classes([prompt])   # 프롬프트만 교체 (재로딩 0)
            self._cur_prompt = prompt

        dets = detector.detect(img)
        ts = s.get('ts', meta.get('start_time', 0))
        if dets:
            best = max(dets, key=lambda d: d[4])
            thumb = self._save_thumb(img, dets, job_id, ts)
            self.result_queue.put({
                'kind': 'search', 'job_id': job_id, 'hit': True,
                'ts': ts, 'conf': float(best[4]),
                'bbox': [float(x) for x in best[:4]], 'thumb': thumb,
            })

        total = s.get('total', 0)
        idx = s.get('idx', 0)
        self.result_queue.put({'kind': 'search', 'job_id': job_id, 'status': 'running',
                               'total': total,
                               'progress': (idx + 1) / total if total else 0.0})

    def _save_thumb(self, img, dets, job_id, ts):
        thumb_dir = Path(self.thumb_root) / job_id
        thumb_dir.mkdir(parents=True, exist_ok=True)
        vis = img.copy()
        h, w = vis.shape[:2]
        for d in dets:
            x1, y1, x2, y2 = int(d[0] * w), int(d[1] * h), int(d[2] * w), int(d[3] * h)
            cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 200, 255), 2)
        name = f"{int(ts * 1000)}.jpg"
        cv2.imwrite(str(thumb_dir / name), vis)
        return f"{job_id}/{name}"

    def stop(self):
        self.running.clear()
