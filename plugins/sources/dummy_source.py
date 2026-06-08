import numpy as np
import cv2

from .base_source import BaseSource, RatePacer


class DummySource(BaseSource):
    def __init__(self, config):
        super().__init__(config)
        self.width = config.get('width', 1280)
        self.height = config.get('height', 720)
        self.fps = config.get('fps', 30)
        self.pacer = RatePacer(self.fps)
        self.frame_idx = 0

        self.ball_pos = np.array([100.0, 360.0])
        self.velocity = np.array([15.0, 10.0])
        self.radius = 40

        print(f"[DummySource] Initialized. Output: {self.width}x{self.height} @ {self.fps}fps")

    def read(self):
        self.pacer.wait()

        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)

        self.ball_pos += self.velocity

        if self.ball_pos[0] < self.radius or self.ball_pos[0] > self.width - self.radius:
            self.velocity[0] *= -1
        if self.ball_pos[1] < self.radius or self.ball_pos[1] > self.height - self.radius:
            self.velocity[1] *= -1

        center = tuple(self.ball_pos.astype(int))
        cv2.circle(frame, center, self.radius, (0, 255, 0), -1)

        self.frame_idx += 1

        return True, frame

    def release(self):
        print("[DummySource] Released.")
