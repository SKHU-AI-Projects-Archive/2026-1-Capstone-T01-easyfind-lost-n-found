from .base_detector import BaseDetector
from .dummy_detector import DummyDetector
from .yolo11_detector import Yolo11Detector
from .tensorrt_detector import TensorRTDetector
from core.utils.module_loader import get_class_by_name


def build_detector(config):
    detector_type = config.get('type', 'DummyDetector')
    detector_class = get_class_by_name("plugins.detectors", detector_type)
    return detector_class(config)