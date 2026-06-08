import multiprocessing as mp
import cv2
import time
from core.shared_mem import SharedMemoryWriter
from core.archiver import FrameArchiver
from plugins.sources import build_source

class SourceStreamer(mp.Process):
    def __init__(self, config, shm_name, queues, source_ctrl=None):
        super().__init__()
        self.config = config
        self.shm_name = shm_name
        self.queues = queues
        # archive_source 등 제어 가능한 소스에 주입할 핸들(job_q/pause/stop)
        self.source_ctrl = source_ctrl
        w = config.get('width', 1920)
        h = config.get('height', 1080)
        self.shape = (h, w, 3)

        self.running = mp.Event()
        self.running.set()

    def run(self):
        print(f"[SourceStreamer_] PID: {self.pid} Started for SHM: {self.shm_name}")

        try:
            source = build_source(self.config)
            if self.source_ctrl and hasattr(source, 'set_control'):
                source.set_control(self.source_ctrl.get('job_q'),
                                   self.source_ctrl.get('pause'),
                                   self.source_ctrl.get('stop'))
        except Exception as e:
            print(f"[SourceStreamer_] Build Failed: {e}")
            return

        writer = SharedMemoryWriter(
            self.shm_name,
            self.shape,
            buffer_size=self.config.get('buffer_size', 60)
        )

        # 소급 검색용 아카이버 (LatestSlot 스킵과 무관하게 원본 전 프레임/정확 주기 확보)
        archiver = FrameArchiver(
            self.config.get('id', self.shm_name),
            self.config.get('archive', {}),
            fps=self.config.get('fps', 30),
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

                # 제어 가능한 소스(archive_source)가 부가 메타(검색 정보)를 제공하면 병합
                if hasattr(source, 'consume_meta'):
                    extra = source.consume_meta()
                    if extra:
                        meta.update(extra)

                archiver.write(frame, t0)  # 캡처 시각(epoch) 기준 아카이빙

                for q in self.queues:
                    q.put(meta)

                frame_idx += 1
        finally:
            if hasattr(source, 'release'):
                source.release()
            writer.close()
            archiver.close()
            print(f"[SourceStreamer_] Stopped.")

    def stop(self):
        self.running.clear()
