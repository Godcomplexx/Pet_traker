from __future__ import annotations

import argparse
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OVERRIDES_PATH = ROOT / "hat-placement-overrides.json"
REVIEW_PATH = ROOT / "character-animation-review.json"


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self) -> None:
        request_path = self.path.split("?", 1)[0]
        if request_path == "/hat-placement-overrides.json" and not OVERRIDES_PATH.exists():
            self.send_json({})
            return
        if request_path == "/character-animation-review.json" and not REVIEW_PATH.exists():
            self.send_json({})
            return
        super().do_GET()

    def send_json(self, data: dict) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def do_POST(self) -> None:
        request_path = self.path.split("?", 1)[0]
        targets = {
            "/save-hat-overrides": OVERRIDES_PATH,
            "/save-character-animation-review": REVIEW_PATH,
        }
        target_path = targets.get(request_path)
        if target_path is None:
            self.send_error(404)
            return

        length = int(self.headers.get("Content-Length") or 0)
        try:
            data = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(data, dict):
                raise ValueError("Payload must be an object")
            target_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        except Exception as exc:
            self.send_response(400)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(str(exc).encode("utf-8"))
            return

        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps({"ok": True, "path": str(target_path)}).encode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8011)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"http://{args.host}:{args.port}/hat-tuner.html", flush=True)
    print(f"http://{args.host}:{args.port}/character-animation-review.html", flush=True)
    print(f"http://{args.host}:{args.port}/accessory-preview.html", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
