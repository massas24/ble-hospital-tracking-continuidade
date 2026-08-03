"""
Simulação local mínima do listener HTTP do Mirth, para testes quando o servidor Mirth real (192.168.1.117:6661) não está acessível (por exemplo, a trabalhar em casa, fora da rede do hospital).
Apenas regista qualquer JSON enviado via POST e responde com 200 OK - não replica nenhum comportamento real de um canal Mirth.
Uso:

python mock_mirth.py [--port 6661]
Aponte o backend para o mesmo durante os testes locais (antes de iniciar o app.py):
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
