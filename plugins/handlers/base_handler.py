from abc import ABC, abstractmethod


class BaseHandler(ABC):
    def __init__(self, config):
        self.config = config

    @abstractmethod
    def handle(self, data, shm_reader):
        pass

    def release(self):
        pass
