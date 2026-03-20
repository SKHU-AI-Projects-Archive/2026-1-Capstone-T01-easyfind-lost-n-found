from abc import ABC, abstractmethod


class BaseTracker(ABC):
    def __init__(self, config):
        self.config = config

    @abstractmethod
    def update(self, dets, img):
        pass
