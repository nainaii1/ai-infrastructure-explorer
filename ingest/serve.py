"""Local control server for the AI Infrastructure Explorer.

Serves the static app (index.html + data.js) AND exposes one endpoint the
Watchlist "Fetch prices" button calls:

    POST /api/fetch-prices   ->  runs fetch_prices.run(), rewrites data.js,
                                 returns {updated, failed, asOf}

Run it, then open the printed URL. Plain double-click of index.html still works
offline (read-only, last-fetched prices); the button only needs this server.

    python3 ingest/serve.py        # then open http://localhost:8765/

No secrets, no third-party deps.
"""

import sys
import json
import pathlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import fetch_prices

ING = pathlib.Path(__file__).resolve().parent
ROOT = ING.parent
PORT = 8765


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        # Always serve fresh data.js so a price update shows on reload.
        self.send_header("Cache-Control", "no-store, must-revalidate")
        super().end_headers()

    def do_POST(self):
        if self.path.rstrip("/") != "/api/fetch-prices":
            self.send_error(404, "Not found")
            return
        try:
            summary = fetch_prices.run()
            body = json.dumps(summary).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as exc:  # never crash the server on a fetch error
            body = json.dumps({"error": str(exc)}).encode("utf-8")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    def log_message(self, fmt, *args):
        sys.stderr.write("[serve] " + (fmt % args) + "\n")


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print("AI Infrastructure Explorer running at  http://localhost:{}/".format(port))
    print("Watchlist 'Fetch prices' button will update prices via this server.")
    print("Ctrl-C to stop.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.shutdown()


if __name__ == "__main__":
    main()
