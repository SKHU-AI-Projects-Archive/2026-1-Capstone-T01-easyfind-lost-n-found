import multiprocessing as mp
import queue as _queue


class LatestSlot:
    """소비자가 느릴 때 중간 아이템을 폐기하고 최신 아이템만 전달하는 슬롯.

    mp.Queue(maxsize=1)을 내부 저장소로 사용한다. put() 호출 시 기존에
    읽히지 않은 구형 아이템을 먼저 꺼내 버린 뒤 새 아이템을 삽입하므로,
    슬롯에는 항상 가장 최근 아이템 하나만 남는다.

    제약: 단일 생산자(SourceStreamer) + 단일 소비자(PipelineExecutor) 구조 전용.
    두 생산자가 동시에 put()을 호출하면 drain-then-put 사이에 경쟁 조건이 생긴다.

    배경:
        mp.Queue는 FIFO 무제한 큐이므로, 카메라 fps보다 detector/tracker가 느릴 경우
        구형 프레임 메타데이터가 누적되고 파이프라인이 실시간을 따라가지 못한다.
        LatestSlot은 이 문제를 해결한다 — 소비자가 느려도 항상 최신 프레임을 처리한다.
    """

    def __init__(self):
        self._q = mp.Queue(maxsize=1)

    def put(self, item):
        """최신 아이템을 저장한다. 읽히지 않은 구형 아이템이 있으면 폐기한다."""
        try:
            self._q.get_nowait()
        except _queue.Empty:
            pass
        self._q.put(item)

    def get(self, timeout=None):
        """아이템이 준비될 때까지 블로킹한 뒤 반환한다."""
        return self._q.get(timeout=timeout)

    def get_nowait(self):
        return self._q.get_nowait()
