from http.server import BaseHTTPRequestHandler
from pathlib import Path
import json
import sys

# Add root directory to sys.path to import the knowledge base from app.py
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from app import handle_recommend, handle_struggles  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        url_path = self.path.split("?")[0]
        if url_path in ("/struggles", "/api/struggles"):
            action = handle_struggles
        elif url_path in ("/recommend", "/api/recommend"):
            action = handle_recommend
        else:
            self.send_error(404)
            return

        data = self._read_json()
        if data is None:
            self.send_error(400, "Please send valid JSON")
            return
        status, payload = action(data)
        if status != 200:
            self.send_error(status, payload)
            return
        self._send_json(payload)

    def do_GET(self):
        # Health check
        self._send_json({"status": "ok", "app": "Study Buddy Expert System"})

    def _read_json(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            if length <= 0 or length > 20000:
                raise ValueError
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError
            return data
        except Exception:
            return None

    def _send_json(self, obj, status=200):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
