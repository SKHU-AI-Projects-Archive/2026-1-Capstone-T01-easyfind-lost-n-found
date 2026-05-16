import multiprocessing as mp
import threading
import time
import cv2
import queue
from core.memory.shared_mem import SharedMemoryReader
from libs.handlers import build_handler

class OutputAggregator(mp.Process):
    def __init__(self, config, result_queue):
        super().__init__()
        self.config = config
        self.queue = result_queue
        self.mode = config.get('mode', 'sync')
        self.fps = config.get('target_fps', 30)
        self.running = True
        self.handlers = []
        self.readers = {}

    def _get_reader(self, shm_name):
        if shm_name not in self.readers:
            self.readers[shm_name] = SharedMemoryReader(shm_name)
        return self.readers[shm_name]

    def run(self):
        print(f"[Aggregator] Started. Multi-SHM Separate Window Mode.")
        self.lock = threading.Lock()
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
            for r in self.readers.values():
                r.close()
            cv2.destroyAllWindows()

    def _run_sync(self):
        while self.running:
            try:
                data = self.queue.get(timeout=1.0)
                shm_name = data.get('shm_name')
                if not shm_name: continue
                
                reader = self._get_reader(shm_name)
                for h in self.handlers:
                    h.handle(data, reader)

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
                shm_name = data.get('shm_name')
                if shm_name:
                    reader = self._get_reader(shm_name)
                    for h in self.handlers: 
                        h.handle(data, reader)
            
            if cv2.waitKey(1) == ord('q'): 
                self.running = False
            
            time.sleep(max(0, interval - (time.time() - start_time)))

    def _recv_thread(self):
        while self.running:
            try:
                data = self.queue.get()
                with self.lock: 
                    self.latest = data
            except: 
                break
