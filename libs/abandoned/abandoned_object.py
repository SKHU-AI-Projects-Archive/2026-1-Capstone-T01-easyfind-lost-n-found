import time
import math
import numpy as np
from enum import Enum

class objectState(Enum):
    UNASSIGNED = -1
    WITH_OWNER = 0
    SEPARATED = 1
    SUSPECTED = 2
    LOST = 3

class abandonedObject:
    def __init__(self, config):
        
        self.config = config
        self.fps = config.get('fps', 30)

        self.dist_threshold = config.get('dist_threshold', 0.05) # distance 정규화된 좌표를 기준으로 설정해야한다 
        self.suspect_threshold_min = config.get('suspect_threshold', 15) # minute : separated로붙 15분 
        self.lost_threshold_min = config.get('lost_threshold', 15) # minute : suspected로 부터 15분
        self.clean_threshold_sec = config.get('clean_threshold_sec', 3) # second : last_seen - current frame 가 일정 second를 지나면 딕셔너리에서 삭제 
        self.prev_clean_threshold_sec = config.get('prev_clean_threshold', 1) # second : last_seen - current frame이 일정 second를 지나면 prev_bbox, prev_last_seen에서 삭제

        # 프레임으로 계산하여 처리하는 것이 time함수를 사용하는것보다 안정적
        self.suspect_threshold = self.suspect_threshold_min * 60 * self.fps
        self.lost_threshold = self.lost_threshold_min * 60 * self.fps
        self.clean_threshold = self.clean_threshold_sec * self.fps
        self.prev_clean_threshold = self.prev_clean_threshold_sec * self.fps

        self.score_threshold = config.get('score_threshold', 0.7)
        self.owner_frame_threshold = config.get('owner_frame_threshold', 30)
        self.restore_threshold = config.get('restore_threshold', 0.7)

        # 주종관계가 정해지기 전 사용하는 딕셔너리
        # 주종관계가 정해지면 삭제, 화면에서 object가 사라지면 삭제
        # 이 딕셔너리를 참고하여 obj_state의 주인정보를 저장한다 
        # 저장형태: object_id : {person_id1: frame_cnt, person_id2 : frame_cnt || frame_cnt는 score > score_thershold 인경우 누적해나간다 30이되면 주인이됨
        self.pair_hist = {}

        # 이동벡터를 구하기 위해 이전 bbox를 저장하는 딕셔너리
        # 저장형태: {track_id : prev_bbox}
        self.prev_bbox = {} 
        self.prev_last_seen = {}

        self.objs_owner = {} # owner를 기준으로 objects목록을 찾는다 
        self.obj_owner = {} # object를 기준으로 owner가 있는지 찾는다 
        # state가 바뀔때마다 다른 딕셔너리로 옮기는 작업보다 간단히 상태만 수정하면 되므로 하나의 딕셔너리로 관리 
        self.obj_state = {}

    def update(self, frame_id, tracks):
        '''
            매프레임마다 tracking되는 object들의 상태를 업데이트해나간다 
        
            1. owner_check로 person_id와 object들의 주인 관계를 묶음
            2. person과 object가 멀어지는 것을 감지하여 state를 업데이트해나감 

            state : SEPARATED -> SUSPECTED -> LOST

            objs_state 저장형태 : object_id{
                            'owner_id' : ?,
                            'state' : 0(with_owenr) 1(separated), 2(suspected), 3(lost)
                            'bbox' : ?, bbox는 seaprated된 순간 갱신한다 -> 가만히 있는 물체의 id스위치가 일어나도 id를 복구하기 위해
                            'ReID_saved' : True/False,
                            'last_seen' : ?,
                            'separated_start' : ?
                            'suspected_start' : ?,
                            'lost_start' : ?,
                            'restart_with_owner' : ? 누군가 다시 가져갈 수 있으므로 시작점 기록}
                - state = 2인경우 class(object의 종류)와 color(추후 색구분/추출하는 방법을 찾는경우 추가) 정보도 추가 

            objs_owner 저장형태 : owner_id{'object_ids' : [id1 ,id2, ...]}
            
            이후 owner의 ReID를 저장하고싶은 경우 
            { owner_id{'object_ids' :[id1, id2,...],
                     'ReID_list' : [상태벡터1, 상태벡터2, ...]} }형태로 확장
    
                                   obj id는 set 형태로 저장 => 중복 방지

            ReId 외형정보 상태백터는 object와 떨어지는 순간 추출하여 저장한다
            여러 물건을 잃어버릴 수 있으므로 잃어버릴때마다 저장하여 누적
            이후 찾으러왔을때 ReID매칭시 ReID_list안의 상태벡터들의 cosine similarity를 구하여 max값을 이용
            -> 잃어버린 역순으로 찾으러오지 않고 다른물건 먼저 찾으러 오는 경우때문에 이렇게 이용
            
            즉 
            if objects_state의 object_id['ReID_saved'] == False and object_id['state'] == 0 
                외형정보를 추출
                objects_owner의 owner_id['ReID_list'].append()를 통해 저장
                object_id['ReID_saved'] = True로 변경


            + SEPARATED 시작 프레임, SUSPECTED 시작 프레임, LOST 시작 프레임을 저장하는 것이 중요해보임 
            
        '''
        #1. tracks에서 person, object 분리 
        # 저장형태 : {id1 : track, id2 : track, ...}
        person = {}
        obj = {}
        for track in tracks:
            track_id, cls = track[4], track[5]
            if cls == 'person':
                person[track_id] = track
            else:
                obj[track_id] = track

        # 2. restore id 
        # _restore_id를 초반에 실행함으로 보정된 id의 객체의 상태 갱신을 수행할 수 있게한다 
        obj = self._restore_objId(obj)

        # 3. restore가 반영된 new track results를 생성
        new_track_results = list(person.values()) + list(obj.values())

        # 4. owner_check를 통한 owner 확정및 갱신 
        self._owner_check(frame_id, new_track_results)

        # 5. obj_owner에 매칭된 person과 object이 멀어짐을 감지하여 object의 상태를 업데이트
        # 일정 거리이상 멀어지면 objs_state['state'] = objectState.SEPARATED로 설정 
        # obj_id의 bbox를 obj_state[obj_id]['bbox']에 갱신
        ''' TODO: owner 없는 objcet가 분리되어 고정된 상태인 경우 분실물로 처리하기 위한 상태관리 필요 -> 이경우 아래 for for를 for obj_id, belongings in obj.items()로 수정해 돌아야한다 '''

        # owner가 정해진 object에 대한 상태전이 
        for owner_id, obj_ids in self.objs_owner.items():
            for obj_id in obj_ids:
                # obj_id나 owner_id가 현재 프레임에서 가려져 tracks에 존재하지않는 경우 갱신을 하지 않음
                # obj_state에 들어있지 않은 object의 경우 상태 갱신할 필요 없음 -> id switch가 일어난 경우는 restore_id에서 갱신
                # 추후 다른 방식으로 변경 가능 
                if owner_id not in person:
                    continue
                if obj_id not in obj:
                    continue
                if obj_id not in self.obj_state:
                    continue

                owner = person[owner_id] # track_id가 owner_id인 person의 track
                belongings = obj[obj_id] # track_id가 obj_id인 object의 track

                # onwer bbox와 belongings bbox의 distance 계산
                distance = calc_distance(belongings[:4], owner[:4])
                # ------------------------------------
                # 6. state update 및 bbox update
                curr_state = self.obj_state[obj_id]['state']
                if distance <= self.dist_threshold:
                    new_state = objectState.WITH_OWNER
                else:
                    if curr_state == objectState.WITH_OWNER:
                        new_state = objectState.SEPARATED

                    elif curr_state == objectState.SEPARATED and self._turn_suspected(obj_id, frame_id):
                        new_state = objectState.SUSPECTED

                    elif curr_state == objectState.SUSPECTED and self._turn_lost(obj_id, frame_id):
                        new_state = objectState.LOST

                    else: new_state = curr_state

                self._set_state(frame_id, obj_id, new_state)

                #--------------------------------------
                state = self.obj_state[obj_id]['state']
                if state != objectState.WITH_OWNER:
                    self.obj_state[obj_id]['bbox'] = belongings[:4]
                else: 
                    self.obj_state[obj_id]['bbox'] = None

        # owenr가 정해지지 않은 object에 대한 분실물 처리 코드 추가 필요

        # 7. 모든 object의 last seen frame 갱신 
        for obj_id in obj:
            if obj_id in self.obj_state:
                self.obj_state[obj_id]['last_seen'] = frame_id
        
        # 8. 저장공간 정리 
        self._clean(frame_id)

        return new_track_results
    
    def _owner_check(self, frame_id, track_results):
        '''
            owner person과 소유한 object를 묶어 object_owner에 저장
            update에서 while문을 통해 track results를 돌면서 주인관계를 묶는다

            주인여부 판단방법: 사람이 겹쳐있는 경우가 있을 수 있으므로 물건의 주인으로 예상되는 후보들에 점수를 매겨 가장 높은 점수를 가진 사람을 주인으로 
            score = (1- distance/dist_threshold) + 이동벡터의 cosine similarity
            socre가 일정 프레임 동안 socre_threshold(0.7)를 넘으면 주인으로 확정한다 

            한번 owner가 정해지면 다시 재정의 하면 안된다 

        '''
        persons = []
        objects = []
        # 프레임마다 person과 object로 분리 
        for track in track_results:
            '''거리가 가까운 애들끼리 pair'''
            cls = track[5]
            if cls == 'person':
                persons.append(track)
            else:
                objects.append(track)
        ''' 
            owner 후보 탐색

            pair_hist 저장형태: obj_id : {
                                        person_id1 : frame_cnt,
                                        person_id2 : frame_cnt, ... }
            
            1. pair_hist에 object_id를 key로 person_id를 value로 하여 넣는다
            2. max owner_score를 가진 person_id의 frame_cnt를 1 증가시킨다 
               ( owner_score =  (1- distance/dist_threshold) + 이동벡터의 cosine similarity )
               이동벡터는 prev_bbox에 있는 이전 bbox와 현재 bbox로 구한다 
            3. frame_cnt가 먼저 threshold가 되는 person_id를 owner로 확정한다 

            frame_cnt는 연속frmae이 아닌 누적으로 카운트한다 
            이유: 일시적 가려짐 상태에서는 연속이 끊길 수 있으므로 
                추후 선택되지 않은 경우 -1을 하는 방법을 추가해도 될것 같음

            해야할것: owner_score를 구한후 가장 큰 person_id의 frame_cnt를 증가 : 완료
                    30이되면 owner확정 : 완료
                    prev_bbox값이 None인 경우 어떻게 처리할지 : 완료 (obj, person둘중 하나라도 None인 경우 continue)
                    프레임이 끝나기 전 prev_bbox갱신 : 완료
                    perv_bbox는 초기값은 None 꺼낼때 없으면 None으로 처리 : 완료
        '''
        # object와 distance_threshold안쪽인 person을 후보로 묶어 pair_hist에 저장
        for obj in objects:
            obj_id = obj[4]
            obj_bbox = obj[0:4] 
            # 모든 object를 관리하기 위해  obj_state에 저장한다 
            if obj_id not in self.obj_state:
                self.obj_state[obj_id] = {
                    'owner_id' : None,
                    'state' : objectState.UNASSIGNED,
                    'bbox' : None,
                    'last_seen' : frame_id,
                    'separated_start' : None,
                    'suspected_start' : None,
                    'lost_start' : None
                }

            # prev_bbox가 없으면 None으로 하여 초기화 
            self.prev_bbox.setdefault(obj_id, None)

            # 이미 owner가 정해진 object는 더이상 후보를 찾지 않는다 
            if obj_id in self.obj_owner: 
                continue

            # owner가 정해지지 않은 경우 아래 실행 
            self.pair_hist.setdefault(obj_id, {}) # pair_hist에 obj_id가 없으면 생성 있으면 그대로 

            max_score = float('-inf') # owner_score가 음수일수도 있으므로 음의 무한대로 초기값을 지정해둔다 
            maxScore_person = None
            for person in persons:
                person_id = person[4]
                # prev_bbox가 없는 경우 None으로하여 생성
                self.prev_bbox.setdefault(person_id, None)

                # bbox distance < dist_threshold 이면서 pair_hist[object_id]에 person_id가 없는 경우 추가
                person_bbox = person[0:4] # bbox를 화면 기준으로 픽셀화
                distance = calc_distance(obj_bbox, person_bbox)

                if distance > self.dist_threshold: # 박스사이의 거리가 threshold보다 크면 생각할 필요 없음
                    continue

                # if distance <= self.dist_threshold: 조건을 만족하면 
                if person_id not in self.pair_hist[obj_id]:
                    self.pair_hist[obj_id][person_id] = 0

                # prev_bbox = None이면 owner score 계산이 불가능하므로 건너뛰어 진행하지 않음
                '''
                    이 경우 score를 1- distance/dist_threshold로 만 게산할지 생각해봐야함 
                    이유: 첫 등장 프레임에서 score계산이 안됨(이는 원래 의도한대로이긴 함)
                '''
                if self.prev_bbox[obj_id] is None or self.prev_bbox[person_id] is None: 
                    owner_score = 1 - distance

                # owner socre를 계산하여 maxScore_person에 person_id를 갱신
                else: 
                    owner_score = self._calc_ownerScore(obj_bbox, 
                                                          person_bbox, 
                                                          self.prev_bbox[obj_id], 
                                                          self.prev_bbox[person_id], 
                                                          self.dist_threshold)
                    
                if owner_score > max_score:
                    max_score = owner_score
                    maxScore_person = person_id

            # persons를 전부 다 돌면 maxScore_person이 정해진다 -> pair_hist의 person_id값인 frame_cnt를 1 증가 
            # if self.pair_hist[obj_id][maxScore_person] == 30이 되면 pair_hist에서 obj_id 삭제, obj_id와 person_id를 objs_owner와 obj_owner로 옮긴다
            # + objs_state에 obj를 새로 추가한 후 'state'를 with owner로 초기화 한다 
            if maxScore_person is not None and max_score >= self.score_threshold: 
                self.pair_hist[obj_id][maxScore_person] += 1 

                if self.pair_hist[obj_id][maxScore_person] >= self.owner_frame_threshold:
                    owner_id = maxScore_person
                    self.pair_hist.pop(obj_id, None)

                    self.obj_owner[obj_id] = owner_id
                    self.objs_owner.setdefault(owner_id, set()).add(obj_id) # onwer_id가 있으면 add만 실행 없다면 새로 만든다 
                    
                    self.obj_state[obj_id]['owner_id'] = owner_id
                    self.obj_state[obj_id]['state'] = objectState.WITH_OWNER

        # prev_bbox, prev_last_seen 업데이트
        for track in track_results:
            track_id = track[4]
            self.prev_bbox[track_id] = track[:4]
            self.prev_last_seen[track_id] = frame_id

    def _restore_objId(self, obj):
        '''
            obj => 현재 frame에서 추적된 대상
            obj : {id1 : track, id2 : track, ...}

            SEPARATED, SUSPECTED, LOST상태에서의 object는 대부분 이동하지 않은 고정된 상태일 것이다 이를 이용하여 prev bbox(object_state['bbox'])와 curr_bbox의 iou를 비교하여 id를 복구한다 
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
        # 이미 복구된 obj의 id는 재매칭 하지 않음 
        matching_curr_ids = set()

        ''' 1. 복구할 대상인 id를 탐색, id 복구 '''
        for obj_id, obj_info in self.obj_state.items():
            state = obj_info['state']

            if state == objectState.WITH_OWNER: # id 복구 대상은 SEPARATED, SUSPECTED, LOST (이 세가지 상태일 경우만 bbox갱신하므로)
                continue
            if obj_id in obj: # 현재 프레임에서의 obj
                continue
            # WITH_OWNER가 아니면 bbox를 업데이트하니 상관없지만 혹시모르는 상황을 대비하여 작성
            prev_bbox = obj_info['bbox']
            if prev_bbox is None:
                continue

            max_iou = 0
            max_curr_id = None

            for curr_id, track in obj.items():
                if curr_id in matching_curr_ids:
                    continue

                curr_bbox = track[:4]
                iou = calc_iou(curr_bbox, prev_bbox)
                if iou > max_iou:
                    max_iou = iou
                    max_curr_id = curr_id
            # for문이 끝나는 시점에 max_curr_id가 정해져있음 이를 threshold와 비교하여 이상이면 id 복구대상으로 판단 
            if max_iou >= self.restore_threshold and max_curr_id is not None:
                restore_id_map[max_curr_id] = obj_id
                matching_curr_ids.add(max_curr_id)

        ''' 2. new_obj 생성 : restore된 id를 반영 '''
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

            삭제 기준
            obj_state : max_missing_frame(5초)
            pair_hist : owner_check에서 주종관계가 정해지면 삭제됨 but 주종관계가 끝까지 정해지지않으면 삭제되지 않음 
                        새로운 삭제 기준 추가해야함 
                        owner후보는 주종관계가 정해지기 전 id switch가 일어나면 새로운 id 기준으로 다시 owner check하면 되므로 owner가 사라지면 삭제해도 무방할것 같음
                        -> owner_check에서 삭제하도록 하면 됨
            obj_owner : object가 일정 frame이 지나도록 나타나지 않으면 삭제
            objs_owner : owner_id의 스위치가일어나면 어차피 그 owner은 끝까지 없는 상태이므로 object들이 모두 사라지면 삭제
                         어떤 object가 obj_owner에서 삭제되면
                         그 object를 objs_owner[owner_id]에서도 제거
                         그리고 그 owner가 가진 object가 하나도 없으면 owner_id 삭제

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
            # objs_owners는 owner_id가 key값이므로 빠르게 접근하여 삭제하기 위해 obj_state에서 삭제하기 전 owner_id를 추출
            obj_info = self.obj_state.get(obj_id, {})
            owner_id = obj_info.get('owner_id', None)

            self.obj_state.pop(obj_id, None)
            self.obj_owner.pop(obj_id, None)
            self.pair_hist.pop(obj_id, None)
            self.prev_bbox.pop(obj_id, None)
            self.prev_last_seen.pop(obj_id, None)
            
            if owner_id is not None and owner_id in self.objs_owner: # owner가 정해지지 않은 분실물(object)이 있을 수도 있기에 필요한 조건문 
                self.objs_owner[owner_id].discard(obj_id)

                if not self.objs_owner[owner_id]:
                    self.objs_owner.pop(owner_id, None)
        
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


    def _set_state(self, frame_id, obj_id, new_state):
        '''
            state update
        '''
        if new_state == objectState.WITH_OWNER:
            self.obj_state[obj_id]['separated_start'] = None
            self.obj_state[obj_id]['suspected_start'] = None
            self.obj_state[obj_id]['lost_start'] = None
            self.obj_state[obj_id]['state'] = new_state
            #self.obj_state[obj_id]['bbox'] = None
            return 

        elif new_state == objectState.SEPARATED:
            if self.obj_state[obj_id]['state'] != objectState.SEPARATED: # start frame id는 처음 한번만 업데이트해야한다 매번 업데이트하면 안됨 
                self.obj_state[obj_id]['separated_start'] = frame_id

        elif new_state == objectState.SUSPECTED:
            if self.obj_state[obj_id]['state'] != objectState.SUSPECTED:
                self.obj_state[obj_id]['suspected_start'] = frame_id

        elif new_state == objectState.LOST:
            if self.obj_state[obj_id]['state'] != objectState.LOST:
                self.obj_state[obj_id]['lost_start'] = frame_id
        # state 갱신
        self.obj_state[obj_id]['state'] = new_state
        #self.obj_state[obj_id]['bbox'] = obj_bbox


    def _calc_ownerScore(self, obj_bbox, person_bbox, prev_obj, prev_person, dist_threshold):
        '''
            owner_score =  (1- distance/dist_threshold) + 이동벡터의 cosine similarity

            calc_motionVector의 결과와 calc_distance를 이용하여 계산 
        '''
        distance = calc_distance(obj_bbox, person_bbox)

        obj_mv = calc_motionVector(obj_bbox, prev_obj)
        person_mv = calc_motionVector(person_bbox, prev_person)
        owner_score = (1 - distance) + calc_cosineSim(obj_mv, person_mv)# 모션벡터의 코사인 유사도를 더해야함 

        return owner_score
    
    def _turn_suspected(self, obj_id, frame_id):
        '''
            separated start frame과 현재 framge을 비교, suspect threshold 이상이면 flag = true
        '''
        if frame_id - self.obj_state[obj_id]['separated_start'] >= self.suspect_threshold:
            return True
        else:
            return False

    def _turn_lost(self, obj_id, frame_id):
        '''
            suspected start frame과 현재 frame을 비교, suspect threshold 이상이면 flag = true
        '''
        if frame_id - self.obj_state[obj_id]['suspected_start'] >= self.lost_threshold:
            return True
        else:
            return False

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
    obj_cx, obj_cy = calc_center(obj_bbox)
    p_cx, p_cy = calc_center(person_bbox)

    distance = math.dist([obj_cx, obj_cy], [p_cx, p_cy])

    return distance
    
    
def calc_motionVector(curr_bbox, prev_bbox):
    ''' 
        이동벡터 계산 
        : 현재 obj_id의 bbox, person_id의 bbox와 prev_bbox에 있는 이전 프레임 bbox를 이용하여 계산 

        return 값: obj의 이동벡터, person의 이동벡터 
    '''
    curr_center = calc_center(curr_bbox)
    prev_center = calc_center(prev_bbox)

    mv = [curr_center[0] - prev_center[0], curr_center[1] - prev_center[1]]

    return mv
    
def calc_cosineSim(obj_mv, person_mv):
    '''
        obj motiob vector와 person motion vector를 이용하여 cosine simillarity를 계산 

        obj person 둘중 하나가 정지상태로 인해 norm이 0인 경우 0/0이 되므로 NaN이 나온다 
        예외로 이 경우 0을 return 
    '''
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
