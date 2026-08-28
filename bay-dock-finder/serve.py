"""Dev server for Dock Finder.

Python's stock http.server reads MIME types from the Windows registry, where
.js is often mapped to text/plain — and a service worker served as text/plain
is rejected by the browser. This pins the types that matter.

    python serve.py [port]
"""
import sys
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler


class Handler(SimpleHTTPRequestHandler):
    # Keep-alive on a single-threaded server deadlocks the browser: the service
    # worker's script fetch queues behind the page's own held-open connection.
    protocol_version = "HTTP/1.1"

    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".js": "application/javascript",
        ".mjs": "application/javascript",
        ".json": "application/json",
        ".webmanifest": "application/manifest+json",
        ".css": "text/css",
        ".html": "text/html",
        ".png": "image/png",
        ".svg": "image/svg+xml",
    }

    def end_headers(self):
        # Never let the browser hold on to the app shell during development.
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8731
    here = __file__.rsplit("\\", 1)[0].rsplit("/", 1)[0]
    print(f"Dock Finder on http://localhost:{port}  (ctrl-c to stop)")
    ThreadingHTTPServer(("0.0.0.0", port), partial(Handler, directory=here)).serve_forever()
