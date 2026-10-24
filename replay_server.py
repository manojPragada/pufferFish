"""Loopback-only fixture server. No upstream requests or recorded-header replay."""
import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
from app import redact, validate_fixture

def compile_routes(fixture):
    """Validate either one legacy fixture or a bounded exact-match collection."""
    if isinstance(fixture,dict) and 'routes' in fixture:
        routes=fixture.get('routes')
        if fixture.get('version')!=1 or not isinstance(routes,list) or not 1<=len(routes)<=100:
            raise ValueError('Route collection must have version 1 and 1–100 routes')
        compiled={}
        for item in routes:
            if not isinstance(item,dict):raise ValueError('Each route must be a fixture object')
            request=item.get('request',{});method=request.get('method');path=request.get('path')
            if method not in ('GET','HEAD') or not isinstance(path,str) or not path.startswith('/') or '?' in path or '#' in path:
                raise ValueError('Route requests require GET/HEAD and an absolute path without query or fragment')
            key=(method,path)
            if key in compiled:raise ValueError(f'Duplicate route: {method} {path}')
            compiled[key]=validate_fixture(item)
        return compiled
    return {('*','*'):validate_fixture(fixture)}


def create_server(fixture, port=8766, status=None, delay_ms=0, patterns=()):
    routes=compile_routes(fixture)
    if status is not None and (type(status) is not int or not 200 <= status <= 599):
        raise ValueError('Mock status must be an integer from 200 to 599')
    if type(delay_ms) is not int or not 0 <= delay_ms <= 30000:
        raise ValueError('Mock delay must be an integer from 0 to 30000 milliseconds')
    if type(port) is not int or not 0 <= port <= 65535:
        raise ValueError('Port must be an integer from 0 to 65535')
    class Handler(BaseHTTPRequestHandler):
        def respond(self, head=False):
            if delay_ms:
                time.sleep(delay_ms / 1000)
            path=urlsplit(self.path).path
            response=routes.get((self.command,path)) or (routes.get(('GET',path)) if head else None) or routes.get(('*','*'))
            if response is None:
                code=404;payload=json.dumps({'error':'No fixture matched','method':self.command,'path':path}).encode('utf-8')
            else:
                code=response['status'] if status is None else status
                payload=json.dumps(redact(response['body'],patterns),allow_nan=False).encode('utf-8')
                if code in (204,205,304):payload=b''
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

