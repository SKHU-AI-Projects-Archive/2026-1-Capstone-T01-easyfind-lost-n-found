import sys
import time
import cv2
from .base_source import BaseSource


class WebcamSource(BaseSource):
    """다양한 웹캠 모델 / 노트북 내장캠 / OS 환경에서 견고하게 동작하는 웹캠 소스.

    - OS별 안정 백엔드를 우선순위대로 폴백 (Windows: DSHOW→MSMF→ANY 등)
    - isOpened()만 믿지 않고 실제 프레임 read까지 검증 후 백엔드 확정
    - fourcc/해상도/fps 설정은 실패해도 진행하고 실제 적용값을 로깅
    - 첫 프레임 워밍업으로 검은/빈 프레임 흡수
    - read() 일시 실패(USB 글리치 등)는 재시도로 흡수
    """

    def __init__(self, config):
        super().__init__(config)

        self.device_index = int(config.get("device_index", 0))
        self.width = int(config.get("width", 1920))
        self.height = int(config.get("height", 1080))
        self.fps = float(config.get("fps", 30))
        # MJPG 등 fourcc 강제는 옵션. 지원 안 하는 캠을 위해 빈 문자열/None이면 캠 기본값 사용.
        self.fourcc = config.get("fourcc", "MJPG")
        # read 일시 실패 시 재시도 횟수 (USB 글리치/워밍업 흡수)
        self.read_retries = int(config.get("read_retries", 5))

        self.cap = self._open_capture()
        self._configure(self.cap)
        self._warmup(self.cap)

    def _backend_candidates(self):
        """OS별로 안정적인 백엔드를 우선순위대로 반환."""
        if sys.platform.startswith("win"):
            return [("DSHOW", cv2.CAP_DSHOW), ("MSMF", cv2.CAP_MSMF), ("ANY", cv2.CAP_ANY)]
        if sys.platform.startswith("linux"):
            return [("V4L2", cv2.CAP_V4L2), ("ANY", cv2.CAP_ANY)]
        if sys.platform == "darwin":
            return [("AVFOUNDATION", cv2.CAP_AVFOUNDATION), ("ANY", cv2.CAP_ANY)]
        return [("ANY", cv2.CAP_ANY)]

    def _open_capture(self):
        """백엔드를 순서대로 시도하고, isOpened + 실제 read까지 성공하는 첫 백엔드를 사용."""
        last_err = None
        for name, backend in self._backend_candidates():
            cap = cv2.VideoCapture(self.device_index, backend)
            if not cap.isOpened():
                cap.release()
                last_err = f"{name}: isOpened()==False"
                continue
            # isOpened()만으로는 부족 — 실제 프레임을 한 장 읽어 검증
            ok = False
            for _ in range(10):
                ret, frame = cap.read()
                if ret and frame is not None:
                    ok = True
                    break
                time.sleep(0.05)
            if ok:
                print(f"[WebcamSource] Opened device {self.device_index} via {name}")
                return cap
            cap.release()
            last_err = f"{name}: opened but no frame"

        raise RuntimeError(
            f"[WebcamSource] Cannot open camera {self.device_index}. last error: {last_err}"
        )

    def _configure(self, cap):
        """fourcc/해상도/fps 설정을 시도하되 실패해도 진행하고 실제 적용값을 로깅한다.
        실제 해상도가 요청과 달라도 streamer가 리사이즈하므로 강제하지 않는다."""
        if self.fourcc:
            try:
                cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*self.fourcc))
            except Exception:
                pass  # 미지원 fourcc — 캠 기본 포맷으로 진행
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        cap.set(cv2.CAP_PROP_FPS, self.fps)

        actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = cap.get(cv2.CAP_PROP_FPS)
        if (actual_w, actual_h) != (self.width, self.height):
            print(f"[WebcamSource] Requested {self.width}x{self.height}, "
                  f"camera provides {actual_w}x{actual_h} (streamer will resize)")
        print(f"[WebcamSource] Active: {actual_w}x{actual_h} @ {actual_fps:.0f}fps")

    def _warmup(self, cap, frames=3):
        """일부 캠은 첫 몇 프레임이 비거나 노출/화이트밸런스가 안 잡힘 → 버려서 안정화."""
        for _ in range(frames):
            cap.read()

    def read(self):
        """일시적 read 실패(USB 글리치 등)를 재시도로 흡수. 끝까지 실패하면 (False, None).

        소프트웨어 fps 페이싱은 하지 않는다 — 웹캠은 cap.read()가 하드웨어 fps로
        블로킹되어 자연 동기화되며(_configure에서 CAP_PROP_FPS로 요청), 소프트웨어로
        더 느리게 페이싱하면 드라이버 버퍼에 프레임이 쌓여 지연(latency)만 늘어난다.
        """
        for _ in range(max(1, self.read_retries)):
            ret, frame = self.cap.read()
            if ret and frame is not None:
                return True, frame
            time.sleep(0.02)
        return False, None

    def release(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        print("[WebcamSource] Released.")
