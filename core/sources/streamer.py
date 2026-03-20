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
        self.shape = (h, w, 3)  # (H, W, C)

        self.running = mp.Event()
        self.running.set()

    def run(self):
        print(f"[SourceStreamer] PID: {self.pid} Started.")

        try:
            source = build_source(self.config)
        except Exception as e:
            print(f"[SourceStreamer] PID: {self.pid} Build Failed: {e}")
            return

        writer = SharedMemoryWriter(
            self.shm_name,
            self.shape,
            buffer_size=self.config.get('buffer_size', 60)
        )

        frame_idx = 0

        try:
            while self.running.is_set():
                t0 = time.time() #read 직전에 시작 시점 기록
                ret, frame = source.read()
                if not ret:
                    break

                if frame.shape != self.shape:
                    frame = cv2.resize(frame, (self.shape[1], self.shape[0]))

                meta = writer.put(frame) # put 이후에 소요시간 계산
                meta['frame_id'] = frame_idx
                meta['timing'] = {'source':time.time() - t0}
                meta['start_time'] = t0

                for q in self.queues:
                    q.put(meta)

                frame_idx += 1

        except Exception as e:
            print(f"[SourceStreamer] PID: {self.pid} Error: {e}")
        finally:
            if hasattr(source, 'release'):
                source.release()
            writer.close()
            print(f"[SourceStreamer] PID: {self.pid} Stopped.")

    def stop(self):
        self.running.clear()
