# import torch
# import time
import numpy as np
import cv2
from .base_tracker import BaseTracker

from .deep.feature_extractor import Extractor
from .utils.nn_matching import NearestNeighborDistanceMetric
from .utils.nms import non_max_suppression
from .deep.tracker import Tracker

from .utils.denormalize import denormalize_detections


class Detection(object):
    """
    This class represents a bounding box detection in a single image.

    Parameters
    ----------
    tlwh : array_like
        Bounding box in format `(x, y, w, h)`.
    confidence : float
        Detector confidence score.
    feature : array_like
        A feature vector that describes the object contained in this image.

    Attributes
    ----------
    tlwh : ndarray
        Bounding box in format `(top left x, top left y, width, height)`.
    confidence : ndarray
        Detector confidence score.
    feature : ndarray | NoneType
        A feature vector that describes the object contained in this image.

    """

    def __init__(self, tlwh, confidence, feature):
        self.tlwh = np.asarray(tlwh, dtype=float)
        self.confidence = float(confidence)
        self.feature = np.asarray(feature, dtype=float)

    def to_tlbr(self):
        """Convert bounding box to format `(min x, min y, max x, max y)`, i.e.,
        `(top left, bottom right)`.
        """
        ret = self.tlwh.copy()
        ret[2:] += ret[:2]
        return ret

    def to_xyah(self):
        """Convert bounding box to format `(center x, center y, aspect ratio,
        height)`, where the aspect ratio is `width / height`.
        """
        ret = self.tlwh.copy()
        ret[:2] += ret[2:] / 2
        ret[2] /= ret[3]
        return ret



class DeepSORTTracker(BaseTracker):
    def __init__(self, config):
        super().__init__(config)

        self.model_path = config.get("model_path", 'assets/weights/ckpt.t7')
        self.min_confidence = config.get("min_confidence", 0.3)
        self.nms_max_overlap = config.get("nms_max_overlap", 1.0)
        self.max_dist = config.get("max_dist", 0.2)
        self.nn_budget = config.get("nn_budget", 100)
        self.metric = config.get("metric", "cosine")
        self.use_cuda = config.get("use_cuda", True)
        
        self.extractor = Extractor(self.model_path, use_cuda=self.use_cuda)
        
        max_cosine_distance = self.max_dist
        metric = NearestNeighborDistanceMetric("cosine", max_cosine_distance, self.nn_budget)
        self.tracker = Tracker(metric)

        # 핵심: track_id를 키로, class_id를 값으로 저장하는 메모리
        self.track_class_map = {}

    def update(self, dets, img):
        # print("dets1\n\n\n : " ,dets)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB) 
        if img is None: return np.empty((0, 6))
        self.img_h, self.img_w = img.shape[:2]

        # 1. 전처리 및 배치 특징 추출 준비
        denormalized_list = denormalize_detections(dets, self.img_h, self.img_w)
        # print("d_dets\n\n\n : " ,denormalized_list)
        crops = []
        detection_metadata = [] # conf와 class_id 임시 보관

        for res in denormalized_list:
            x1, y1, x2, y2, conf, cls_id = res
            if conf < self.min_confidence: continue
            
            x1, y1 = max(0, int(x1)), max(0, int(y1))
            x2, y2 = min(self.img_w, int(x2)), min(self.img_h, int(y2))
            
            crop = img[y1:y2, x1:x2]
            if crop.size > 0:
                crops.append(crop)
                detection_metadata.append({ 
                    "tlwh": [x1, y1, x2 - x1, y2 - y1],
                    "conf": conf,
                    "cls_id": cls_id
                })
        

        # 2. 특징 추출 (Batch Inference)
        detections_list = []
        if len(crops) > 0:
            features = self.extractor(crops) # 리스트로 한 번에 전달하여 속도 확보
            for i, feat in enumerate(features):
                metadata = detection_metadata[i]
                det = Detection(metadata["tlwh"], metadata["conf"], feat)
                # Detection 객체에 class_id를 임시로 들고 있게 함 (매칭 후 사용용도)
                det.class_id = metadata["cls_id"]
                detections_list.append(det)

            # NMS 수행
            boxes = np.array([d.tlwh for d in detections_list])
            scores = np.array([d.confidence for d in detections_list])
            indices = non_max_suppression(boxes, self.nms_max_overlap, scores)
            detections_list = [detections_list[i] for i in indices]

        # 3. Tracker 예측 및 업데이트
        self.tracker.predict()
        self.tracker.update(detections_list)

        # 4. 결과 정리 및 Class ID 매핑 관리
        results = []
        current_track_ids = []

        for track in self.tracker.tracks:
            if not track.is_confirmed() or track.time_since_update > 1:
                continue
            
            tlwh = track.to_tlwh()
            x1, y1, x2, y2 = self._tlwh_to_xyxy(tlwh)
            tid = int(track.track_id)
            current_track_ids.append(tid)

            cls_id = self.track_class_map.get(tid, -1)
            
            # # 만약 새로운 트랙이라면, 현재 입력된 detections 중 가장 IOU가 높은 놈의 class_id 부여
            if cls_id == -1 and len(detections_list) > 0:
                # 간단한 IOU 기반 추정 (또는 가장 가까운 거리)
                cls_id = self._assign_class_id(track, detections_list)
                self.track_class_map[tid] = cls_id

            results.append([
                x1 / self.img_w, 
                y1 / self.img_h,
                x2 / self.img_w, 
                y2 / self.img_h,
                int(tid), 
                int(cls_id)
            ])
        # print("last dets \n\n\n: ", results)
        # 5. 메모리 관리 (사라진 트랙 삭제)
        self.track_class_map = {k: v for k, v in self.track_class_map.items() if k in [int(t.track_id) for t in self.tracker.tracks]}

        return np.array(results) if len(results) > 0 else np.empty((0, 6))

    def _assign_class_id(self, track, detections):
        """매칭된 트랙에 클래스 ID를 부여하기 위해 가장 가까운 탐지 결과의 클래스를 반환"""
        best_iou = 0
        assigned_cls = 0
        t_box = track.to_tlwh()
        for d in detections:
            # IOU 계산 로직 (생략 - 라이브러리 iou_matching 사용 가능)
            # 여기서는 단순하게 마지막 매칭된 클래스를 추정하는 용도
            assigned_cls = getattr(d, 'class_id', 0)
        return assigned_cls

    def _tlbr_to_tlwh(self, bbox_tlbr):
        """
        bbox_tlbr: [x1, y1, x2, y2] (Top-Left, Bottom-Right)
        반환값: [x1, y1, w, h] (Top-Left, Width, Height)
        """
        # 원본 데이터 보호를 위해 copy() 사용 권장
        bbox_tlwh = bbox_tlbr.copy().astype(float) 
        
        # Width = x2 - x1
        bbox_tlwh[:, 2] = bbox_tlbr[:, 2] - bbox_tlbr[:, 0]
        # Height = y2 - y1
        bbox_tlwh[:, 3] = bbox_tlbr[:, 3] - bbox_tlbr[:, 1]
        
        return bbox_tlwh

    def _xywh_to_tlwh(self, bbox_xywh): # center x, center y를 받는다. -> 필요 없음
        bbox_xywh[:,0] = bbox_xywh[:,0] - bbox_xywh[:,2]/2.
        bbox_xywh[:,1] = bbox_xywh[:,1] - bbox_xywh[:,3]/2.
        return bbox_xywh

    def _tlwh_to_xyxy(self, bbox_tlwh):
        x,y,w,h = bbox_tlwh
        # x1 = max(int(x),0)
        # x2 = min(int(x+w),self.img_w-1)
        # y1 = max(int(y),0)
        # y2 = min(int(y+h),self.img_h-1)
    
        x1 = x
        y1 = y
        x2 = x+w
        y2 = y+h
        x1 = max(0.0, x1)
        y1 = max(0.0, y1)
        x2 = min(float(self.img_w - 1), x2)
        y2 = min(float(self.img_h - 1), y2)
        return x1,y1,x2,y2
    