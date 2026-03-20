import time
import math

from .base_detector import BaseDetector


class DummyDetector(BaseDetector):
    def __init__(self, config):
        super().__init__(config)
        self.config = config
        self.img_width = config.get('img_width', 640)
        self.img_height = config.get('img_height', 360)

        self.angle = 0.0
        self.center_x = 0.5
        self.center_y = 0.5
        self.radius = 0.25
        self.box_w = 0.1
        self.box_h = 0.15

        print(f"[DummyDetector] Initialized.")

    def detect(self, img):
        time.sleep(0.03)

        cx = self.center_x + self.radius * math.cos(self.angle)
        cy = self.center_y + self.radius * math.sin(self.angle)

        self.angle += 0.1
        if self.angle > 2 * math.pi:
            self.angle -= 2 * math.pi

        x1 = cx - (self.box_w / 2)
        y1 = cy - (self.box_h / 2)
        x2 = cx + (self.box_w / 2)
        y2 = cy + (self.box_h / 2)

        x1 = max(0.0, min(x1, 1.0))
        y1 = max(0.0, min(y1, 1.0))
        x2 = max(0.0, min(x2, 1.0))
        y2 = max(0.0, min(y2, 1.0))

        return [[x1, y1, x2, y2, 0.95, 0.0]]
