import time
import math
import torch
import numpy as np

from .base_detector import BaseDetector
import ultralytics

class YOLOWorldDetector(BaseDetector):
    def __init__(self, config):
        super().__init__(config)
    
        self.weights_path = config.get('weights_path', 'assets/weights/yolov8s-worldv2.pt')
        self.conf = config.get('conf', 0.25)
        self.iou = config.get('iou', 0.7)
        self.imgsz = config.get('imgsz', 640)
        self.classes = config.get('classes', "")
        
        if isinstance(self.classes, str):
            # 쉼표로 자르고 공백을 제거하여 리스트 생성
            self.classes = [c.strip() for c in self.classes.split(',')]
        else:
            self.classes = self.classes
        
        self.model = ultralytics.YOLOWorld(self.weights_path)
        self.model.to(self.device)

        # 2. 이미 리스트이므로 []로 감싸지 않고 바로 전달
        if self.classes:
            self.model.set_classes(self.classes)

        if self.classes is not None:
            print(f"[YoloDetector] Loaded {self.weights_path} on {self.device}, detecting classes: {self.classes}")
        else:
            print(f"[YoloDetector] Loaded {self.weights_path} on {self.device}, detecting all classes")

        # GPU Warm-up
        print(f"[YOLO World] Warming up {self.device}...")
        dummy_img = np.zeros((self.imgsz, self.imgsz, 3), dtype=np.uint8)
        self.model.predict(dummy_img, imgsz=self.imgsz, device=self.device, verbose=False)
        
        print(f"[YOLO World] Initialized and Warmed up.")


    def detect(self, img):
        """
        Detects objects in the given image using YOLO World.
        """
        if img is None:
            return []
        
        h, w = img.shape[:2]

        # Use positional argument for consistency with other detectors
        # and to ensure ultralytics treats it as a single image.
        results = self.model.predict(
            img,
            conf=self.conf,
            iou=self.iou,
            imgsz=self.imgsz,
            device=self.device,
            verbose=False # Set to False to reduce console noise
        )

        if not results or len(results[0].boxes) == 0:
            return []

        detection_result = []
        # Process only the first result since we passed a single image
        for box in results[0].boxes:
            # Extract coordinates, confidence and class id
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            conf = float(box.conf[0])
            cls_id = int(box.cls[0])

            # bbox point normalization to [0.0, 1.0]
            nx1 = max(0.0, min(x1 / w, 1.0))
            ny1 = max(0.0, min(y1 / h, 1.0))
            nx2 = max(0.0, min(x2 / w, 1.0))
            ny2 = max(0.0, min(y2 / h, 1.0))

            detection_result.append([nx1, ny1, nx2, ny2, conf, cls_id])

        return detection_result
        # return [[x1, y1, x2, y2, confidence_score, class_id]]
    
