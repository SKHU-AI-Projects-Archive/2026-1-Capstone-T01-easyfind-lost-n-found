import numpy as np
from ultralytics import YOLO

from .base_detector import BaseDetector


class Yolo11Detector(BaseDetector):
    def __init__(self, config):
        super().__init__(config)
    
        self.weights_path = config.get('weights_path', 'assets/weights/yolo11n.pt')
        self.conf = config.get('conf', 0.25)
        self.iou = config.get('iou', 0.7)
        self.imgsz = config.get('imgsz', 640)
        self.classes = config.get('classes', None)
        
        self.model = YOLO(self.weights_path)
        self.model.to(self.device)

        if self.classes is not None:
            print(f"[YoloDetector] Loaded {self.weights_path} on {self.device}, detecting classes: {self.classes}")
        else:
            print(f"[YoloDetector] Loaded {self.weights_path} on {self.device}, detecting all classes")

    def detect(self, img):
        if img is None:
            return []
        
        h, w = img.shape[:2]
        
        results = self.model.predict(
            img,
            conf=self.conf,
            iou=self.iou,
            imgsz=self.imgsz,
            classes=self.classes,
            device=self.device,
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