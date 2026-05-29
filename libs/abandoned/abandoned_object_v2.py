import os
import time
import math
import numpy as np
import cv2
import csv
from datetime import datetime
from enum import Enum
from pathlib import Path
from scipy.optimize import linear_sum_assignment

class objectState(Enum):
    UNASSIGNED = -1
    WITH_OWNER = 0
    STATIC = 1
    SUSPECTED = 2
    LOST = 3

class objLogger:
    def __init__(self, pipename, logs_folder):
        self.base_folder = Path(logs_folder) / pipename
        self.file = None
        self.writer = None
        self.current_date = None

    def _open_for_date(self, date_str):
        if self.current_date == date_str:
            return
        if self.file:
            self.file.close()
        folder = self.base_folder / date_str
        os.makedirs(folder, exist_ok=True)
        csv_path = str(folder / 'info.csv')
        is_new = not os.path.exists(csv_path)
        self.file = open(csv_path, 'a', newline='', encoding='utf-8')
        self.writer = csv.writer(self.file)
        if is_new:
            self.writer.writerow(['obj_id', 'class', 'time'])
        self.current_date = date_str

    def save(self, obj_id, obj_info):
        date_str = datetime.now().strftime('%Y-%m-%d')
        self._open_for_date(date_str)
        cls = obj_info.get('class')
        timestamp = obj_info.get('last_seen(time)')
        self.writer.writerow([obj_id, cls, timestamp])
        self.file.flush()

    def close(self):
        if self.file:
            self.file.close()

class abandonedObject:
    def __init__(self, config):
        
        self.config = config
        self.fps = config.get('fps', 30)

        self.dist_threshold             = config.get('dist_threshold', 0.05) # distance 정규화된 좌표를 기준으로 설정해야한다 
        self.suspected_threshold_min    = config.get('suspected_threshold_min', 15) # minute : static으로부터 15분
        self.lost_threshold_min         = config.get('lost_threshold_min', 15) # minute : suspected로부터 15분


        self.clean_threshold_sec        = config.get('clean_threshold_sec', 30) # second : last_seen - current frame 가 일정 second를 지나면 딕셔너리에서 삭제 
        self.prev_clean_threshold_sec   = config.get('prev_clean_threshold_sec', 1) # second : last_seen - current frame이 일정 second를 지나면 prev_bbox, prev_last_seen에서 삭제

        self.static_dist_threshold      = config.get('static_dist_threshold', 0.01)
        self.iou_threshold              = config.get('iou_threshold', 0.9)

        self.p_lost_threshold            = config.get('p_lost_threshold', 0.75)

        # 프레임으로 계산하여 처리하는 것이 time함수를 사용하는것보다 안정적
        self.suspected_threshold        = self.suspected_threshold_min * 60 * self.fps
        self.lost_threshold             = self.lost_threshold_min * 60 * self.fps

        self.move_lapse                 = 0.5 * self.fps

        self.clean_threshold            = self.clean_threshold_sec * self.fps
        self.prev_clean_threshold       = self.prev_clean_threshold_sec * self.fps

        self.restore_threshold          = config.get('restore_threshold', 0.7)

        self.alpha                      = config.get('alpha_per_sec', 0.01) / self.fps
        self.beta                       = config.get('beta_per_sec', 0.03) / self.fps

        # owner score 가중치
        self.w_vector                   = config.get('w_vector', 0.4)
        self.w_dist                     = config.get('w_dist',   0.6)

        # 이동벡터를 구하기 위해 이전 bbox를 저장하는 딕셔너리
        self.prev_bbox                  = {}
        self.prev_last_seen             = {}

        # state가 바뀔때마다 다른 딕셔너리로 옮기는 작업보다 간단히 상태만 수정하면 되므로 하나의 딕셔너리로 관리
        self.obj_state                  = {}

        # 누군가 분실물을 가져갔음이 의심되는 시점, 시간, object id를 저장하는 딕셔너리
        # {obj_id : {'frame' : , 'time': }}
        self.picked_up                  = {}

        self.scene_folder = Path(__file__).parent / 'scenes'
        self.obj_imgs_folder = Path(__file__).parent / 'obj-imgs'
        self.logs_folder = Path(__file__).parent / 'logs'

        # logger
        self.pipename = config.get('name', 'default')
        self.logger = objLogger(self.pipename, self.logs_folder)

    def close(self):
        self.logger.close()

    def update(self, frame_id, tracks, img=None):
        '''
            매프레임마다 tracking되는 object들의 상태를 업데이트해나간다 
            state : SEPARATED -> SUSPECTED -> LOST

            objs_state 저장형태 : object_id{
                            'class' : 물체의 종류(detector에서 분류한 class)
                            'state' : 0(with_owenr) 1(separated), 2(suspected), 3(lost)
                            'bbox' : ?, bbox는 seaprated된 순간 갱신한다 -> 가만히 있는 물체의 id스위치가 일어나도 id를 복구하기 위해
                            'owner_scores' : {obj_id : {}, ...}
                            'last_seen' : ?,
                            'last_seen(time) : ?,
                            'lost_start' : ?,
                            'static_start' : ?,}
                - state = 2인경우 class(object의 종류)와 color(추후 색구분/추출하는 방법을 찾는경우 추가) 정보도 추가 
            
        '''
        #1. tracks에서 person, object 분리 
        # 저장형태 : {id1 : track, id2 : track, ...}
        person = {}
        obj = {}
        for track in tracks:
            track_id, cls = track[4], track[5]
            if cls in ('person', 'head'):
                person[track_id] = track
            else:
                obj[track_id] = track

        # 2. restore id 
        # _restore_id를 초반에 실행함으로 보정된 id의 객체의 상태 갱신을 수행할 수 있게한다 
        obj = self._restore_objId(obj)

        # 3. restore가 반영된 new track results를 생성
        new_track_results = list(person.values()) + list(obj.values())

        # 4.
        ''' 
            version2 로직 
                1. is_static을 통한 상태 판단 
                    is_static == False : WITH_OWNER 상태 (임시 owner가 있든 없든 움직임이있는 상태이므로 주인과 있다고 판단)
                    is_static == True : SUSEPCTED (멈춰있는 객체에 대한 경우 전부 의심 상태로 전환 LOST로 가기전 유예상태 )

                2. 분실물일 실시간으로 계산하여 LOST로의 전환 
                    LOST 확률 : w1*s_static 지속 시간 + w2*(1-temp_owner`s stay score) + 
        '''
        for obj_id, obj_track in obj.items(): 

            # 4-1. obj_state 초기화, owner score 업데이트
            self._init_obj_state(frame_id, obj_id, obj_track)
            self._update_owner_score(obj_id, obj_track, person)

            # 4-2. 
            obj_info = self.obj_state[obj_id]

            prev_bbox = self.prev_bbox.get(obj_id)
            curr_bbox = obj_track[:4]

            state = obj_info['state']

            static = self._is_static(curr_bbox, prev_bbox)

            if state == objectState.LOST:
                # 이미 LOST로 상태전이 되었으면 확인할 필요 없음 

                # 가능하다면 추후 조건부 LOST상태 해제 로직 추가 예정 
                continue
            
            # 움직임이 없는 경우 
            if static:
                static_start = obj_info['static_start']
                obj_info['move_start'] = None
                
                # STATIC 상태 전환
                state = obj_info['state']
                if state not in [objectState.SUSPECTED, objectState.LOST]:
                    obj_info['state'] = objectState.STATIC

                # static 시작 지점에서만 static start 갱신
                if static_start is None:
                    obj_info['static_start'] = frame_id

                else:
                    susp_lapse   = frame_id - static_start
                    scores  = obj_info['owner_scores']

                    # lapse가 일정 frame을 넘어가면 분실물일 확률을 계산
                    if susp_lapse >= self.suspected_threshold:
                        p_lost = self._calc_p_lost(scores)
                        # thresh 이상 => SUSEPCTED로 갱신
                        if p_lost >= self.p_lost_threshold:
                            if obj_info['suspected_start'] is None: 
                                obj_info['state'] = objectState.SUSPECTED
                                obj_info['suspected_start'] = frame_id
                                self.logger.save(obj_id, obj_info)
                                self._save_objImg(img, obj_id, curr_bbox)
                                print(f'{obj_id} : turn SUSPECTED')

                    susp_start = obj_info['suspected_start']

                    if susp_start is not None:
                        lost_lapse = frame_id - susp_start
                        if lost_lapse >= self.lost_threshold and obj_info['state'] == objectState.SUSPECTED:
                            obj_info['state'] = objectState.LOST
                            print(f'{obj_id} : turn LOST')  

            # 움직임이 있는 경우     
            else:
                move_start = obj_info['move_start']
                state = obj_info['state']

                if state not in [objectState.SUSPECTED, objectState.LOST]:
                    obj_info['state'] = objectState.WITH_OWNER
                    obj_info['static_start'] = None
                    obj_info['suspected_start'] = None
                    obj_info['move_start'] = None
                    continue

                if move_start is None:
                    obj_info['move_start'] = frame_id
                    continue

                lapse = frame_id - move_start
                if lapse >= self.move_lapse: #누군가 분실물을 가져가는 상황(분실물을 주인이 가져갔을 수 있지만 주인이 아닌사람이 가져갔을 경우도 의심가능) : picked_up 기록, scene저장
                    if self.picked_up.get(obj_id) is None:
                        self._save_pickup(obj_id, frame_id, curr_bbox) 
                        self._save_scene(obj_id, curr_bbox, img)
                        
        
        # 5. 모든 object의 last seen frame 갱신 및 bbox 업데이트
        for obj_id, obj_track in obj.items():
            if obj_id in self.obj_state:
                self.obj_state[obj_id]['last_seen'] = frame_id
                self.obj_state[obj_id]['last_seen(time)'] = time.strftime('%Y-%m-%d %H:%M:%S')

                state = self.obj_state[obj_id]['state']
                if state in [objectState.SUSPECTED, objectState.LOST]:
                    self.obj_state[obj_id]['bbox'] = obj_track[:4]
                    # box기준 주변 장면을 crop한 numpy형태 image갱신
                    scene_np = self._numpy_scene(img, obj_track[:4])
                    self.obj_state[obj_id]['last_crop_np'] = scene_np

        # 6. prev_bbox, prev_last_seen 업데이트
        for track in new_track_results:
            track_id = track[4]
            self.prev_bbox[track_id] = track[:4]
            self.prev_last_seen[track_id] = frame_id
        
        # 7. 저장공간 정리 
        self._clean(frame_id)

        # 8. new track results에 state 정보 추가 -> 화면 출력시 suspected: orange / lost: red 
        results = []
        for track in new_track_results:
            track_id = track[4]
            obj_info = self.obj_state.get(track_id)
            state = obj_info.get('state') if obj_info else None
            owner_scores = obj_info.get('owner_scores', {}) if obj_info else {}
            max_score = max(owner_scores.values(), default=0.0)
            results.append(list(track) + [state.name if state else None, round(max_score, 2)])

        return results
    

    def _init_obj_state(self, frame_id, obj_id, obj_track):
        '''
            obj_state에 obj_id 초기화 
        '''
        if obj_id not in self.obj_state:
            self.obj_state[obj_id] = {
                'class'             : obj_track[5],
                'state'             : objectState.UNASSIGNED,
                'bbox'              : obj_track[:4],
                'last_seen'         : frame_id,
                'last_seen(time)'   : time.strftime('%Y-%m-%d %H:%M:%S'),
                'last_crop_np'      : None,
                'static_start'      : None,
                'suspected_start'   : None,
                'move_start'        : None,
                'owner_scores'       : {},
            }
    

    def _update_owner_score(self, obj_id, obj_track, person):
        '''
            object와 일정 거리 안에 있는 person의 owner score(주인이 있을 것이다라는 신뢰도)를 실시간으로 계산하여 업데이트 
            owner score(신뢰도)의 점진적 상승, 하강

            - 오랜 시간 가까이 있을 수록 +alpha로 인해 owner score(신뢰도) 상승
            - 반대로 지나가는 사람이라면 이후 -beta로 신뢰도 하강 
            - 현재 프레임에서 보이지 않는 id도 감소 필요 (ID switch로 인한 id 소실)

        '''
        obj_bbox = obj_track[:4]
        owner_score = self.obj_state[obj_id]['owner_scores']
        owner_pids = set(owner_score.keys()) | set(person.keys()) # 현재 트랙에서 보이지 않는 pid까지 포함한다 

        for pid in owner_pids:
            # pid가 현재 트랙에 있는 경우 
            if pid in person:
                p_bbox = person[pid][:4]
                distance = calc_distance(obj_bbox, p_bbox)
                # 
                if distance <= self.dist_threshold:
                    owner_score[pid] = min(1.0, owner_score.get(pid, 0.0) + self.alpha)
                # 
                else:
                    owner_score[pid] = max(0.0, owner_score.get(pid, 0.0) - self.beta)
                    if owner_score[pid] == 0.0:
                        owner_score.pop(pid, None)
            
            # pid가 현재 트랙에 없는 경우(현재 프레임에서 보이지 않음 -> ID switch일 가능성도 있음)
            else:
                owner_score[pid] = max(0.0, owner_score.get(pid, 0.0) - self.beta)
                if owner_score[pid] == 0.0:
                    owner_score.pop(pid, None)

        '''for pid, p_track in person.items():
            p_bbox = p_track[:4]

            distance = calc_distance(obj_bbox, p_bbox)
            
            if distance <= self.dist_threshold:
                owner_score[pid] = min(1.0, owner_score.get(pid, 0.0) + self.alpha)
            else:
                owner_score[pid] = max(0.0, owner_score.get(pid, 0.0) - self.beta)
                if owner_score[pid] == 0.0:
                    owner_score.pop(pid, None)

        # 현재 트랙에서 보이지 않는 person에 대한 점진적 감속 필요
        # : ID switch가 일어나 사라진 경우 점수가 멈춘상태 -> 감소를 통한 변경 및 삭제 필요
        for pid, score in owner_score.items():
            if pid not in person:
                owner_score[pid] = max(0.0, owner_score - self.beta)
                if score == 0.0:
                    owner_score.pop(pid, None)'''

    
    def _restore_objId(self, obj):
        '''
            obj => 현재 frame에서 추적된 대상
            obj : {id1 : track, id2 : track, ...}

            SUSPECTED, LOST상태에서의 object는 대부분 이동하지 않은 고정된 상태일 것이다 
            이를 이용하여 prev bbox(object_state['bbox'])와 curr_bbox의 iou를 비교하여 id를 복구한다 
            -> score = (w1 x iou) + (w2 x distance) / (w1 + w2)를 이용하여 복구하는 방향으로 수정 
            복구된 id와 기존 track을 담은 new track results를 return
            tracker의 output results 형태와 동일한 형태로 new track results를 만들어야한다 
            저장형태: [[float(x1 / img_w),
                     float(y1 / img_h),
                     float(x2 / img_w),
                     float(y2 / img_h),
                     int(strack.track_id),
                     int(strack.class_id)], ...] =>  tlbr 형태의 bbox
        '''
        # 현재 id와 복구된 id를 매핑 || {curr_id : restore_id}
        restore_id_map = {}
        # iou 와 distance 가중치
        w_iou, w_dist = 0.7, 0.3
        # math.exp의 k값
        k = 2
        
        curr_ids = [
            curr_id for curr_id in obj.keys()
            if curr_id not in self.obj_state or
              self.obj_state[curr_id]['state'] is not objectState.WITH_OWNER
        ]

        '''1. 복구 대상 수집'''
        restore_ids = []
        restore_bboxes = []
        for obj_id, obj_info in self.obj_state.items():
            state = obj_info['state']

            if state not in [objectState.SUSPECTED, objectState.LOST]:
                continue
            
            if obj_id in obj: # obj(현재 프레임에서 tracking중인 objects)안에 있으면 id switch가 일어난게 아니므로
                continue
            
            # WITH_OWNER가 아니면 bbox를 업데이트하니 상관없지만 혹시모르는 상황을 대비하여 작성
            prev_bbox = obj_info['bbox']
            if prev_bbox is None:
                continue

            # 위의 if문들에 걸러지지 않았다면 id switch가 일어난 것이라고 판단한다 
            restore_ids.append(obj_id)
            restore_bboxes.append(prev_bbox)

        '''2. cost matrix 생성'''
        if restore_ids and curr_ids: # 복구대상이 없거나 첫프레임인경우... 에는 불필 계산할 필요 없음
            cost_matrix = np.zeros((len(restore_ids), len(curr_ids)))

            for i, (prev_bbox, restore_id) in enumerate(zip(restore_bboxes, restore_ids)):
                restore_class = self.obj_state[restore_id]['class']
                for j, curr_id in enumerate(curr_ids):
                    track = obj[curr_id]
                    curr_class = track[5]

                    if curr_class != restore_class:
                        cost_matrix[i][j] = 1.0
                        continue

                    curr_bbox = track[:4]

                    iou = calc_iou(prev_bbox, curr_bbox)
                    distance = calc_distance(prev_bbox, curr_bbox)
                    dist_score = math.exp(k * -distance)

                    score = ((w_iou * iou) + (w_dist * dist_score)) / (w_iou + w_dist)

                    cost_matrix[i][j] = 1 - score
        
            '''3. hungarian matching'''
            row_ind, col_ind = linear_sum_assignment(cost_matrix)

            for row, col in zip(row_ind, col_ind):
                score = 1 - cost_matrix[row][col]
            
                if score >= self.restore_threshold:
                    curr_id = curr_ids[col]
                    restore_id = restore_ids[row]

                    restore_id_map[curr_id] = restore_id

        ''' 4. new_obj 생성 : restore된 id를 반영 '''
        new_obj = {}
        for curr_id, track in obj.items():
            new_track = list(track)
            restored_id = restore_id_map.get(curr_id, curr_id) # restore_id_map에 curr_id와 매핑된 복구할 id가 없다면 현재 curr_id를 restored_id로한다

            # key값이 중복되지않게 해뒀지만 혹시모를 상황을 대비해 같은 key가 2개일때 덮어씌기 방지
            if restored_id in new_obj:
                restored_id = curr_id

            new_track[4] = restored_id
            new_obj[restored_id] = new_track

        return new_obj

    def _clean(self, frame_id):
        '''딕셔너리에 무한히 저장할 수 없으므로 정리해줘야한다 
            1. last seen frame 과 현재 frame을 비교하여 일정 프레임이 지나면 삭제 
                - obj_owner : obj_id를 삭제
                - objs_owners : owner_id 안의 [obj1, 2, 3..] obj들이 모두 사라지면 owner_id를 삭제
                - obj_state : obj_id 삭제 
                - prev_bbox : obj_id 삭제, person_id도 삭제해야한다 => self.prev_last_seen을 따로 만들어 일정 프레임이 지나면 삭제하는 것이 좋아보인다 

        obj_state의 object를 기준으로 한다 => obj_state를 돌면서 last_seen과 현재 frame의 차이를 계산하는 방식 
        '''
        # 1. obj_state기준 object 삭제
        # 1-1 삭제할 조건을 만족하는 id를 수집
        delete_obj_ids = []
        for obj_id, obj_info in self.obj_state.items():
            last_seen = obj_info.get('last_seen') 

            if last_seen is None:
                continue

            lapse = frame_id - last_seen
            if lapse >= self.clean_threshold:
                delete_obj_ids.append(obj_id)

        # 1-2 delete_obj_ids의 obj_id를 각 저장공간에서 삭제
        for obj_id in delete_obj_ids:
            # susepcted, lost 상태였던 object의 트랙이 끊겨 lost 상태가 된다 -> 누군가 가져갔을 가능성이 있으므로 pickup 기록 
            state = self.obj_state[obj_id]['state']
            # state = suspected / lost 이면서 picked_up에 저장되어있지 않은 경우( 움직임으로 누군가 가져갔다고 판단되는 경우 )
            if state in [objectState.SUSPECTED, objectState.LOST] and self.picked_up.get(obj_id) is None:
                self._save_pickup(obj_id)
                self._numpy2img(obj_id)

            self.obj_state.pop(obj_id, None)
            self.prev_bbox.pop(obj_id, None)
            self.prev_last_seen.pop(obj_id, None)
        
        # 2. prev_bbox 정리
        # 2-1 삭제할 조건을 만족하는 id 수집
        delete_prev_ids = []
        for track_id, last_seen in self.prev_last_seen.items():

            if last_seen is None:
                continue

            lapse = frame_id - last_seen

            if lapse >= self.prev_clean_threshold:
                delete_prev_ids.append(track_id)
        
        for track_id in delete_prev_ids:
            self.prev_bbox.pop(track_id, None)
            self.prev_last_seen.pop(track_id, None)


    def _calc_ownerScore(self, obj_id, person_id, obj_bbox, person_bbox):
        '''
            owner_score = w_dist * dist_score + w_vector * vector_sim
        '''
        distance = calc_distance(obj_bbox, person_bbox)
        dist_score = 1 - distance / self.dist_threshold

        prev_obj = self.prev_bbox.get(obj_id)
        prev_person = self.prev_bbox.get(person_id)
        if prev_obj is None or prev_person is None:
            return self.w_dist * dist_score

        obj_mv = calc_motionVector(obj_bbox, prev_obj)
        person_mv = calc_motionVector(person_bbox, prev_person)
        vector_sim = calc_cosineSim(obj_mv, person_mv)

        return self.w_dist * dist_score + self.w_vector * vector_sim
    
    
    def _calc_p_lost(self, owner_scores):
        '''
            움직임이 없다고 판단되는 object에 대하여 분실물 확률(신뢰도 점수)을 계산 
            max owner score가 낮은 상태가 지속된다면 분실물일 가능성이 높아진다 

            - 1 - max owner score 
        '''
        max_score = max(owner_scores.values(), default=0)

        p_lost = 1 - max_score

        return p_lost
    
    
    def _is_static(self, curr_bbox, prev_bbox):
        '''
            curr_bbox가 prev_bbox와 비교했을때 고정된 상태로 볼 수 있는가를 판단
            두 박스의 iou, distance를 구하여 각 threshold를 통해 판단
        '''
        if curr_bbox is None or prev_bbox is None:
            return False

        iou = calc_iou(curr_bbox, prev_bbox)
        distance = calc_distance(curr_bbox, prev_bbox)
        
        if iou >= self.iou_threshold and distance <= self.static_dist_threshold:
            return True
        
        return False
    
    
    def _save_pickup(self, obj_id, frame_id=None, bbox=None):
        obj_info = self.obj_state.get(obj_id, {})

        self.picked_up[obj_id] = {
            'class'         : obj_info.get('class'),
            'state'         : obj_info.get('state'),
            'bbox'          : obj_info.get('bbox') if bbox is None else bbox,
            'last_seen'     : obj_info.get('last_seen') if  frame_id is None else frame_id,
            'time'          : time.strftime('%Y-%m-%d %H:%M:%S')
        }

    def _save_scene(self, obj_id, bbox, img):
        '''
            _save_pickup과 함께 호출
            누군가 분실물로 추정되는 물체를 가져갔다 판단되는 경우 
            scence폴더의 year / month / day / hour 에 저장
        '''
        timestamp = datetime.now()
        year = timestamp.year
        month = timestamp.month
        day = timestamp.day
        hour = timestamp.hour

        folder_path = self.scene_folder / self.pipename / f'{year}-{month}-{day}' / str(hour)
        os.makedirs(folder_path, exist_ok=True)
        file_path = str(folder_path / f"{obj_id}.jpg")

        img_h, img_w = img.shape[:2]
        box_x1 = round(bbox[0] * img_w)
        box_y1 = round(bbox[1] * img_h)
        box_x2 = round(bbox[2] * img_w)
        box_y2 = round(bbox[3] * img_h)

        side = round(max(box_x2 - box_x1, box_y2 - box_y1) * 5)
        cx = (box_x1 + box_x2) // 2
        cy = (box_y1 + box_y2) // 2
        crop_x1 = max(0, cx - side // 2)
        crop_y1 = max(0, cy - side // 2)
        crop_x2 = min(img_w, cx + side // 2)
        crop_y2 = min(img_h, cy + side // 2)

        crop = img[crop_y1:crop_y2, crop_x1:crop_x2].copy()

        timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
        font_scale = max(0.4, crop.shape[1] / 600)
        thickness = max(1, int(font_scale * 2))
        (text_w, text_h), _ = cv2.getTextSize(timestamp_str, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
        x = crop.shape[1] - text_w - int(crop.shape[1] * 0.02)
        y = text_h + int(crop.shape[0] * 0.02)
        cv2.putText(crop, timestamp_str, (x, y), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 255, 0), thickness)

        cv2.imwrite(file_path, crop)

    def _save_objImg(self, img, obj_id, bbox):
        '''
            obj-imgs폴더에 
            bbox crop 한 jpg 저장
        '''
        # 1. bbox를 crop
        folder_path = self.obj_imgs_folder / self.pipename
        os.makedirs(folder_path, exist_ok=True)
        image_path = str(folder_path / f'{obj_id}.jpg')

        img_h, img_w = img.shape[:2]
        x1 = int(bbox[0] * img_w)
        y1 = int(bbox[1] * img_h)
        x2 = int(bbox[2] * img_w)
        y2 = int(bbox[3] * img_h)

        crop = img[y1:y2, x1:x2]
        cv2.imwrite(image_path, crop)

    def _numpy_scene(self, img, bbox):
        '''
            SUSPECTED / LOST state인 object의 scene을 numpy 형태로 obj_state에 저장 
            : _clean 대상이 되었을때 scene을 크롭하면 이미 없어진 상태의 장면이 저장될 가능성이 크다 
              -> 마지막으로 보인 장면을 numpy 형태로 저장 후 해당 상태의 object가 clean 대상이 될 시 image로 변환하여 여장
        '''
        img_h, img_w = img.shape[:2]
        box_x1 = round(bbox[0] * img_w)
        box_y1 = round(bbox[1] * img_h)
        box_x2 = round(bbox[2] * img_w)
        box_y2 = round(bbox[3] * img_h)

        side = round(max( box_x2 - box_x1, box_y2 - box_y1 ) * 5)
        cx = (box_x1 + box_x2) // 2
        cy = (box_y1 + box_y2) // 2
        crop_x1 = max( 0, cx - side//2 )
        crop_y1 = max( 0, cy - side//2)
        crop_x2 = min( img_w, cx + side//2)
        crop_y2 = min( img_h, cy + side//2)

        crop = img[crop_y1:crop_y2, crop_x1:crop_x2].copy()
        return crop

    def _numpy2img(self, obj_id):
        '''
            obj_state에 저장된 numpy형태의 이미지 정보를 image파일로 저장
        '''
        obj_info = self.obj_state.get(obj_id)
        if obj_info is None:
            return
        
        crop = obj_info.get('last_crop_np')
        if crop is None:
            return 

        timestamp_str = obj_info.get('last_seen(time)')
        if timestamp_str is None:
            return 
        
        dt = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S') # str type의 timestamp을 datetime 객체로 파싱
        year = dt.year
        month = dt.month
        day = dt.day
        hour = dt.hour

        folder_path = self.scene_folder / self.pipename / f'{year}-{month}-{day}' / str(hour)
        os.makedirs(folder_path, exist_ok=True)
        file_path = str(folder_path / f'{obj_id}.jpg')

        font_scale = max(0.4, crop.shape[1] / 600)
        thickness = max(1, int(font_scale * 2))
        (text_w, text_h), _ = cv2.getTextSize(timestamp_str, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
        x = crop.shape[1] - text_w - int(crop.shape[1] * 0.02)
        y = text_h + int(crop.shape[0] * 0.02)
        cv2.putText(crop, timestamp_str, (x, y), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 255, 0), thickness)
        cv2.imwrite(file_path, crop)       


'''
    아래 코드들은 추후 utils.py로 분리
'''
  
def calc_center(bbox):
    '''
        center x, y를 구하는 함수 
        tlbr 형태의 bbox의 center좌표를 구한다 
    '''
    x1, y1, x2, y2 = bbox
    cx = (x1 + x2) / 2
    cy = (y1 + y2) / 2

    return (cx, cy)

def calc_distance(obj_bbox, person_bbox):
    '''
        ojcect와 person 사이의 거리를 구한다 
        1. object와 person의 중심좌표의 거리로 구한다 -> 변수가 많아보임 
        2. object의 중심좌표와 person에서 가장 변동이 적은 안정적인 bottom의 중심좌표로 구하다 
        3. 최단거리를 각 변의 중심좌표와의 거리중 최단 거리를 선택한다 
        4. cctv에서 가장 잘 보이는 머리부분의 중심좌표 이용 ***
        현재 1을 사용
    '''
    if obj_bbox is None or person_bbox is None:
        return np.inf
    obj_cx, obj_cy = calc_center(obj_bbox)
    p_cx, p_cy = calc_center(person_bbox)

    distance = math.dist([obj_cx, obj_cy], [p_cx, p_cy])

    return distance
    
    
def calc_motionVector(curr_bbox, prev_bbox):
    curr_center = calc_center(curr_bbox)
    prev_center = calc_center(prev_bbox)
    return [curr_center[0] - prev_center[0], curr_center[1] - prev_center[1]]

def calc_cosineSim(obj_mv, person_mv):
    norm_obj, norm_person = np.linalg.norm(obj_mv), np.linalg.norm(person_mv)
    if norm_obj == 0 or norm_person == 0:
        return 0
    return np.dot(obj_mv, person_mv) / (norm_obj * norm_person)

def calc_iou(bbox1, bbox2):
    '''
        curr_bbox : 현재 프레임 object의 bbox
        obj_bbox : state가 SEPARATED, SUSPECTED, LOST인  object의 bbox

        iou를 계산하여 return
    '''
    # 교집합 좌표
    x1 = max(bbox1[0], bbox2[0])
    y1 = max(bbox1[1], bbox2[1])
    x2 = min(bbox1[2], bbox2[2])
    y2 = min(bbox1[3], bbox2[3])

    # 교집합 area
    w = max(0, (x2 - x1))
    h = max(0, (y2 - y1))
    inter_area = w * h

    # 합집합 : curr_bbox_area + obj_bbox_area - inter_area
    bbox1_area = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
    bbox2_area = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])
    union_area = bbox1_area + bbox2_area - inter_area

    # 겹치는 부분이 없으면 0
    if union_area <= 0:
        return 0
    
    # iou
    iou = inter_area / union_area
    return iou
    
'''view_w = 1280
view_h = 720
def _to_pixel(bbox_norm):
    x1 = int(bbox_norm[0] * view_w)
    y1 = int(bbox_norm[1] * view_h)
    x2 = int(bbox_norm[2] * view_w)
    y2 = int(bbox_norm[3] * view_h)
            
    x1 = max(0, min(x1, view_w))
    y1 = max(0, min(y1, view_h))
    x2 = max(0, min(x2, view_w))
    y2 = max(0, min(y2, view_h))

    return x1, y1, x2, y2'''

'''def calc_shortest_distance(self, object_bbox, person_bbox):

        distance = 

        return distance'''
