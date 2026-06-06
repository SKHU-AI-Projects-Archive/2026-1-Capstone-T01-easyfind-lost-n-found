import os
import glob
import time
from typing import List
import cv2
from natsort import natsort_keygen
from .base_source import BaseSource


class FolderImageSource(BaseSource):
    def __init__(self, config: dict):
        super().__init__(config)
        self.folder_path: str = config.get("folder_path", "")
        if not self.folder_path:
            raise ValueError("[FolderImageSource] 'folder_path' is required in config.")
        if not os.path.isdir(self.folder_path):
            raise ValueError(f"[FolderImageSource] folder_path not found: {self.folder_path}")
        
        self.fps: float = float(config.get("fps", 30.0))
        if self.fps <= 0:
            raise ValueError(f"[FolderImageSource] fps must be > 0. got {self.fps}")
        
        self.pattern: str = config.get("pattern", "*")
        self.recursive: bool = config.get("recursive", False)
        self.sort_mode: str = config.get("sort", "name").lower()
        self.loop: bool = config.get("loop", True)
        self.drop_if_missing: bool = config.get("drop_if_missing", True)
        
        self.file_idx: int = config.get("start_index", 0)
        self.files: List[str] = self._collect_files()
        
        if not self.files:
            raise ValueError(
                f"[FolderImageSource] No image files found in: {self.folder_path} "
                f"(pattern={self.pattern})"
            )
        
        self._period = 1.0 / self.fps
        self._next_time = time.perf_counter()
        
        print(
            f"[FolderImageSource] Initialized. files={len(self.files)}, "
            f"fps={self.fps}, loop={self.loop}, sort={self.sort_mode}"
        )
    
    def _collect_files(self) -> List[str]:
        patterns = [p.strip() for p in self.pattern.split(";") if p.strip()]
        if not patterns:
            patterns = ["*"]
        
        matches = []
        for pat in patterns:
            if self.recursive:
                path = os.path.join(self.folder_path, "**", pat)
                matches.extend(glob.glob(path, recursive=True))
            else:
                path = os.path.join(self.folder_path, pat)
                matches.extend(glob.glob(path))
        
        matches = [p for p in matches if os.path.isfile(p)]
        
        if self.sort_mode == "natsort":
            matches.sort(key=natsort_keygen())
        else:
            matches.sort()
        
        return matches
    
    def _pace(self):
        now = time.perf_counter()
        if now < self._next_time:
            time.sleep(self._next_time - now)
            now = time.perf_counter()
        self._next_time = max(self._next_time + self._period, now + self._period * 0.25)
    
    def read(self):
        self._pace()
        
        if self.file_idx >= len(self.files):
            if self.loop:
                self.file_idx = 0
            else:
                return False, None
        
        path = self.files[self.file_idx]
        frame = cv2.imread(path, cv2.IMREAD_COLOR)
        self.file_idx += 1
        
        if frame is None:
            msg = f"[FolderImageSource] Failed to read image: {path}"
            if self.drop_if_missing:
                print(msg + " (skip)")
                return self.read()
            raise RuntimeError(msg)
        
        return True, frame
    
    def release(self):
        print("[FolderImageSource] release() called.")