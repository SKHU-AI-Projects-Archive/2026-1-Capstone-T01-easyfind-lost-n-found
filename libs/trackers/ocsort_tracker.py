"""
    This script is adopted from the SORT script by Alex Bewley alex@bewley.ai
"""
from __future__ import print_function

import numpy as np
from .association import *
from .base_tracker import BaseTracker
from .kalman_filter import KalmanFilter   

def k_previous_obs(observations, cur_age, k):
    if len(observations) == 0:
        return [-1, -1, -1, -1, -1]
    for i in range(k):
        dt = k - i
        if cur_age - dt in observations:
            return observations[cur_age - dt]
    max_age = max(observations.keys())
    return observations[max_age]


def convert_bbox_to_z(bbox):
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    x = bbox[0] + w / 2.
    y = bbox[1] + h / 2.
    s = w * h
    r = w / float(h + 1e-6)
    return np.array([x, y, s, r]).reshape((4, 1))


def convert_x_to_bbox(x, score=None):
    
    #음수 방지
    s = max(x[2], 1e-6)
    r = max(x[3], 1e-6)
    
    w = np.sqrt(s * r)
    h = x[2] / (w + 1e-6)

    if score is None:
        return np.array([x[0] - w / 2., x[1] - h / 2.,
                         x[0] + w / 2., x[1] + h / 2.]).reshape((1, 4))
    else:
        return np.array([x[0] - w / 2., x[1] - h / 2.,
                         x[0] + w / 2., x[1] + h / 2., score]).reshape((1, 5))


def speed_direction(bbox1, bbox2):
    cx1, cy1 = (bbox1[0] + bbox1[2]) / 2.0, (bbox1[1] + bbox1[3]) / 2.0
    cx2, cy2 = (bbox2[0] + bbox2[2]) / 2.0, (bbox2[1] + bbox2[3]) / 2.0
    speed = np.array([cy2 - cy1, cx2 - cx1])
    norm = np.sqrt((cy2 - cy1) ** 2 + (cx2 - cx1) ** 2) + 1e-6
    return speed / norm


class KalmanBoxTracker:
    count = 0

    def __init__(self, bbox, class_id, delta_t=3):
        self.kf = KalmanFilter(dim_x=7, dim_z=4)

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

        self.kf.R[2:, 2:] *= 10.
        self.kf.P[4:, 4:] *= 1000.
        self.kf.P *= 10.
        self.kf.Q[-1, -1] *= 0.01
        self.kf.Q[4:, 4:] *= 0.01

        self.kf.x[:4] = convert_bbox_to_z(bbox)

        self.time_since_update = 0
        self.id = KalmanBoxTracker.count
        KalmanBoxTracker.count += 1
        
        self.class_id = int(class_id)

        self.history = []
        self.hits = 0
        self.hit_streak = 0
        self.age = 0

        self.last_observation = np.array([-1, -1, -1, -1, -1])
        self.observations = {}
        self.history_observations = []
        self.velocity = None
        self.delta_t = delta_t

    def update(self, bbox, score=0):
        if bbox is not None:
            obs = np.array([bbox[0], bbox[1], bbox[2], bbox[3], score])
            if self.last_observation[4] >= 0:
                previous_box = self.last_observation[:4]
                self.velocity = speed_direction(previous_box, bbox)
            self.last_observation = obs
            self.observations[self.age] = obs
            self.history_observations.append(obs)

            self.time_since_update = 0
            self.history = []
            self.hits += 1
            self.hit_streak += 1
            self.kf.update(convert_bbox_to_z(bbox))
        else:
            self.kf.update(np.zeros((4, 1)))

    def predict(self):
        self.kf.predict()
        self.age += 1
        self.time_since_update += 1
        self.history.append(convert_x_to_bbox(self.kf.x))
        return self.history[-1]

    def get_state(self):
        return convert_x_to_bbox(self.kf.x)


ASSO_FUNCS = {
    "iou": iou_batch,
    "giou": giou_batch,
    "ciou": ciou_batch,
    "diou": diou_batch,
    "ct_dist": ct_dist
}


class OCSortTracker(BaseTracker):

    def __init__(self, config):
        super().__init__(config)

        self.max_age = config.get("max_age", 30)
        self.min_hits = config.get("min_hits", 3)
        self.iou_threshold = config.get("iou_threshold", 0.3)

        self.det_thresh = config.get('det_thresh', 0.5)
        self.delta_t = config.get('delta_t', 3)
        self.inertia = config.get('inertia', 0.2)
        self.use_byte = False
        self.asso_func = ASSO_FUNCS["iou"]

        self.classes = config.get('classes', [])
        class_ids = config.get('class_ids', list(range(len(self.classes))))
        self.class_map = dict(zip(class_ids, self.classes))
        self.trackers = []
        self.frame_count = 0

        KalmanBoxTracker.count = 0

    def update(self, dets, img):

        if dets is None or len(dets) == 0:
            return []

        self.frame_count += 1

        dets = np.asarray(dets, dtype=np.float32)

        bboxes = dets[:, :4]
        scores = dets[:, 4]
        class_ids = dets[:,5]

        remain_inds = scores > self.det_thresh
        dets = np.concatenate((bboxes, scores[:, None]), axis=1)
        dets = dets[remain_inds]
        class_ids = class_ids[remain_inds]

        trks = np.zeros((len(self.trackers), 5))
        ret = []

        for t, trk in enumerate(self.trackers):
            pos = trk.predict()[0]
            trks[t][:4] = pos
            trks[t][4] = 0

        velocities = np.array([
            trk.velocity if trk.velocity is not None else [0, 0]
            for trk in self.trackers
        ])
        previous_obs = np.array([
            k_previous_obs(trk.observations, trk.age, self.delta_t)
            for trk in self.trackers
        ]) if len(self.trackers) > 0 else np.zeros((0, 5))

        matched, unmatched_dets, unmatched_trks = associate(
            dets, trks, self.iou_threshold,
            velocities,
            previous_obs,
            self.inertia
        )

        for m in matched:
            self.trackers[m[1]].update(dets[m[0], :4], dets[m[0], 4])
            self.trackers[m[1]].class_id = int(class_ids[m[0]])

        for i in unmatched_dets:
            self.trackers.append(
                KalmanBoxTracker(dets[i, :4], class_ids[i], self.delta_t)
            )

        i = len(self.trackers)
        for trk in reversed(self.trackers):
            d = trk.get_state()[0]
            if (trk.time_since_update < 1) and \
               (trk.hit_streak >= self.min_hits or self.frame_count <= self.min_hits):
                ret.append(np.concatenate((d, [trk.id + 1], [trk.class_id])).reshape(1, -1))
            i -= 1
            if trk.time_since_update > self.max_age:
                self.trackers.pop(i)
        # print("\n", ret)

        if len(ret) > 0:
            output = []
            for r in ret:
                x1, y1, x2, y2, track_id, cls_id = r[0]
                cls_name = self.class_map.get(int(cls_id), int(cls_id))
                output.append([float(x1), float(y1), float(x2), float(y2), int(track_id), cls_name])
            return output
        else:
            return []
        
        
        
