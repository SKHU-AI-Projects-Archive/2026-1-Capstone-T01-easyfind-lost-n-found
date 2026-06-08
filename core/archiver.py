import time
from datetime import datetime, date as date_cls
from pathlib import Path

import cv2


def collect_archive_frames(root, cam_id, start_ts, end_ts):
    """아카이브에서 [start_ts, end_ts] 범위의 JPEG 프레임을 시간순으로 수집한다.

    FrameArchiver의 저장 규칙({root}/{cam}/{date}/{HH}/{epoch_ms}.jpg)을 역이용한다.
    파일명(epoch_ms)을 파싱해 범위 내 (path, ts_sec) 목록을 정렬해 반환한다.
    소급 검색(SearchExecutor)의 입력 소스로 쓰인다.
    """
    root = Path(root)
    cam_dir = root / cam_id
    if not cam_dir.is_dir():
        return []

    # 범위에 걸치는 날짜 디렉토리만 순회
    start_day = datetime.fromtimestamp(start_ts).date()
    end_day = datetime.fromtimestamp(end_ts).date()

    results = []
    for date_dir in sorted(cam_dir.iterdir()):
        if not date_dir.is_dir():
            continue
        try:
            d = datetime.strptime(date_dir.name, '%Y-%m-%d').date()
        except ValueError:
            continue
        if d < start_day or d > end_day:
            continue
        for hour_dir in date_dir.iterdir():
            if not hour_dir.is_dir() or hour_dir.name == 'video':
                continue
            for jpg in hour_dir.glob('*.jpg'):
                try:
                    ts = int(jpg.stem) / 1000.0
                except ValueError:
                    continue
                if start_ts <= ts <= end_ts:
                    results.append((str(jpg), ts))

    results.sort(key=lambda x: x[1])
    return results


class FrameArchiver:
    """상시 파이프라인의 원본 프레임을 timestamp 기반으로 디스크에 보관한다.

    두 가지 모드를 config로 옵션화한다.
      - JPEG 주기 저장: jpeg_interval_sec 간격으로 1장.
          {root}/{cam}/{YYYY-MM-DD}/{HH}/{epoch_ms}.jpg
      - 비디오 세그먼트(옵션): save_video=True면 매 프레임을 mp4에 기록하고
        video_segment_sec 경과 시 새 파일로 회전.
          {root}/{cam}/{YYYY-MM-DD}/video/{epoch_sec}.mp4

    파일명을 epoch(ms/sec)로 두어 검색 시 시간 범위 매칭과 정렬을 단순화한다.
    소급 검색(core/search.py)은 이 JPEG들을 1차 소스로 사용한다.
    """

    def __init__(self, cam_id, config, fps=30):
        self.cam_id = cam_id
        self.enable = bool(config.get('enable', False))
        self.root = Path(config.get('root', 'archives'))
        self.jpeg_interval = float(config.get('jpeg_interval_sec', 5))
        self.save_video = bool(config.get('save_video', False))
        self.video_segment_sec = float(config.get('video_segment_sec', 60))
        self.fps = float(fps) if fps and fps > 0 else 30.0

        self._last_jpeg_ts = 0.0
        self._writer = None
        self._seg_start = 0.0

    def _dir_for(self, ts, *sub):
        dt = datetime.fromtimestamp(ts)
        d = self.root / self.cam_id / dt.strftime('%Y-%m-%d')
        for s in sub:
            d = d / s
        d.mkdir(parents=True, exist_ok=True)
        return d

    def write(self, frame, ts):
        if not self.enable or frame is None:
            return

        # --- JPEG 주기 저장 ---
        if ts - self._last_jpeg_ts >= self.jpeg_interval:
            dt = datetime.fromtimestamp(ts)
            out_dir = self._dir_for(ts, dt.strftime('%H'))
            cv2.imwrite(str(out_dir / f"{int(ts * 1000)}.jpg"), frame)
            self._last_jpeg_ts = ts

        # --- 비디오 세그먼트 ---
        if self.save_video:
            if self._writer is None or (ts - self._seg_start) >= self.video_segment_sec:
                self._open_segment(frame, ts)
            self._writer.write(frame)

    def _open_segment(self, frame, ts):
        self._close_writer()
        h, w = frame.shape[:2]
        out_dir = self._dir_for(ts, 'video')
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        path = str(out_dir / f"{int(ts)}.mp4")
        self._writer = cv2.VideoWriter(path, fourcc, self.fps, (w, h))
        self._seg_start = ts

    def _close_writer(self):
        if self._writer is not None:
            self._writer.release()
            self._writer = None

    def close(self):
        self._close_writer()
