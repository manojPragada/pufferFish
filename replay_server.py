"""Loopback-only fixture server. No upstream requests or recorded-header replay."""
import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from app import redact, validate_fixture


def create_server(fixture, port=8766, status=None, delay_ms=0, patterns=()):
    response = validate_fixture(fixture)
    code = response['status'] if status is None else status
    if type(code) is not int or not 200 <= code <= 599:
        raise ValueError('Mock status must be an integer from 200 to 599')
    if type(delay_ms) is not int or not 0 <= delay_ms <= 30000:
        raise ValueError('Mock delay must be an integer from 0 to 30000 milliseconds')
    if type(port) is not int or not 0 <= port <= 65535:
        raise ValueError('Port must be an integer from 0 to 65535')
    payload = json.dumps(redact(response['body'], patterns), allow_nan=False).encode('utf-8')
    if code in (204, 205, 304):
        payload = b''

    class Handler(BaseHTTPRequestHandler):
        def respond(self, head=False):
            if delay_ms:
                time.sleep(delay_ms / 1000)
            self.send_response(code)
            # Recorded cookies, redirects and hop-by-hop headers are intentionally omitted.
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(payload)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            if not head:
                try:
                    self.wfile.write(payload)
                except (BrokenPipeError, ConnectionResetError):
                    pass

        def do_GET(self):
            self.respond()

        def do_HEAD(self):
            self.respond(head=True)

        def log_message(self, *args):
            pass

    return ThreadingHTTPServer(('127.0.0.1', port), Handler)

