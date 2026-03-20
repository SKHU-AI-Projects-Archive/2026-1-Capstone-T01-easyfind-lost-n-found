import os
import csv
from .base_handler import BaseHandler


class FileLogHandler(BaseHandler):
    def __init__(self, config):
        super().__init__(config)
        self.output_dir = config.get('output_dir', './logs')
        os.makedirs(self.output_dir, exist_ok=True)

        filename = config.get('filename', 'result.csv')
        self.filepath = os.path.join(self.output_dir, filename)

        self.file = open(self.filepath, 'w', newline='', encoding='utf-8')
        self.writer = csv.writer(self.file)

        self.writer.writerow(['frame_id', 'x1', 'y1', 'x2', 'y2', 'track_id'])
        print(f"[FileLogHandler] Logging to {self.filepath}")

    def handle(self, data, shm_reader):
        fid = data.get('frame_id')
        tracks = data.get('tracks', [])

        for trk in tracks:
            row = [fid] + [x for x in trk]
            self.writer.writerow(row)

    def release(self):
        if self.file:
            self.file.close()
            print("[FileLogHandler] File closed.")
