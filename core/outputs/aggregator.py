import multiprocessing as mp
import threading
import time
import cv2
import queue
from core.memory.shared_mem import SharedMemoryReader
from libs.handlers import build_handler


class OutputAggregator(mp.Process):
    def __init__(self, config, result_queue, shm_name):
        super().__init__()
        self.config = config
        self.queue = result_queue
        self.shm_name = shm_name
        self.mode = config.get('mode', 'sync')
        self.fps = config.get('target_fps', 30)
        self.running = True
        self.handlers = []

    def run(self):
        print(f"[Aggregator] Started. Mode: {self.mode}")
        self.lock = threading.Lock()
        self.reader = SharedMemoryReader(self.shm_name)

        for h_cfg in self.config.get('handlers', []):
            if h_cfg.get('enable'):
                try:
                    self.handlers.append(build_handler(h_cfg))
                except Exception as e:
                    print(f"[Aggregator] Handler Load Error: {e}")

        try:
            if self.mode == 'async':
                self._run_async()
            else:
                self._run_sync()
        except KeyboardInterrupt:
            pass
        finally:
            print("[Aggregator] Stopping...")
            for h in self.handlers:
                h.release()
            self.reader.close()
            cv2.destroyAllWindows()

    def _run_sync(self):
        while self.running:
            try:
                data = self.queue.get(timeout=1.0)

                for h in self.handlers:
                    h.handle(data, self.reader)

                if cv2.waitKey(1) == ord('q'):
                    self.running = False

            except queue.Empty:
                continue
            except Exception as e:
                print(f"[Aggregator] Error: {e}")
                break

    def _run_async(self):
        self.latest = None
        threading.Thread(target=self._recv_thread, daemon=True).start()

        interval = 1.0 / self.fps

        while self.running:
            start_time = time.time()

            with self.lock:
                data = self.latest

            if data:
                for h in self.handlers:
                    h.handle(data, self.reader)

            elapsed = time.time() - start_time
            wait_ms = max(1, int((interval - elapsed) * 1000))

            if cv2.waitKey(wait_ms) == ord('q'):
                self.running = False

    def _recv_thread(self):
        while self.running:
            try:
                data = self.queue.get()
                with self.lock:
                    self.latest = data
            except:
                break
