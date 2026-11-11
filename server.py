"""PayPilot demo-store server (Python stdlib, no deps)."""
import json, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from agent import run_agent
from catalog import CATALOG

class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/health":
            return self._send(200, {"ok": True, "service": "paypilot"})
        if path == "/api/catalog":
            return self._send(200, {"products": CATALOG})
        if path == "/" or path == "/index.html":
            with open("index.html", "rb") as f:
                return self._send(200, f.read(), "text/html")
        return self._send(404, {"error": "not found"})

    def do_POST(self):
        path = urlparse(self.path).path
        if path != "/api/agent/run":
            return self._send(404, {"error": "not found"})
        n = int(self.headers.get("Content-Length") or 0)
        req = json.loads(self.rfile.read(n) or b"{}")
        query = req.get("query") or ""
        budget = req.get("budget")
        try:
            result = run_agent(query, budget)
        except Exception as e:
            return self._send(500, {"ok": False, "error": str(e)})
        return self._send(200, result)

    def log_message(self, *a):
        pass

def serve(port=8080):
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()

if __name__ == "__main__":
    import os
    serve(int(os.environ.get("PORT", 8080)))
