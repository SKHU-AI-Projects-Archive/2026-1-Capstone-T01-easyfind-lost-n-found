from abc import ABC, abstractmethod


class BaseDetector(ABC):
    def __init__(self, config):
        self.config = config

    @abstractmethod
    def detect(self, img):
        pass
