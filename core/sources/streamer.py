import multiprocessing as mp
import cv2
import time
from core.memory.shared_mem import SharedMemoryWriter
from libs.sources import build_source

class SourceStreamer(mp.Process):
    def __init__(self, config, shm_name, queues):
        super().__init__()
        self.config = config
        self.shm_name = shm_name
        self.queues = queues
        w = config.get('width', 1920)
        h = config.get('height', 1080)
        self.shape = (h, w, 3)

        self.running = mp.Event()
        self.running.set()

    def run(self):
        print(f"[SourceStreamer_] PID: {self.pid} Started for SHM: {self.shm_name}")

        try:
            source = build_source(self.config)
        except Exception as e:
            print(f"[SourceStreamer_] Build Failed: {e}")
            return

        writer = SharedMemoryWriter(
            self.shm_name,
            self.shape,
            buffer_size=self.config.get('buffer_size', 60)
        )

        frame_idx = 0
        try:
            while self.running.is_set():
                t0 = time.time()
                ret, frame = source.read()
                if not ret:
                    break

                if frame.shape != self.shape:
                    frame = cv2.resize(frame, (self.shape[1], self.shape[0]))

                meta = writer.put(frame)
                meta['frame_id'] = frame_idx
                meta['shm_name'] = self.shm_name  # 데이터 출처 명시
                meta['timing'] = {'source': time.time() - t0}
                meta['start_time'] = t0

                for q in self.queues:
                    q.put(meta)

                frame_idx += 1
        finally:
            if hasattr(source, 'release'):
                source.release()
            writer.close()
            print(f"[SourceStreamer_] Stopped.")

    def stop(self):
        self.running.clear()
