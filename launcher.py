"""
launcher.py — main.py 실행/정지를 HTTP API로 제어하는 독립 서버.
웹 대시보드에서 시스템을 켜고 끌 수 있게 한다.

사용법: python launcher.py
기본 포트: 5001
"""

import subprocess
import sys
import os
import threading
import logging
from flask import Flask, jsonify, request
from flask_cors import CORS

logging.getLogger('werkzeug').setLevel(logging.ERROR)

app = Flask(__name__)
CORS(app)

_lock = threading.Lock()
_process: subprocess.Popen | None = None
_config_path = ""

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _is_running() -> bool:
    return _process is not None and _process.poll() is None


@app.route("/api/launcher/configs")
def configs():
    configs_dir = os.path.join(BASE_DIR, "configs")
    files = sorted(
        f for f in os.listdir(configs_dir)
        if f.endswith(".yaml") and f != "default_config.yaml"
    )
    return jsonify({"configs": files})


@app.route("/api/launcher/status")
def status():
    with _lock:
        running = _is_running()
    return jsonify({"running": running, "config": _config_path})


@app.route("/api/launcher/start", methods=["POST"])
def start():
    global _process, _config_path
    data = request.get_json(silent=True) or {}
    config = data.get("config", _config_path)

    with _lock:
        if _is_running():
            return jsonify({"ok": False, "msg": "Already running"})
        _config_path = config
        _process = subprocess.Popen(
            [sys.executable, "main.py", "-c", config],
            cwd=BASE_DIR,
        )
    return jsonify({"ok": True, "pid": _process.pid})


@app.route("/api/launcher/stop", methods=["POST"])
def stop():
    global _process
    with _lock:
        if not _is_running():
            return jsonify({"ok": False, "msg": "Not running"})
        pid = _process.pid
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                capture_output=True,
            )
        else:
            _process.terminate()
            try:
                _process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                _process.kill()
        _process = None
    return jsonify({"ok": True})


if __name__ == "__main__":
    port = int(os.environ.get("LAUNCHER_PORT", 5001))
    print(f"[Launcher] Listening on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
