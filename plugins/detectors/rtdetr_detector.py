import numpy as np
import torch
from ultralytics import RTDETR

from .base_detector import BaseDetector


class RTDETRDetector(BaseDetector):
    def __init__(self, config):
        super().__init__(config)

        self.weights_path = config.get('weights_path', 'assets/weights/rtdetr-l.pt')
        self.conf = config.get('conf', 0.25)
        self.imgsz = config.get('imgsz', 640)
        self.classes = config.get('classes', None)
        self.half = torch.cuda.is_available()

        self.model = RTDETR(self.weights_path)

        if self.classes is not None:
            print(f"[RTDETRDetector] Loaded {self.weights_path}, detecting classes: {self.classes}")
        else:
            print(f"[RTDETRDetector] Loaded {self.weights_path}, detecting all classes")

        print(f"[RTDETRDetector] Warming up GPU...")
        dummy_img = np.zeros((self.imgsz, self.imgsz, 3), dtype=np.uint8)
        self.model.predict(dummy_img, imgsz=self.imgsz, half=self.half, verbose=False)
        print(f"[RTDETRDetector] Initialized and Warmed up.")

    def detect(self, img):
        if img is None:
            return []

        h, w = img.shape[:2]

        results = self.model.predict(
            img,
            conf=self.conf,
            imgsz=self.imgsz,
            classes=self.classes,
            half=self.half,
            verbose=False
        )

        if not results or len(results[0].boxes) == 0:
            return []

        detections = []
        for box in results[0].boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            conf = float(box.conf[0])
            cls_id = int(box.cls[0])

            nx1 = max(0.0, min(x1 / w, 1.0))
            ny1 = max(0.0, min(y1 / h, 1.0))
            nx2 = max(0.0, min(x2 / w, 1.0))
            ny2 = max(0.0, min(y2 / h, 1.0))

            detections.append([nx1, ny1, nx2, ny2, conf, cls_id])

        return detections
