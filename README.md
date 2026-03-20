# 2025-W-Research-T01-ai-perception-engine

```
.
├── configs/            # 설정 파일 (.yaml)
├── core/               # 시스템 엔진
│   ├── memory/         # Shared Memory 관리
│   ├── sources/        # 입력 관리자 (Streamer) -> libs/sources/
│   ├── pipelines/      # 추론 관리자 (Executor) -> libs/detectors/, libs/trackers/
│   └── outputs/        # 출력 관리자 (Aggregator) -> libs/handlers/
├── libs/               # 요소 알고리즘 구현체
│   ├── sources/        # 입력 소스 (BaseSource 상속)
│   ├── detectors/      # 검출기 (BaseDetector 상속)
│   ├── trackers/       # 추적기 (BaseTracker 상속)
│   └── handlers/       # 출력 처리 (BaseHandler 상속)
└── main.py             # 프로그램 실행
```
---

## Installation

python 3.10에서 실행합니다.

### step 1
repository를 복제합니다.

```shell
git clone https://github.com/SKHU-AI-Projects-Archive/2025-W-Research-T01-ai-perception-engine.git
```

### step 2
cuda 사용을 위해 pytorch를 설치합니다.
또한, YOLOWorld 사용을 위해 CLIP을 설치합니다.
```shell
pip3 install torch torchvision --index-url https://download.pytorch.org/whl/cu130
```

```shell
pip install git+https://github.com/ultralytics/CLIP.git
```

### step 3
실행에 필요한 라이브러리를 설치합니다.
```shell
pip install -r requirements.txt
```

---

## Demo
탐지기와 추적기를 선택할 수 있는 것이 특징입니다.

configs 폴더에 위치한 yaml 파일로 탐지할 객체를 지정할 수도 있습니다.

이미지, 웹캠, 비디오로 구성된 3가지의 소스와 2개의 탐지기, 2개의 추적기를 구현했습니다.

- source
    - image
    - webcam
    - video
- detector
    - YOLOv11
    - YOLOWorld
- tracker
     - SORT
     - BYTETrack
     - DeepSORT

yolo11과 yoloworld를 이용할 경우 다중 객체 추적이 가능합니다.
yaml 파일에서 classes 항목의 값을 수정하여 여러 객체들을 탐지할 수 있습니다.

yolo11의 클래스는 [여기에서](https://github.com/ultralytics/ultralytics/blob/main/ultralytics/cfg/datasets/coco.yaml) 확인할 수 있습니다.

```shell
#yolo11
[0,1,56,64]

# yoloworld
["person who have bag","skyblue shirts"]
```

사용 방법은 아래의 코드를 참고하세요.
```shell 
python main.py --config configs/source_detector_tracker.yaml 

python main.py -c configs/source_detector_tracker.yaml 
```

---
