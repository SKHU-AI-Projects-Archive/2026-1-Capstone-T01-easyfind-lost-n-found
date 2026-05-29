import multiprocessing as mp
import time
from core.memory.shared_mem import SharedMemoryReader
from libs.detectors import build_detector
from libs.trackers import build_tracker
from libs.abandoned import build_abandoned

class PipelineExecutor(mp.Process):
    def __init__(self, config, input_queue, result_queue, shm_name):
        super().__init__()
        self.config = config
        self.name_tag = config.get('name', 'UnknownPipeline')
        self.input_queue = input_queue
        self.result_queue = result_queue
        self.shm_name = shm_name
        self.running = mp.Event()
        self.running.set()

    def run(self):
        print(f"[{self.name_tag}] PID: {self.pid} connecting to {self.shm_name}")
        try:
            reader = SharedMemoryReader(self.shm_name)
            detector = build_detector(self.config['detector'])
            tracker = build_tracker(self.config['tracker'])
            abandoned = build_abandoned(self.config['abandoned'])
            print(f"[{self.name_tag}] PID: {self.pid} Initialized.")
        except Exception as e:
            print(f"[{self.name_tag}] Build Failed: {e}")
            return

        try:
            while self.running.is_set():
                meta = self.input_queue.get()
                if meta is None: break

                img = reader.get(meta)
                t0 = time.time()
                dets = detector.detect(img)
                meta['timing']['detector'] = time.time() - t0

                t0 = time.time()
                tracks = tracker.update(dets, img)
                meta['timing']['tracker'] = time.time() - t0

                abandoned_tracks = abandoned.update(meta['frame_id'], tracks)

                result_package = {
                    'pipe_name': self.name_tag,
                    'frame_id': meta['frame_id'],
                    'detections': dets,
                    'tracks': tracks,
                    'tracks_ab' : abandoned_tracks,
                    'shm_meta': meta,
                    'shm_name': self.shm_name # 데이터 출처 명시
                }

                self.result_queue.put(result_package)

        except Exception as e:
            print(f"[{self.name_tag}] Runtime Error: {e}")
        finally:
            reader.close()
            print(f"[{self.name_tag}] Stopped.")

    def stop(self):
        self.running.clear()
