import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from app.web import ParkingApplication

application = ParkingApplication()


class Handler(BaseHTTPRequestHandler):
    def _handle(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length else b""
        response = application.dispatch(
            self.command, self.path.split("?", 1)[0], dict(self.headers), body
        )
        self.send_response(response.status)
        self.send_header("Content-Type", response.content_type)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(response.body)

    do_GET = _handle
    do_POST = _handle


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    print(f"SmartParking disponivel em http://localhost:{port}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
