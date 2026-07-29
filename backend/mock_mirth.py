"""
Minimal local mock of the Mirth HTTP listener, for testing when the real
Mirth server (192.168.1.117:6661) isn't reachable (e.g. working from home,
outside the hospital network).

Just logs whatever JSON is POSTed to it and replies 200 OK - it does not
replicate any real Mirth channel behavior.

Usage:
    python mock_mirth.py [--port 6661]

Point the backend at it during local testing (before starting app.py):
    # PowerShell
    $env:MIRTH_URL = "http://localhost:6661"
    python app.py
"""

import argparse
import json
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer


class MockMirthHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(length) if length else b""

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n[{timestamp}] POST {self.path}")
        try:
            body = json.loads(raw_body) if raw_body else {}
            print(json.dumps(body, indent=2, ensure_ascii=False))
        except json.JSONDecodeError:
            print(f"(corpo nao-JSON, {len(raw_body)} bytes): {raw_body!r}")

        response = json.dumps({"status": "ok", "received_by": "mock_mirth"}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, format, *args):
        # Silence the default per-request access log line; we print our own.
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=6661)
    args = parser.parse_args()

    server = HTTPServer(("0.0.0.0", args.port), MockMirthHandler)
    print(f"Mock Mirth a escutar em http://0.0.0.0:{args.port} (Ctrl+C para parar)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nA parar mock Mirth...")
        server.server_close()


if __name__ == "__main__":
    main()
