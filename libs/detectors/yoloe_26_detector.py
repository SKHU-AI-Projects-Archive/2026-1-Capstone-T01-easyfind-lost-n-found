import time
import math
import torch
import numpy as np
from .base_detector import BaseDetector
import ultralytics

class YoloE26Detector(BaseDetector):
    def __init__(self, config):
        super().__init__(config)
    
        self.weights_path = config.get('weights_path', 'assets/weights/yolov8s-worldv2.pt')
        self.conf = config.get('conf', 0.25)
        self.iou = config.get('iou', 0.7)
        self.imgsz = config.get('imgsz', 640)
        self.classes = config.get('classes', "")

        self.half = torch.cuda.is_available() # FP32 -> FP16 (메모리 사용량 절반 감소 -> 속도 향상, 추론성능 차이 거의 없음)
        
        if isinstance(self.classes, str):
            # 쉼표로 자르고 공백을 제거하여 리스트 생성
            self.classes = [c.strip() for c in self.classes.split(',')]
        else:
            self.classes = self.classes
        
        self.model = ultralytics.YOLOE(self.weights_path)
        
        # 2. 이미 리스트이므로 []로 감싸지 않고 바로 전달
        if self.classes:
            self.model.set_classes(self.classes)

        if self.classes is not None:
            print(f"[YoloDetector] Loaded {self.weights_path}, detecting classes: {self.classes}")
        else:
            print(f"[YoloDetector] Loaded {self.weights_path}, detecting all classes")

        print(f"[YOLOE] Initialized.")
        # GPU Warm-up
        print(f"[YOLOE] Warming up GPU...")
        dummy_img = np.zeros((self.imgsz, self.imgsz, 3), dtype=np.uint8)
        self.model.predict(dummy_img, imgsz=self.imgsz, half=self.half, verbose=False)
        
        print(f"[YOLOE] Initialized and Warmed up.")


    def detect(self, img):
        """
        img를 넣으면 yolov8s-world.pth를 사용하여 yolo-world detect가 수행된다.

        Returns:
            x1, y1, x2, y2, : bounding box의 각 꼭짓점의 좌표
            0.95, : confidence score
            0.0 : class_id
        """
        if img is None:
            return []
        
        h, w = img.shape[:2]


        # model = ultralytics.YOLOWorld("yolov8s-world.pt") # detect 메서드에서 set_classes를 수행할 경우, 10ms 정도 느려지는 문제 발생 -> 자연어를 한 번만 처리해도 될 것을 img 한 장 마다 수행하기 때문에 느려지는 것으로 판단
        # -> __init__ 내부에 넣어 처음 YOLOWorld가 선언될 때만 실행되도록 한다.
        # super().model.set_classes([insert_class])
        # self.model.set_classes(["person"])

        results = self.model.predict(
            source=img, conf = self.conf, iou = self.iou, imgsz = self.imgsz, half = False, verbose = False)

        for result in results:
            boxes = result.boxes   
            probs = result.probs

        bbox_list = boxes.xyxy.tolist()
        conf_score_list = boxes.conf.tolist()
        class_id_list = boxes.cls.tolist()

        detection_result = []
        for box, conf, cls in zip(bbox_list, conf_score_list, class_id_list):
            x1, y1, x2, y2 = box
            confidence_score = float(conf)
            class_id = int(cls)

            # bbox point normalization
            x1 = max(0.0, min(x1 / w, 1.0))
            y1 = max(0.0, min(y1 / h, 1.0))
            x2 = max(0.0, min(x2 / w, 1.0))
            y2 = max(0.0, min(y2 / h, 1.0))

            # if you want to get detection result, uncomment this two code
            detection_result.append([x1, y1, x2, y2, confidence_score, int(class_id)])

        return detection_result # format : [[x1, y1, x2, y2, 0.95, 0.0]]
        # return [[x1, y1, x2, y2, confidence_score, class_id]]
    
