# EasyFind — CCTV 기반 분실물 탐지 시스템

> 2026-1 인공지능 캡스톤디자인 · T01

CCTV 영상에서 **방치·유실된 물건을 실시간으로 탐지**하고, 사용자가 **특정 시각과 물건을 입력하면 과거 영상을 거슬러 검색**해 "그 물건이 언제부터 언제까지 어디에 있었는지" 찾아주는 시스템입니다.

현실에서 일어날 수 있는 **모든 종류의 분실물을 미리 학습시켜 상시 탐지하는 것은 사실상 불가능**합니다. 그래서 EasyFind는 가방·노트북처럼 흔한 물건은 **상시 자동으로 감지**하고, 그 밖의 물건은 사용자가 *"빨간 배낭"* 처럼 **말로 묘사해 요청하면** 과거 영상에서 찾아내는 **자연어 기반 검색(grounding detector)을 보조 수단**으로 결합했습니다. 즉, 상시 감지가 놓친 물건도 사용자의 묘사 한 줄로 되짚어 찾을 수 있습니다.

핵심은 config로 조립되는 멀티프로세스 추론 엔진입니다. 입력 소스 · 검출기 · 추적기 · 출력 핸들러를 플러그인처럼 교체할 수 있고, 상시 감시와 소급 검색이 같은 파이프라인 구조를 공유합니다.

---

## 주요 기능

- **상시 분실물 감지** — 검출(detector) → 추적(tracker) → 방치 판정(abandoned) 파이프라인으로 주인과 분리된 물건의 상태(WITH_OWNER → STATIC → SUSPECTED → LOST)를 추적
- **소급 검색 (Retrospective Search)** — 상시 감지가 놓친 물건도, CCTV·시각·물건 묘사(한/영)를 입력하면 과거 아카이브 프레임에서 자연어 기반(YOLOWorld)으로 검색. 발견 즉시 타임라인 카드로 누적 표시
- **웹 대시보드 (React)** — 실시간 모니터링, 알림, 탐지 이력, 정밀 검색, 설정 → [frontend/README.md](frontend/README.md)
- **플러그인 구조** — 소스/검출기/추적기/핸들러를 base 클래스 상속 + config 한 줄로 교체
- **GPU 추론** — 검출기별 `device` 지정 (단일 GPU 공유 또는 멀티 GPU 분리)

---

## 아키텍처

멀티프로세스 + 공유메모리(SharedMemory) 기반. 프레임 본체는 공유메모리로, 메타데이터만 큐로 전달합니다.

```
[상시 감시]
  WebcamSource ─▶ SourceStreamer ─▶ SharedMemory ─▶ PipelineExecutor ─▶ result_queue ─▶ OutputAggregator ─▶ handlers
                       │ (LatestSlot: 최신 프레임만)      │ detect→track→abandoned                 ├ ScreenHandler
                       └─▶ FrameArchiver                                                          ├ WebHandler (:5000)
                            archives/{cam}/{date}/{HH}/{epoch_ms}.jpg                             └ FileLogHandler

[소급 검색]  POST /api/search {cam, 시각범위, prompt}
  ArchiveSource(검색잡) ─프레임+검색메타─▶ SourceStreamer ─▶ SharedMemory ─▶ PipelineExecutor(검색모드)
       └ 과거 아카이브 공급                                       │ set_classes(prompt) → detect
                                                                 └─ kind='search' ─▶ WebHandler ─▶ /api/search/<job> (타임라인)
```

- **LatestSlot**: 소비자가 느릴 때 구형 프레임을 버리고 최신만 처리 — 실시간 타이밍 밀림 방지
- **FrameArchiver**: 상시 프레임을 timestamp 기반으로 디스크에 보관 → 소급 검색의 입력
- **검색 모드**: 별도 엔진 없이 기존 `PipelineExecutor`가 `meta['search']`를 감지해 동작. YOLOWorld 모델은 상주하며 프롬프트만 교체

---

## 디렉토리 구조

```
.
├── main.py                     # 진입점 — 프로세스 조립 및 실행
├── configs/                    # 파이프라인 설정 (.yaml)
│   ├── default_config.yaml     #   모든 파라미터 기본값 (실험 config가 deep-merge)
│   ├── multi_cam.yaml          #   웹캠 상시 감시 + 소급 검색 (메인)
│   └── lostfound_demo.yaml     #   비디오 기반 검색 데모
├── core/                       # 런타임 엔진
│   ├── streamer.py             #   SourceStreamer — 입력 → SharedMemory + 아카이빙
│   ├── executor.py             #   PipelineExecutor — 검출/추적/방치 + 검색 모드
│   ├── aggregator.py           #   OutputAggregator — 결과 수집 → 핸들러 분배
│   ├── archiver.py             #   FrameArchiver — timestamp 기반 프레임 아카이브
│   ├── shared_mem.py           #   SharedMemory 순환버퍼 Reader/Writer
│   ├── latest_slot.py          #   LatestSlot — 최신 프레임만 유지하는 슬롯
│   └── utils/                  #   config_loader · module_loader
├── plugins/                    # 교체 가능한 알고리즘 구현체
│   ├── sources/                #   webcam · video · image(folder) · archive · dummy
│   ├── detectors/              #   YOLO11 · YOLOWorld · RT-DETR · ...
│   ├── trackers/               #   SORT · BYTETrack · DeepSORT
│   ├── handlers/               #   screen · web · filelog
│   └── abandoned/              #   방치/유실 객체 상태 판정
└── frontend/                   # React 웹 대시보드 (Vite) — frontend/README.md 참고
    └── src/pages/              #   dashboard · alerts · detection-history · precise-detection · settings
```

---

## 설치

Python 3.11 기준입니다.

### 1. 저장소 복제
```shell
git clone https://github.com/sylee-skhu/2026-1-Capstone-T01-easyfind-lost-n-found.git
cd 2026-1-Capstone-T01-easyfind-lost-n-found
```

### 2. PyTorch (CUDA) 설치
GPU 추론을 위해 **본인 환경의 CUDA 버전에 맞는** PyTorch 빌드를 먼저 설치합니다. 아래는 **CUDA 13.0 예시**일 뿐이며, 설치 가능한 조합은 [PyTorch 공식 안내](https://pytorch.org/get-started/locally/)에서 확인하세요.
```shell
# 예시: CUDA 13.0  (cu118, cu121, cu124 등 환경에 맞게 변경)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu130
```

### 3. 나머지 의존성 설치
```shell
pip install -r requirements.txt
```
- 한글 프롬프트 자동 번역에 `deep-translator`를 사용합니다.
- `lap` / `cython-bbox`는 Windows에서 빌드가 실패할 수 있습니다. 설치에 실패해도 `plugins/trackers/utils/matching.py`의 scipy/numpy 폴백으로 BYTETracker가 동작하므로 건너뛰어도 됩니다.

### 4. 프론트엔드 (선택)
웹 대시보드는 별도로 실행합니다. 설치·실행·API 연동은 **[frontend/README.md](frontend/README.md)** 를 참고하세요.
```shell
cd frontend
npm install
npm run dev
```

---

## 실행

```shell
# 웹캠 상시 감시 + 소급 검색 (메인)
python main.py -c configs/multi_cam.yaml

# 비디오 기반 검색 데모
python main.py -c configs/lostfound_demo.yaml
```

실행 후 대시보드는 `http://localhost:5000/`, 프론트엔드 개발 서버는 `http://localhost:5173/`(Vite 기본)에서 확인합니다.

> 종료는 콘솔에서 **Ctrl+C**로 하세요. 강제 종료 시 SharedMemory가 잔존할 수 있으나, 다음 실행 시 자동 정리/재사용됩니다.

---

## 설정 (config)

`configs/*.yaml`로 소스·검출기·추적기·출력을 조립합니다. 지정하지 않은 값은 `default_config.yaml`에서 상속됩니다.

```yaml
sources:
  - id: cam_0
    type: WebcamSource          # WebcamSource | VideoSource | FolderImageSource | ArchiveSource
    device_index: 0
    archive: { enable: true, jpeg_interval_sec: 5 }   # 소급 검색용 아카이브

pipelines:
  - name: Office_Cam
    source_id: cam_0
    detector:
      type: YOLOWorldDetector    # YOLOWorldDetector | Yolo11Detector | RTDETRDetector
      device: cuda:0
      classes: ["person", "bag", "laptop"]
    tracker:  { type: BYTETracker }
    abandoned: { type: abandonedObject, suspected_threshold_min: 15, lost_threshold_min: 15 }

output:
  handlers:
    - { type: ScreenHandler, enable: true }
    - { type: WebHandler, enable: true, port: 5000 }
```

### 검출 대상 지정
- **Yolo11Detector**: COCO 클래스 인덱스 — 예) `classes: [0, 24, 26]` ([클래스 목록](https://github.com/ultralytics/ultralytics/blob/main/ultralytics/cfg/datasets/coco.yaml))
- **YOLOWorldDetector**: 자연어 프롬프트 — 예) `classes: ["red backpack", "person with a bag"]`

---

## 구성 요소

| 구분 | 구현체 |
|------|--------|
| **Source** | WebcamSource, VideoSource, FolderImageSource, **ArchiveSource**(소급 검색), DummySource |
| **Detector** | Yolo11Detector, **YOLOWorldDetector**(자연어 프롬프트), RTDETRDetector |
| **Tracker** | SORT, BYTETracker, DeepSORT |
| **Handler** | ScreenHandler, WebHandler, FileLogHandler |
| **Abandoned** | abandonedObject (주인 분리 → 정적 → 의심 → 분실 상태머신) |

새 알고리즘은 해당 base 클래스(`BaseSource`/`BaseDetector`/`BaseTracker`/`BaseHandler`)를 상속해 `plugins/` 아래에 추가하면 config의 `type` 이름으로 자동 로드됩니다.

---

## 웹 대시보드

실시간 모니터링 · 알림 · 탐지 이력 · 정밀(소급) 검색 · 설정 UI는 React로 구현되어 있습니다. 자세한 내용은 **[frontend/README.md](frontend/README.md)** 를 참고하세요.
