from multiprocessing import shared_memory
import numpy as np
import time

class SharedMemoryWriter:
    def __init__(self, shm_name, shape, dtype=np.uint8, buffer_size=60):
        self.shm_name = shm_name
        self.shape = shape
        self.dtype = dtype
        self.buffer_size = buffer_size
        
        self.frame_nbytes = int(np.prod(shape) * np.dtype(dtype).itemsize)
        self.total_size = self.frame_nbytes * buffer_size
        
        try:
            self.shm = shared_memory.SharedMemory(name=shm_name, create=True, size=self.total_size)
        except FileExistsError:
            # 이미 존재(이전 실행 잔존/좀비). Windows는 unlink()가 무효라 재생성이 실패하므로
            # 동일 크기 이상이면 기존 세그먼트를 재사용한다. (POSIX는 부족 시 unlink 후 재생성)
            existing = shared_memory.SharedMemory(name=shm_name, create=False)
            if existing.size >= self.total_size:
                self.shm = existing
                print(f"[Writer] Reusing existing SharedMemory '{shm_name}' ({existing.size} bytes)")
            else:
                existing.close()
                try:
                    existing.unlink()
                except Exception:
                    pass
                self.shm = shared_memory.SharedMemory(name=shm_name, create=True, size=self.total_size)

        self.cursor = 0
        print(f"[Writer] Initialized SharedMemory '{shm_name}'")

    def put(self, frame):
        if frame.shape != self.shape:
            raise ValueError(f"Frame shape mismatch! Expected {self.shape}, got {frame.shape}")

        start_offset = self.cursor * self.frame_nbytes
        shared_arr = np.ndarray(self.shape, dtype=self.dtype, buffer=self.shm.buf, offset=start_offset)
        shared_arr[:] = frame[:]

        metadata = {
            'shm_name': self.shm_name,
            'index': self.cursor,
            'shape': self.shape,
            'dtype_str': np.dtype(self.dtype).str,
            'timestamp': time.time()
        }
        self.cursor = (self.cursor + 1) % self.buffer_size
        return metadata

    def close(self):
        try:
            self.shm.close()
            self.shm.unlink()
            print(f"[Writer] Unlinked SharedMemory '{self.shm_name}'")
        except:
            pass


class SharedMemoryReader:
    def __init__(self, shm_name, dtype=np.uint8, max_retries=50):
        self.shm_name = shm_name
        self.dtype = dtype
        
        self.shm = None
        for _ in range(max_retries):
            try:
                self.shm = shared_memory.SharedMemory(name=shm_name)
                break 
            except FileNotFoundError:
                time.sleep(0.1)
        
        if self.shm is None:
            raise FileNotFoundError(f"[Reader] Timeout! SharedMemory '{shm_name}' not found after retries.")

    def get(self, metadata):
        shape = metadata['shape']
        dtype_str = metadata.get('dtype_str', '|u1') 
        dtype = np.dtype(dtype_str)
        frame_bytes = int(np.prod(shape) * dtype.itemsize)
        offset = metadata['index'] * frame_bytes

        # Create a view first
        shared_img = np.ndarray(shape, dtype=dtype, buffer=self.shm.buf, offset=offset)
        # Return a copy to ensure the data doesn't change if the writer overwrites this buffer index
        return shared_img.copy()

    def close(self):
        if self.shm:
            self.shm.close()