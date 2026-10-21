"""Loopback-only read-only fixture dashboard."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from app import differences, redact, validate_fixture

ASSETS = Path(__file__).with_name('dashboard')
MIME = {'.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8','.js':'text/javascript; charset=utf-8'}

def fixture_files(root):
    return sorted(path.name for path in Path(root).glob('*.json') if path.is_file())

def load_fixture(root, name, patterns=()):
    if not isinstance(name, str) or Path(name).name != name or not name.endswith('.json'):
        raise ValueError('Invalid fixture name')
    path = Path(root) / name
    if not path.is_file(): raise ValueError('Fixture not found')
    with path.open(encoding='utf-8') as handle: fixture = json.load(handle)
    validate_fixture(fixture)
    return redact(fixture, patterns)

def create_dashboard(root, port=8765, patterns=()):
    root = Path(root).resolve()
    if not root.is_dir(): raise ValueError('Fixture directory not found')
    if type(port) is not int or not 0 <= port <= 65535: raise ValueError('Port must be from 0 to 65535')
    class Handler(BaseHTTPRequestHandler):
        def send_bytes(self, status, body, content_type):
            self.send_response(status);self.send_header('Content-Type',content_type);self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(body)
        def send_json(self, status, value): self.send_bytes(status,json.dumps(value).encode(), 'application/json; charset=utf-8')
        def do_GET(self):
            parsed=urlsplit(self.path)
            try:
                if parsed.path == '/api/fixtures': return self.send_json(200,{'fixtures':fixture_files(root)})
                if parsed.path == '/api/fixture': return self.send_json(200,load_fixture(root,parse_qs(parsed.query).get('name',[''])[0],patterns))
                if parsed.path == '/api/diff':
                    query=parse_qs(parsed.query);before=load_fixture(root,query.get('before',[''])[0],patterns);after=load_fixture(root,query.get('after',[''])[0],patterns)
                    return self.send_json(200,{'changes':differences(before,after)})
                asset='index.html' if parsed.path=='/' else parsed.path.removeprefix('/')
                if asset not in {'index.html','style.css','app.js'}: return self.send_json(404,{'error':'Not found'})
                body=(ASSETS/asset).read_bytes();return self.send_bytes(200,body,MIME[Path(asset).suffix])
            except (OSError,ValueError,json.JSONDecodeError) as exc:return self.send_json(400,{'error':str(exc)})
        def log_message(self,*args): pass
    return ThreadingHTTPServer(('127.0.0.1',port),Handler)
