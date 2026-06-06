import time
import numpy as np

from .base_tracker import BaseTracker


class DummyTracker(BaseTracker):
    def __init__(self, config):
        super().__init__(config)
        print(f"[DummyTracker] Initialized.")

    def update(self, dets, img):
        time.sleep(0.005)

        results = []
        for i, det in enumerate(dets):
            x1, y1, x2, y2 = det[:4]

            w = x2 - x1
            h = y2 - y1

            x1 -= w * 0.05
            x2 += w * 0.05
            y1 -= h * 0.05
            y2 += h * 0.05

            offset_x = 0.01 + np.random.uniform(-0.005, 0.005)
            offset_y = 0.01 + np.random.uniform(-0.005, 0.005)

            x1 += offset_x
            y1 += offset_y
            x2 += offset_x
            y2 += offset_y

            x1 = max(0.0, min(x1, 1.0))
            y1 = max(0.0, min(y1, 1.0))
            x2 = max(0.0, min(x2, 1.0))
            y2 = max(0.0, min(y2, 1.0))

            track_id = i + 1
            results.append([x1, y1, x2, y2, track_id])

        return results
