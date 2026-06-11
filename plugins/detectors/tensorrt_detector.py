import numpy as np
from ultralytics import YOLO

from .base_detector import BaseDetector


class TensorRTDetector(BaseDetector):
    def __init__(self, config):
        super().__init__(config)
    
        self.weights_path = config.get('weights_path', 'assets/weights/model.engine')
        self.conf = config.get('conf', 0.25)
        self.iou = config.get('iou', 0.7)
        self.imgsz = config.get('imgsz', 640)
        self.classes = config.get('classes', None)
        
        # Load the TensorRT engine
        self.model = YOLO(self.weights_path, task='detect')

        if self.classes is not None:
            print(f"[TensorRTDetector] Loaded {self.weights_path} on {self.device}, detecting classes: {self.classes}")
        else:
            print(f"[TensorRTDetector] Loaded {self.weights_path} on {self.device}, detecting all classes")

        # GPU Warm-up (Crucial for TensorRT engines)
        print(f"[TensorRTDetector] Warming up {self.device}...")
        dummy_img = np.zeros((self.imgsz, self.imgsz, 3), dtype=np.uint8)
        self.model.predict(dummy_img, imgsz=self.imgsz, device=self.device, verbose=False)
        print(f"[TensorRTDetector] Initialized and Warmed up.")

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
            
            # bbox point normalization to [0.0, 1.0]
            nx1 = max(0.0, min(x1 / w, 1.0))
            ny1 = max(0.0, min(y1 / h, 1.0))
            nx2 = max(0.0, min(x2 / w, 1.0))
            ny2 = max(0.0, min(y2 / h, 1.0))
            
            detections.append([nx1, ny1, nx2, ny2, conf, cls_id])
        
        return detections
