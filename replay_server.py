"""Loopback-only fixture server. No upstream requests or recorded-header replay."""
import json
import time
import hashlib
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
from app import redact, validate_fixture

SAFE_MATCH_HEADERS={'accept','content-type'}

def _compile_match_headers(request):
    headers=request.get('match_headers',{})
    if not isinstance(headers,dict) or len(headers)>10:
        raise ValueError('match_headers must be an object with at most 10 entries')
    compiled={}
    for name,value in headers.items():
        normalized=name.lower() if isinstance(name,str) else ''
        if normalized not in SAFE_MATCH_HEADERS and not normalized.startswith('x-puffer-'):
            raise ValueError('Only Accept, Content-Type and X-Puffer-* headers may be matched')
        if not isinstance(value,str) or len(value)>256 or '\r' in value or '\n' in value:
            raise ValueError('Matched header values must be strings of at most 256 characters')
        compiled[normalized]=value
    return compiled

def compile_routes(fixture):
    """Validate either one legacy fixture or a bounded exact-match collection."""
    if isinstance(fixture,dict) and 'routes' in fixture:
        routes=fixture.get('routes')
        if fixture.get('version')!=1 or not isinstance(routes,list) or not 1<=len(routes)<=100:
            raise ValueError('Route collection must have version 1 and 1–100 routes')
        compiled=[];seen=set()
        for item in routes:
            if not isinstance(item,dict):raise ValueError('Each route must be a fixture object')
            request=item.get('request',{});method=request.get('method');path=request.get('path')
            if method not in ('GET','HEAD','POST') or not isinstance(path,str) or not path.startswith('/') or '?' in path or '#' in path:
                raise ValueError('Route requests require GET/HEAD/POST and an absolute path without query or fragment')
            digest=request.get('body_sha256')
            if digest is not None and (method!='POST' or not isinstance(digest,str) or re.fullmatch(r'[0-9a-f]{64}',digest) is None):raise ValueError('body_sha256 requires POST and a lowercase SHA-256 digest')
            headers=_compile_match_headers(request);key=(method,path,tuple(sorted(headers.items())),digest)
            if key in seen:raise ValueError(f'Duplicate route: {method} {path}')
            seen.add(key);compiled.append((method,path,headers,digest,validate_fixture(item)))
        return compiled
    return [('*','*',{},None,validate_fixture(fixture))]


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
            length=int(self.headers.get('Content-Length','0')) if self.command=='POST' else 0
            if length<0 or length>1_048_576:self.send_error(413);return
            body_digest=hashlib.sha256(self.rfile.read(length)).hexdigest() if self.command=='POST' else None
            candidates=[]
            for method,route_path,headers,expected_digest,fixture_response in routes:
                method_matches=method==self.command or (head and method=='GET') or method=='*'
                if method_matches and (route_path==path or route_path=='*'):
                    if all(self.headers.get(name)==value for name,value in headers.items()) and (expected_digest is None or expected_digest==body_digest):
                        candidates.append((len(headers)+int(expected_digest is not None),fixture_response))
            response=max(candidates,key=lambda item:item[0])[1] if candidates else None
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

        def do_POST(self):
            self.respond()

        def log_message(self, *args):
            pass

    return ThreadingHTTPServer(('127.0.0.1', port), Handler)

