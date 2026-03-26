import cv2
from .base_source import BaseSource

class WebcamSource(BaseSource):
    def __init__(self, config):
        super().__init__(config)

        self.device_index = int(config.get("device_index", 0))
        self.width = int(config.get("width", 1920))
        self.height = int(config.get("height", 1080))
        self.fps = float(config.get("fps", 30))
        
        import platform
        if platform.system() == "Windows":
            backend = cv2.CAP_DSHOW
        elif platform.system() == "Linux":
            backend = cv2.CAP_V4L2
        else:
            backend = cv2.CAP_ANY

        self.cap = cv2.VideoCapture(self.device_index, backend)
        if not self.cap.isOpened():
            raise RuntimeError(f"Cannot open camera: {self.device_index}")

        self.cap.set(
            cv2.CAP_PROP_FOURCC,
            cv2.VideoWriter_fourcc(*"MJPG")
        )
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)

    def read(self):
        return self.cap.read()

    def release(self):
        self.cap.release()
