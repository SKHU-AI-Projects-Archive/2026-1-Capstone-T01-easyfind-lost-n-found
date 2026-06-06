import time
import numpy as np
import cv2
from .base_source import BaseSource
from core.archiver import collect_archive_frames


class ArchiveSource(BaseSource):
    """아카이브된 프레임을 소급 검색용으로 공급하는 소스.

    평소 read()는 job_q에서 검색 잡을 대기한다(idle). 잡을 받으면 archive에서
    [start_ts, end_ts] 프레임을 시간순으로 모아 한 장씩 공급하며, 각 프레임에
    검색 메타(job_id/prompt/ts/idx/total)를 실어 보낸다(consume_meta로 노출).
    잡 소진/중지 시 done 메타를 1회 보내고 다음 잡을 대기한다.

    제어 핸들(job_q/pause/stop)은 SourceStreamer가 set_control로 주입한다.
    검색은 detector(YOLOWorld)만 거치므로 이 소스를 쓰는 파이프라인은 tracker를 둔다.
    """

    def __init__(self, config):
        super().__init__(config)
        self.width = int(config.get('width', 640))
        self.height = int(config.get('height', 480))
        self.root = config.get('root', 'archives')
        self.interval_sec = float(config.get('interval_sec', 0))

        self.job_q = None
        self.pause_event = None
        self.stop_event = None

        self._frames = []       # [(path, ts)]
        self._idx = 0
        self._job = None
        self._meta = None       # 직전 read의 검색 메타 (streamer가 consume)

    def set_control(self, job_q, pause=None, stop=None):
        self.job_q = job_q
        self.pause_event = pause
        self.stop_event = stop

    def _blank(self):
        return np.zeros((self.height, self.width, 3), np.uint8)

    def _load_job(self, job):
        self._job = job
        frames = collect_archive_frames(self.root, job['cam'],
                                        job['start_ts'], job['end_ts'])
        self._frames = self._sample(frames, float(job.get('interval_sec', self.interval_sec)))
        self._idx = 0
        print(f"[ArchiveSource] job {job.get('job_id')}: {len(self._frames)} frames to scan "
              f"(cam={job.get('cam')})", flush=True)
        if self.stop_event is not None:
            self.stop_event.clear()

    @staticmethod
    def _sample(frames, interval):
        if interval <= 0:
            return frames
        out, nxt = [], None
        for path, ts in frames:
            if nxt is None or ts >= nxt:
                out.append((path, ts))
                nxt = ts + interval
        return out

    def read(self):
        # 진행 중인 잡이 없으면 새 잡 대기 (프레임 공급 없이 idle)
        while self._job is None:
            if self.job_q is None:
                time.sleep(0.5)
                continue
            job = self.job_q.get()         # 블록
            if job is None:
                return False, None          # 종료 센티널 → streamer 종료
            self._load_job(job)

        # 중지 요청 → 현재 잡 종료
        if self.stop_event is not None and self.stop_event.is_set():
            return self._finish_job()

        # 일시정지 → 프레임 공급 없이 대기
        while self.pause_event is not None and self.pause_event.is_set():
            if self.stop_event is not None and self.stop_event.is_set():
                return self._finish_job()
            time.sleep(0.1)

        # 잡 소진 → done
        if self._idx >= len(self._frames):
            return self._finish_job()

        path, ts = self._frames[self._idx]
        img = cv2.imread(path)
        self._meta = {'search': {
            'job_id': self._job['job_id'], 'prompt': self._job.get('prompt', ''),
            'ts': ts, 'idx': self._idx, 'total': len(self._frames),
        }}
        self._idx += 1
        return True, (img if img is not None else self._blank())

    def _finish_job(self):
        job_id = self._job['job_id'] if self._job else None
        self._meta = {'search': {'job_id': job_id, 'done': True}}
        self._job = None
        self._frames = []
        self._idx = 0
        return True, self._blank()

    def consume_meta(self):
        m, self._meta = self._meta, None
        return m

    def release(self):
        pass
