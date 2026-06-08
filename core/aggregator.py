import multiprocessing as mp
import threading
import time
import cv2
import queue
from core.shared_mem import SharedMemoryReader
from plugins.handlers import build_handler

class OutputAggregator(mp.Process):
    def __init__(self, config, result_queue, search_ctx=None):
        super().__init__()
        self.config = config
        self.queue = result_queue
        self.mode = config.get('mode', 'sync')
        self.fps = config.get('target_fps', 30)
        self.running = True
        self.handlers = []
        self.readers = {}
        # 검색 제어 핸들(job_queue/pause/stop) — WebHandler의 Flask 라우트가 사용
        self.search_ctx = search_ctx

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

        # 검색 제어 핸들을 WebHandler(Flask 라우트)에 주입
        if self.search_ctx:
            for h in self.handlers:
                if hasattr(h, 'set_search_context'):
                    h.set_search_context(self.search_ctx)

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

    def _dispatch_search(self, data):
        """검색 결과(kind='search')는 handle_search를 가진 핸들러(WebHandler)로 전달."""
        for h in self.handlers:
            if hasattr(h, 'handle_search'):
                h.handle_search(data)

    def _run_sync(self):
        while self.running:
            try:
                data = self.queue.get(timeout=1.0)
                if data.get('kind') == 'search':
                    self._dispatch_search(data)
                    continue
                # live: handler가 느릴 경우 쌓인 구형 결과를 폐기하고 최신만 보존
                # (검색 결과가 섞여 있으면 버리지 않고 그때그때 처리)
                while True:
                    try:
                        nxt = self.queue.get_nowait()
                    except queue.Empty:
                        break
                    if nxt.get('kind') == 'search':
                        self._dispatch_search(nxt)
                    else:
                        data = nxt
                shm_name = data.get('shm_name')
                if not shm_name: continue

                try:
                    reader = self._get_reader(shm_name)
                    for h in self.handlers:
                        h.handle(data, reader)
                except FileNotFoundError:
                    # 카메라 소스가 아직 준비되지 않았을 때 시스템이 죽지 않도록 예외 처리
                    continue

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
                    try:
                        reader = self._get_reader(shm_name)
                        for h in self.handlers: 
                            h.handle(data, reader)
                    except FileNotFoundError:
                        pass
            
            if cv2.waitKey(1) == ord('q'): 
                self.running = False
            
            time.sleep(max(0, interval - (time.time() - start_time)))

    def _recv_thread(self):
        while self.running:
            try:
                data = self.queue.get()
                if data.get('kind') == 'search':
                    self._dispatch_search(data)
                    continue
                with self.lock:
                    self.latest = data
            except:
                break
