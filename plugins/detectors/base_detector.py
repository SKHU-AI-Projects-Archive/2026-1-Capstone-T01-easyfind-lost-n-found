from abc import ABC, abstractmethod


def resolve_device(config):
    """detector가 사용할 torch device 문자열을 결정한다.

    우선순위:
      1) config['device']        — 예: "cuda:0", "cuda:1", "cpu"
      2) "cuda:{gpu_id}"          — CUDA 가용 시 (config['gpu_id'], 기본 0)
      3) "cpu"                    — CUDA 미가용 시

    단일 GPU 환경에서는 상시·검색이 같은 "cuda:0"을 공유하고,
    GPU를 추가하면 config의 device/gpu_id만 바꿔 물리 분리할 수 있다.
    """
    import torch

    device = config.get('device', None)
    if device:
        return device

    if torch.cuda.is_available():
        gpu_id = config.get('gpu_id', 0)
        return f"cuda:{gpu_id}"
    return "cpu"


class BaseDetector(ABC):
    def __init__(self, config):
        self.config = config
        self.device = resolve_device(config)

    @abstractmethod
    def detect(self, img):
        pass
