import os
import cv2
from .base_source import BaseSource, RatePacer


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
        # config의 fps가 우선, 없으면 영상 원본 fps. 둘 다 무효면 30으로 폴백.
        self.fps = config.get("fps", video_fps) or 30
        if self.fps <= 0:
            self.fps = 30
        self.pacer = RatePacer(self.fps)
        print(f"[VideoSource] Initialized: {self.video_path} "
              f"(source_fps={video_fps}, play_fps={self.fps})")

    def read(self):
        self.pacer.wait()
        ret, frame = self.cap.read()
        if not ret and self.loop:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.cap.read()
        return ret, frame
    
    def release(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        print("[VideoSource] Released.")