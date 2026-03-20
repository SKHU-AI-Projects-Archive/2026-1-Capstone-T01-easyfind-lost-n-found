import os
import time
import cv2
from cv2.gapi import video
from .base_source import BaseSource


class VideoSource(BaseSource):
    def __init__(self, config: dict):
        super().__init__(config)
        
        self.video_path = config.get("video_path", "")
        if not self.video_path or not os.path.isfile(self.video_path):
            raise ValueError(f"[VideoSource] Invalid video_path: {self.video_path}")

        self.loop = config.get("loop", True)
        self.cap = cv2.VideoCapture(self.video_path)
        if not self.cap.isOpened():
                raise RuntimeError(f"[VideoSource] Failed to open: {self.video_path}")

        video_fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.fps = config.get("fps",video_fps)
        self.frame_delay = 1.0 / self.fps if self.fps > 0 else 0
        print(f"[VideoSource] Initialized: {self.video_path} (fps={video_fps})")

    def read(self):
        start = time.time()
        ret, frame = self.cap.read()
        if not ret and self.loop:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.cap.read()
        elapsed = time.time() - start
        time.sleep(max(0,self.frame_delay - elapsed))
        
        return ret, frame   
    
    def release(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        print("[VideoSource] Released.")