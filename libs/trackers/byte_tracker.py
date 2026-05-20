import numpy as np
from collections import deque
import os
import os.path as osp
import copy
import torch
import torch.nn.functional as F

from collections import OrderedDict
from libs.trackers.utils.kalman_filter_byte import KalmanFilter
import libs.trackers.utils.matching as matching
from .base_tracker import BaseTracker

class TrackState:
    New = 0
    Tracked = 1
    Lost = 2
    Removed = 3

class STrack:
    _count = 0
    shared_kalman = KalmanFilter()
    def __init__(self, tlwh, score, class_id):

        # wait activate
        self._tlwh = np.asarray(tlwh, dtype=float)
        self.kalman_filter = None
        self.mean, self.covariance = None, None
        self.is_activated = False

        self.score = score
        self.class_id = class_id # class_id별 색 지정을 위한 seed로 사용하기 위해 
        self.tracklet_len = 0

        self.track_id = 0
        self.state = TrackState.New

        self.history = OrderedDict()
        self.features = []
        self.curr_feature = None
        self.start_frame = 0
        self.frame_id = 0
        self.time_since_update = 0

        # multi-camera
        self.location = (np.inf, np.inf)

    @property
    def end_frame(self):
        return self.frame_id

    @staticmethod
    def next_id():
        STrack._count += 1
        return STrack._count
    
    def mark_lost(self):
        self.state = TrackState.Lost

    def mark_removed(self):
        self.state = TrackState.Removed

    def predict(self):
        mean_state = self.mean.copy()
        if self.state != TrackState.Tracked:
            mean_state[7] = 0
        self.mean, self.covariance = self.kalman_filter.predict(mean_state, self.covariance)

    @staticmethod
    def multi_predict(stracks):
        if len(stracks) > 0:
            multi_mean = np.asarray([st.mean.copy() for st in stracks])
            multi_covariance = np.asarray([st.covariance for st in stracks])
            for i, st in enumerate(stracks):
                if st.state != TrackState.Tracked:
                    multi_mean[i][7] = 0
            multi_mean, multi_covariance = STrack.shared_kalman.multi_predict(multi_mean, multi_covariance)
            for i, (mean, cov) in enumerate(zip(multi_mean, multi_covariance)):
                stracks[i].mean = mean
                stracks[i].covariance = cov

    def activate(self, kalman_filter, frame_id):
        """Start a new tracklet"""
        self.kalman_filter = kalman_filter
        self.track_id = self.next_id()
        self.mean, self.covariance = self.kalman_filter.initiate(self.tlwh_to_xyah(self._tlwh))

        self.tracklet_len = 0
        self.state = TrackState.Tracked
        if frame_id == 1:
            self.is_activated = True
        #self.is_activated = True
        self.frame_id = frame_id
        self.start_frame = frame_id

    def re_activate(self, new_track, frame_id, new_id=False):
        self.mean, self.covariance = self.kalman_filter.update(
            self.mean, self.covariance, self.tlwh_to_xyah(new_track.tlwh)
        )
        self.tracklet_len = 0
        self.state = TrackState.Tracked
        self.is_activated = True
        self.frame_id = frame_id
        if new_id:
            self.track_id = self.next_id()
        self.score = new_track.score
        self.class_id = new_track.class_id

    def update(self, new_track, frame_id):
        """
        Update a matched track
        :type new_track: STrack
        :type frame_id: int
        :type update_feature: bool
        :return:
        """
        self.frame_id = frame_id
        self.tracklet_len += 1

        new_tlwh = new_track.tlwh
        self.mean, self.covariance = self.kalman_filter.update(
            self.mean, self.covariance, self.tlwh_to_xyah(new_tlwh))
        self.state = TrackState.Tracked
        self.is_activated = True

        self.score = new_track.score
        self.class_id = new_track.class_id

    @property
    # @jit(nopython=True)
    def tlwh(self):
        """Get current position in bounding box format `(top left x, top left y,
                width, height)`.
        """
        if self.mean is None:
            return self._tlwh.copy()
        ret = self.mean[:4].copy()
        ret[2] *= ret[3]
        ret[:2] -= ret[2:] / 2
        return ret

    @property
    # @jit(nopython=True)
    def tlbr(self):
        """Convert bounding box to format `(min x, min y, max x, max y)`, i.e.,
        `(top left, bottom right)`.
        """
        ret = self.tlwh.copy()
        ret[2:] += ret[:2]
        return ret

    @staticmethod
    # @jit(nopython=True)
    def tlwh_to_xyah(tlwh):
        """Convert bounding box to format `(center x, center y, aspect ratio,
        height)`, where the aspect ratio is `width / height`.
        """
        ret = np.asarray(tlwh).copy()
        ret[:2] += ret[2:] / 2
        ret[2] /= ret[3]
        return ret

    def to_xyah(self):
        return self.tlwh_to_xyah(self.tlwh)

    @staticmethod
    # @jit(nopython=True)
    def tlbr_to_tlwh(tlbr):
        ret = np.asarray(tlbr).copy()
        ret[2:] -= ret[:2]
        return ret

    @staticmethod
    # @jit(nopython=True)
    def tlwh_to_tlbr(tlwh):
        ret = np.asarray(tlwh).copy()
        ret[2:] += ret[:2]
        return ret

    def __repr__(self):
        return 'OT_{}_({}-{})'.format(self.track_id, self.start_frame, self.end_frame)


class BYTETracker(BaseTracker):
    def __init__(self, config):
        self.tracked_stracks = []  # type: list[STrack]
        self.lost_stracks = []  # type: list[STrack]
        self.removed_stracks = []  # type: list[STrack]

        self.frame_id = 0
        self.fps = config.get('fps', 30)
        #self.config = config
        self.track_thresh = config.get('track_thresh', 0.5)
        self.det_thresh = self.track_thresh + 0.1
        self.track_buffer = config.get('track_buffer', 30)
        self.buffer_size = int(self.fps / 30.0 * self.track_buffer)
        self.crowd = config.get('crowd', False)
        self.match_thresh = config.get('match_thresh', 0.8)
        self.max_time_lost = self.buffer_size
        self.kalman_filter = KalmanFilter()

        classes_config = config.get('classes', [])
        if isinstance(classes_config, dict):
            self.class_map = {int(k): v for k, v in classes_config.items()}
        else:
            class_ids = config.get('class_ids', list(range(len(classes_config))))
            self.class_map = dict(zip(class_ids, classes_config))
        # 확인용
        print('[BYTE Tracker] Initialized')

    '''def to_ndarray(self, output_resutls):
           #list형태의 output_results를 ndarray 형태로 변환
        if 

        return output_results'''

    # pipeline에서 updatetl img_size 사용안함 => img_info로부터 img_size를 추출
    '''
        yolo의 결과는 x1, y1, x2, y2, score, class_id 이다 
        반면 byte track은 xy, y1, x2, y2, object confidecne, class confidence
        yolo의 score는 obj confidence x class confidence이다 
        => score만 있으면 된다 

        좌표 x1 y1 x2 y2는 정규화 된 상태이다 
        byte tracker는 픽셀좌표를 받는다 => 정규화된 좌표를 픽셀 좌표로 바꿔야한다 
    '''
    def update(self, output_results, img_info):
        self.frame_id += 1
        activated_starcks = []
        refind_stracks = []
        lost_stracks = []
        removed_stracks = []

        '''
            detector에서 나온 output_results는 좌표가 정규화된 상태
            bytetracker는 좌표가 정규화 되지 않은 상태를 받아야한다 
            구조:
                detector -> output_results(좌표 정규화)
                -> tracker(outpt_results의좌표를 정규화 이전 상태로 만들어야함) 
                -> output_stracks(좌표 정규화x) -> output_stracksList(좌표 정규화)
        '''

        '''
            output_results가 list형태이므로 .shape의 사용이 불가능 하다 
            => 해결방법: np.ndarray형태로 바꾸는 함수를 작성하여 적용한다 
        '''
        # list를 np.ndarray형태로 바꿈
        # output_results = self.to_ndarray(output_results)

        # img_info는 이미지 그자체
        if img_info is not None:
            img_h, img_w = img_info.shape[:2] # .shape[:2]
        else:
            img_h = self.config.get('img_height')
            img_w = self.config.get('img_width')
        img_size = (img_h, img_w)

        '''
            원본 byte tracker의 이 코드는 shape가 5라면 스코어가 이미 계산된상태인거고
            6이라면 score를 마지막 2개 값으로 계산한다는 것을 의미한다

        if output_results.shape[1] == 5:
            scores = output_results[:, 4]
            bboxes = output_results[:, :4]
            
        else: # 수정-----------
            output_results = output_results.cpu().numpy()
            # scores = output_results[:, 4] * output_results[:, 5]
            scores = output_results[:, 4]
            bboxes = output_results[:, :4]  # x1y1x2y2
        '''
        # score가 이미 계산되어 나오므로 아래와 같이 처리
        '''
            output_results가 2차원 리스트형태면 numpy형태로 바꾸면되지만
            애초에 비어있는 상태라면 numpy형태로 바꿔도 2차원 형태가 아님
            => too many indices Error 발생 

            output_results가 비어있다면 (0,6)형태의 numpy 배열 생성
        '''
        output_results = np.array(output_results)
        if output_results.size == 0:
            output_results = np.zeros((0, 6), dtype=float)
        scores = output_results[:, 4]
        bboxes = output_results[:, :4]
        class_id = output_results[:, 5]

        # img_h, img_w = img_info[0], img_info[1]
        bboxes = bboxes.copy()
        bboxes[:, 0] *= img_w
        bboxes[:, 1] *= img_h
        bboxes[:, 2] *= img_w
        bboxes[:, 3] *= img_h

        scale = min(img_size[0] / float(img_h), img_size[1] / float(img_w))
        bboxes /= scale

        remain_inds = scores > self.track_thresh
        inds_low = scores > 0.1
        inds_high = scores < self.track_thresh

        inds_second = np.logical_and(inds_low, inds_high)
        dets_second = bboxes[inds_second]
        dets = bboxes[remain_inds]
        scores_keep = scores[remain_inds]
        scores_second = scores[inds_second]
        class_id_keep = class_id[remain_inds]
        class_id_second = class_id[inds_second]

        if len(dets) > 0:
            '''Detections'''
            detections = [STrack(STrack.tlbr_to_tlwh(tlbr), s, cid) for
                          (tlbr, s, cid) in zip(dets, scores_keep, class_id_keep)]
        else:
            detections = []
        # 확인용
        #print('dets: ', dets)
        #print('sorces_keep', scores_keep)
        #print('len(detections)', len(detections))

        ''' Add newly detected tracklets to tracked_stracks'''
        unconfirmed = []
        tracked_stracks = []  # type: list[STrack]
        for track in self.tracked_stracks:
            if not track.is_activated:
                unconfirmed.append(track)
            else:
                tracked_stracks.append(track)

        ''' Step 2: First association, with high score detection boxes'''
        strack_pool = joint_stracks(tracked_stracks, self.lost_stracks)
        # Predict the current location with KF
        STrack.multi_predict(strack_pool)
        dists = matching.iou_distance(strack_pool, detections)

        ''' dists의 결과가 행렬로 나오게된다(행: det / 열: track) 이를 이용하여 np.inf값을 부여 '''
        track_class = np.array([t.class_id for t in strack_pool])[:, None] # 열
        det_class = np.array([d.class_id for d in detections])[None, :] # 행
        class_mismatch = track_class != det_class # filter(다른 클래스면 True)
        dists[class_mismatch] = np.inf

        if not self.crowd: # 군중밀집 상황에서는 confidence score를 이용하지 않는 fuse_score를 이용X
            dists = matching.fuse_score(dists, detections)
        matches, u_track, u_detection = matching.linear_assignment(dists, thresh=self.match_thresh)

        '''
            tracked 상태(이전 프레임에서 정상 추적중, 현재 프레임에서도 detection과 매칭됨) => update
            untracked상태(이전 프레임에서 매칭x: 추적실패, 현재프레임에서 다시 매칭됨) => re_activate
        '''
        for itracked, idet in matches:
            track = strack_pool[itracked]
            det = detections[idet]
            if track.state == TrackState.Tracked:
                track.update(det, self.frame_id)
                activated_starcks.append(track)
            else:
                track.re_activate(det, self.frame_id, new_id=False)
                refind_stracks.append(track)

        ''' Step 3: Second association, with low score detection boxes'''
        # association the untrack to the low score detections
        if len(dets_second) > 0:
            '''Detections'''
            detections_second = [STrack(STrack.tlbr_to_tlwh(tlbr), s, cid) for
                          (tlbr, s, cid) in zip(dets_second, scores_second, class_id_second)]
        else:
            detections_second = []
        r_tracked_stracks = [strack_pool[i] for i in u_track if strack_pool[i].state == TrackState.Tracked]
        dists = matching.iou_distance(r_tracked_stracks, detections_second)

        ''' dists의 결과가 행렬로 나오게된다(행: det / 열: track) 이를 이용하여 np.inf값을 부여  '''
        track_class = np.array([t.class_id for t in r_tracked_stracks])[:, None] # 열
        det_class = np.array([d.class_id for d in detections_second])[None, :] # 행
        class_mismatch = track_class != det_class # mismatch이면 True
        dists[class_mismatch] = np.inf # True인 부분을 inf값으로 처리

        matches, u_track, u_detection_second = matching.linear_assignment(dists, thresh=0.5)
        for itracked, idet in matches:
            track = r_tracked_stracks[itracked]
            det = detections_second[idet]
            if track.state == TrackState.Tracked:
                track.update(det, self.frame_id)
                activated_starcks.append(track)
            else:
                track.re_activate(det, self.frame_id, new_id=False)
                refind_stracks.append(track)

        for it in u_track:
            track = r_tracked_stracks[it]
            if not track.state == TrackState.Lost:
                track.mark_lost()
                lost_stracks.append(track)

        '''Deal with unconfirmed tracks, usually tracks with only one beginning frame'''
        detections = [detections[i] for i in u_detection]
        dists = matching.iou_distance(unconfirmed, detections)
        # fuse_score 제거: low confidence 환경에서 fuse_cost = 1 - (iou_sim * det_score)가
        # thresh(0.7)를 넘어 unconfirmed track이 영구적으로 매칭 불가해지는 문제 방지
        # if not self.crowd:
        #     dists = matching.fuse_score(dists, detections)
        matches, u_unconfirmed, u_detection = matching.linear_assignment(dists, thresh=0.7)
        for itracked, idet in matches:
            unconfirmed[itracked].update(detections[idet], self.frame_id)
            activated_starcks.append(unconfirmed[itracked])
        for it in u_unconfirmed:
            track = unconfirmed[it]
            track.mark_removed()
            removed_stracks.append(track)

        """ Step 4: Init new stracks"""
        for inew in u_detection:
            track = detections[inew]
            # 확인용
            #print('activate try, score', track.score)
            if track.score < self.det_thresh:
                continue
            track.activate(self.kalman_filter, self.frame_id)
            activated_starcks.append(track)
        """ Step 5: Update state"""
        for track in self.lost_stracks:
            if self.frame_id - track.end_frame > self.max_time_lost:
                track.mark_removed()
                removed_stracks.append(track)

        # print('Ramained match {} s'.format(t4-t3))

        self.tracked_stracks = [t for t in self.tracked_stracks if t.state == TrackState.Tracked]
        self.tracked_stracks = joint_stracks(self.tracked_stracks, activated_starcks)
        self.tracked_stracks = joint_stracks(self.tracked_stracks, refind_stracks)
        self.lost_stracks = sub_stracks(self.lost_stracks, self.tracked_stracks)
        self.lost_stracks.extend(lost_stracks)
        self.lost_stracks = sub_stracks(self.lost_stracks, self.removed_stracks)
        self.removed_stracks.extend(removed_stracks)
        self.tracked_stracks, self.lost_stracks = remove_duplicate_stracks(self.tracked_stracks, self.lost_stracks)
        # get scores of lost tracks
        output_stracks = [track for track in self.tracked_stracks if track.is_activated]
        '''
            screen handler에서는 Strack객체를 받아들이지 않기에 오류가 난다 
            Strack의 형태를 리스트로 만들어야 한다 
            output_stracks를 [[x1,y1,x2,y2,track id], [x1,y1,...], ...] 형태로 만들어야 handler에서 처리 가능 
            handler에서는 정규화된 x1 y1 x2 y2를 이용하여 픽셀좌표로 바꾸므로 기존 Strack의 좌표값을 정규화 하는 작업이 필요

            Strack_toList()를 만들어 해결
        '''
        output_stracksList = self.Strack_toList(output_stracks, img_w, img_h)

        return output_stracksList

    def Strack_toList(self, output_stracks, img_w, img_h):
        output_list = []
        for strack in output_stracks:
            x1, y1, x2, y2 = strack.tlbr
            cls_id = int(strack.class_id)
            cls_name = self.class_map.get(cls_id, cls_id)

            output_list.append([
                float(x1 / img_w),
                float(y1 / img_h),
                float(x2 / img_w),
                float(y2 / img_h),
                int(strack.track_id),
                cls_name
            ])

        return output_list


def joint_stracks(tlista, tlistb):
    exists = {}
    res = []
    for t in tlista:
        exists[t.track_id] = 1
        res.append(t)
    for t in tlistb:
        tid = t.track_id
        if not exists.get(tid, 0):
            exists[tid] = 1
            res.append(t)
    return res


def sub_stracks(tlista, tlistb):
    stracks = {}
    for t in tlista:
        stracks[t.track_id] = t
    for t in tlistb:
        tid = t.track_id
        if stracks.get(tid, 0):
            del stracks[tid]
    return list(stracks.values())


def remove_duplicate_stracks(stracksa, stracksb):
    pdist = matching.iou_distance(stracksa, stracksb)
    pairs = np.where(pdist < 0.15)
    dupa, dupb = list(), list()
    for p, q in zip(*pairs):
        timep = stracksa[p].frame_id - stracksa[p].start_frame
        timeq = stracksb[q].frame_id - stracksb[q].start_frame
        if timep > timeq:
            dupb.append(q)
        else:
            dupa.append(p)
    resa = [t for i, t in enumerate(stracksa) if not i in dupa]
    resb = [t for i, t in enumerate(stracksb) if not i in dupb]
    return resa, resb