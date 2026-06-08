import numpy as np
from scipy.optimize import linear_sum_assignment
from .utils.kalman_filter_sort import KalmanFilter
from .base_tracker import BaseTracker

def iou_batch(bb_test, bb_gt):
    if bb_test.size == 0 or bb_gt.size == 0:
        return np.empty((bb_test.shape[0], bb_gt.shape[0]))

    bb_gt = np.expand_dims(bb_gt, 0)
    bb_test = np.expand_dims(bb_test, 1)

    xx1 = np.maximum(bb_test[..., 0], bb_gt[..., 0])
    yy1 = np.maximum(bb_test[..., 1], bb_gt[..., 1])
    xx2 = np.minimum(bb_test[..., 2], bb_gt[..., 2])
    yy2 = np.minimum(bb_test[..., 3], bb_gt[..., 3])

    w = np.maximum(0., xx2 - xx1)
    h = np.maximum(0., yy2 - yy1)
    inter = w * h

    area1 = (bb_test[..., 2] - bb_test[..., 0]) * (bb_test[..., 3] - bb_test[..., 1])
    area2 = (bb_gt[..., 2] - bb_gt[..., 0]) * (bb_gt[..., 3] - bb_gt[..., 1])

    return inter / (area1 + area2 - inter + 1e-6)


class KalmanBoxTracker:
    count = 0

    def __init__(self, bbox, class_id=-1):
        self.kf = KalmanFilter(dim_x=7, dim_z=4)

        # 상태 전이 행렬과 관측 행렬 설정
        self.kf.F = np.array([
            [1, 0, 0, 0, 1, 0, 0],
            [0, 1, 0, 0, 0, 1, 0],
            [0, 0, 1, 0, 0, 0, 1],
            [0, 0, 0, 1, 0, 0, 0],
            [0, 0, 0, 0, 1, 0, 0],
            [0, 0, 0, 0, 0, 1, 0],
            [0, 0, 0, 0, 0, 0, 1],
        ], dtype=float)

        self.kf.H = np.array([
            [1, 0, 0, 0, 0, 0, 0],
            [0, 1, 0, 0, 0, 0, 0],
            [0, 0, 1, 0, 0, 0, 0],
            [0, 0, 0, 1, 0, 0, 0],
        ], dtype=float)

        # 초기화
        self.kf.R[2:, 2:] *= 10.
        self.kf.P[4:, 4:] *= 1000.
        self.kf.P *= 10.
        self.kf.Q[-1, -1] *= 0.01
        self.kf.Q[4:, 4:] *= 0.01
        self.kf.x[:4] = self._bbox_to_z(bbox)

        self.time_since_update = 0
        self.id = KalmanBoxTracker.count
        KalmanBoxTracker.count += 1
        self.hits = 1
        self.hit_streak = 1
        self.age = 0
        self.class_id = int(class_id)

    def update(self, bbox, class_id=None):
        self.time_since_update = 0
        self.hits += 1
        self.hit_streak += 1
        self.kf.update(self._bbox_to_z(bbox))
        if class_id is not None:
            self.class_id = int(class_id)

    def predict(self):
        if (self.kf.x[6] + self.kf.x[2]) <= 0:
            self.kf.x[6] = 0
        self.kf.predict()
        self.age += 1
        self.time_since_update += 1
        return self._x_to_bbox(self.kf.x)

    def get_state(self):
        return self._x_to_bbox(self.kf.x)

    # bbox를 측정 벡터 z로 변환
    @staticmethod
    def _bbox_to_z(bbox):
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        x = bbox[0] + w / 2.0
        y = bbox[1] + h / 2.0
        s = w * h
        r = w / (h + 1e-6)
        return np.array([x, y, s, r]).reshape((4, 1))

    # 상태 벡터 x를 bbox로 변환
    @staticmethod
    def _x_to_bbox(x):
        w = np.sqrt(x[2] * x[3])
        h = x[2] / (w + 1e-6)
        return np.array([
            x[0] - w / 2.0,
            x[1] - h / 2.0,
            x[0] + w / 2.0,
            x[1] + h / 2.0,
        ]).reshape((4,))


class SortTracker(BaseTracker):
    def __init__(self, config):
        super().__init__(config)

        self.max_age = config.get("max_age", 5)
        self.min_hits = config.get("min_hits", 3)
        self.iou_threshold = config.get("iou_threshold", 0.3)

        self.trackers = []
        self.frame_count = 0

        print("[SortTracker] Initialized.")

    def update(self, dets, img=None):
        self.frame_count += 1 # frame count 증가

        # detection에서 bbox와 class_id 추출
        if len(dets) > 0:
            det_bboxes = np.asarray([d[:4] for d in dets], dtype=np.float32)
            det_class_ids = np.asarray([
                d[5] if len(d) > 5 else -1 for d in dets
            ], dtype=np.int32)
        else:
            det_bboxes = np.empty((0, 4), dtype=np.float32)
            det_class_ids = np.empty((0,), dtype=np.int32)

        trks = np.array([t.predict() for t in self.trackers]) if len(self.trackers) > 0 else np.empty((0, 4), dtype=np.float32)

        iou_mat = iou_batch(det_bboxes, trks) if det_bboxes.size and trks.size else np.empty((det_bboxes.shape[0], trks.shape[0]))

        # Hungarian algorithm 적용
        if iou_mat.size > 0:
            row, col = linear_sum_assignment(-iou_mat)
        else:
            row, col = np.array([], dtype=int), np.array([], dtype=int)

        matched, unmatched_dets, unmatched_trks = [], [], []

        # 매칭 결과 처리
        for d in range(len(det_bboxes)):
            if d not in row:
                unmatched_dets.append(d)

        for t in range(len(trks)):
            if t not in col:
                unmatched_trks.append(t)

        for r, c in zip(row, col):
            if iou_mat[r, c] < self.iou_threshold:
                unmatched_dets.append(r)
                unmatched_trks.append(c)
            else:
                matched.append((r, c))

        # 매칭된 트래커 업데이트 및 신규 트래커 생성
        for d, t in matched:
            self.trackers[t].update(det_bboxes[d], det_class_ids[d])

        for idx in unmatched_dets:
            self.trackers.append(KalmanBoxTracker(det_bboxes[idx], det_class_ids[idx]))

        results = []
        alive = []

        for t in self.trackers:
            if t.time_since_update <= self.max_age:
                alive.append(t)
                if t.hits >= self.min_hits or self.frame_count <= self.min_hits:
                    x1, y1, x2, y2 = t.get_state()
                    results.append([x1, y1, x2, y2, t.id, t.class_id])

        self.trackers = alive
        return results
