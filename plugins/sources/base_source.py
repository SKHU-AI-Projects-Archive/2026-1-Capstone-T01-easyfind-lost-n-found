import time
from abc import ABC, abstractmethod


class RatePacer:
    """지정 fps로 호출 속도를 제어하는 페이서.

    perf_counter 기반 누적 방식이라 개별 sleep의 OS 스케줄링 오차가
    다음 주기에 보정되어 장기적으로 드리프트가 없다. (단순 sleep(1/fps)는
    프레임 처리 시간 + sleep 오차가 매 프레임 누적되어 실제 fps가 낮아진다.)

    소비(프레임 생성/디코딩)가 한 주기보다 오래 걸려 뒤처진 경우에는
    목표 시각을 현재 기준으로 부분 리셋해 과도한 따라잡기를 방지한다.
    """

    def __init__(self, fps):
        self.fps = float(fps)
        if self.fps <= 0:
            raise ValueError(f"[RatePacer] fps must be > 0, got {fps}")
        self._period = 1.0 / self.fps
        self._next_time = None

    def wait(self):
        now = time.perf_counter()
        if self._next_time is None:
            # 첫 호출은 기준 시각만 설정하고 대기하지 않는다.
            self._next_time = now + self._period
            return
        if now < self._next_time:
            time.sleep(self._next_time - now)
            now = time.perf_counter()
        self._next_time = max(self._next_time + self._period, now + self._period * 0.25)


class BaseSource(ABC):
    def __init__(self, config):
        self.config = config

    @abstractmethod
    def read(self):
        pass

    @abstractmethod
    def release(self):
        pass
