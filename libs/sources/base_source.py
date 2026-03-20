from abc import ABC, abstractmethod


class BaseSource(ABC):
    def __init__(self, config):
        self.config = config

    @abstractmethod
    def read(self):
        pass

    @abstractmethod
    def release(self):
        pass
