"""Local JSON HTTP fixtures with conservative credential redaction."""
import argparse
import hashlib
from fnmatch import fnmatchcase
import json
import sys
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError
SENSITIVE = {'authorization', 'cookie', 'set-cookie', 'password', 'token', 'access_token', 'refresh_token', 'api_key', 'x-api-key', 'secret'}
def sensitive(key, patterns=()):
    return key.lower() in SENSITIVE or any(fnmatchcase(key.lower(), pattern.lower()) for pattern in patterns)

def redact(value, patterns=()):
    if isinstance(value, dict):
        return {k: '[REDACTED]' if sensitive(k, patterns) else redact(v, patterns) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v, patterns) for v in value]
    return value
def safe_url(url, patterns=()):
    parts = urlsplit(url)
    if parts.scheme not in {'http', 'https'} or not parts.hostname or parts.username or parts.password:
        raise ValueError('Use an HTTP(S) URL without embedded credentials')
    query = urlencode([(k, '[REDACTED]' if sensitive(k, patterns) else v) for k,v in parse_qsl(parts.query, keep_blank_values=True)])
    return urlunsplit((parts.scheme, parts.netloc, parts.path, query, ''))
class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def record(url, patterns=()):
    sanitized = safe_url(url, patterns)
    request = Request(url, headers={'Accept':'application/json'})
    try:
        response = build_opener(NoRedirect).open(request, timeout=10)
    except HTTPError as exc:
        response = exc
    with response:
        raw = response.read(1_048_577)
        if len(raw) > 1_048_576:
            raise ValueError('Response exceeds 1 MiB')
        # JSON only: arbitrary text may contain unstructured credentials.
        body = json.loads(raw)
        return {'version':1, 'request':{'method':'GET', 'url':sanitized},
                'response':{'status':response.code, 'headers':redact(dict(response.headers), patterns), 'body':redact(body, patterns)}}
def validate_fixture(fixture):
    if not isinstance(fixture, dict) or type(fixture.get('version')) is not int or fixture['version'] != 1:
        raise ValueError('Fixture must be an object with version 1')
    response = fixture.get('response')
    if not isinstance(response, dict) or 'body' not in response:
        raise ValueError('Fixture response must contain a body')
    status = response.get('status')
    headers = response.get('headers')
    if type(status) is not int or not 100 <= status <= 599:
        raise ValueError('Fixture response status must be an integer from 100 to 599')
    if not isinstance(headers, dict) or not all(isinstance(k, str) and isinstance(v, str) for k,v in headers.items()):
        raise ValueError('Fixture response headers must map strings to strings')
    return response

def differences(old, new, path='$'):
    if type(old) is not type(new):
        return [{'path':path,'before':old,'after':new}]
    if isinstance(old,dict):
        result=[]
        for key in sorted(old.keys() | new.keys()):
            p=path+'['+json.dumps(key)+']'
            if key not in old: result.append({'path':p,'kind':'added','after':new[key]})
            elif key not in new: result.append({'path':p,'kind':'removed','before':old[key]})
            else: result.extend(differences(old[key],new[key],p))
        return result
    if isinstance(old, list):
        # Positional comparison: insertions may shift following elements.
        result = []
        for index in range(max(len(old), len(new))):
            item_path = f'{path}[{index}]'
            if index >= len(old):
                result.append({'path': item_path, 'kind': 'added', 'after': new[index]})
            elif index >= len(new):
                result.append({'path': item_path, 'kind': 'removed', 'before': old[index]})
            else:
                result.extend(differences(old[index], new[index], item_path))
        return result
    if old != new: return [{'path':path,'before':old,'after':new}]
    return []
def body_digest(path):
    with open(path,'rb') as source:
        raw=source.read(1_048_577)
    if len(raw)>1_048_576:raise ValueError('Request body exceeds 1 MiB')
    return hashlib.sha256(raw).hexdigest()
def route_fixture(fixture,method,path,body_sha256=None):
    response=validate_fixture(fixture);method=method.upper()
    if method not in {'GET','HEAD','POST'} or not isinstance(path,str) or not path.startswith('/') or '?' in path or '#' in path:raise ValueError('Route requires GET/HEAD/POST and an absolute path without query or fragment')
    request={'method':method,'path':path}
    route={'request':request,'response':response,'version':1}
    if body_sha256 is not None:
        if method!='POST' or len(body_sha256)!=64 or any(ch not in '0123456789abcdef' for ch in body_sha256):raise ValueError('Body digest requires POST and 64 lowercase hex characters')
        request['body_sha256']=body_sha256
    return {'version':1,'routes':[route]}
def append_route(collection,fixture,method,path,body_sha256=None):
    from replay_server import compile_routes
    compile_routes(collection)
    routes=collection.get('routes')
    if not isinstance(routes,list) or len(routes)>=100:raise ValueError('Route collection must contain fewer than 100 routes before append')
    candidate=route_fixture(fixture,method,path,body_sha256)['routes'][0]
    result={'version':1,'routes':[*routes,candidate]}
    compile_routes(result)
    return result
def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    r=sub.add_parser('record');r.add_argument('url');r.add_argument('output')
    r=sub.add_parser('replay',help='Print a saved response offline; sends no requests');r.add_argument('fixture')
    r=sub.add_parser('diff');r.add_argument('before');r.add_argument('after')
    r=sub.add_parser('serve',help='Serve a saved JSON body on loopback only');r.add_argument('fixture');r.add_argument('--port',type=int,default=8766);r.add_argument('--status',type=int);r.add_argument('--delay-ms',type=int,default=0)
    r=sub.add_parser('dashboard',help='Browse and compare a directory of fixtures on loopback');r.add_argument('directory');r.add_argument('--port',type=int,default=8765)
    r=sub.add_parser('body-digest',help='Print a SHA-256 digest for a local request body without storing its content');r.add_argument('file')
    r=sub.add_parser('fixture-route',help='Create a one-route collection from an existing fixture');r.add_argument('fixture');r.add_argument('output');r.add_argument('--method',default='GET');r.add_argument('--path',default='/');r.add_argument('--body-sha256')
    r=sub.add_parser('fixture-append',help='Create a new collection by safely appending one route');r.add_argument('collection');r.add_argument('fixture');r.add_argument('output');r.add_argument('--method',default='GET');r.add_argument('--path',default='/');r.add_argument('--body-sha256')
    for command in sub.choices.values():
        command.add_argument('--redact-key', action='append', default=[], metavar='GLOB', help='Additional case-insensitive key glob; repeatable and additive to built-ins')
    a=p.parse_args()
    try:
        if a.command=='body-digest':print(body_digest(a.file));return 0
        if a.command=='fixture-route':
            with open(a.fixture,encoding='utf-8') as f:result=route_fixture(json.load(f),a.method,a.path,a.body_sha256)
            with open(a.output,'x',encoding='utf-8') as f:json.dump(result,f,indent=2)
            return 0
        if a.command=='fixture-append':
            with open(a.collection,encoding='utf-8') as f:collection=json.load(f)
            with open(a.fixture,encoding='utf-8') as f:fixture=json.load(f)
            result=append_route(collection,fixture,a.method,a.path,a.body_sha256)
            with open(a.output,'x',encoding='utf-8') as f:json.dump(result,f,indent=2)
            return 0
        if a.command=='record':
            result=record(a.url, a.redact_key)
            # Exclusive creation prevents accidental fixture replacement.
            with open(a.output,'x',encoding='utf-8') as f: json.dump(result,f,indent=2)
        elif a.command=='serve':
            from replay_server import create_server
            with open(a.fixture,encoding='utf-8') as f: fixture=json.load(f)
            with create_server(fixture,a.port,a.status,a.delay_ms,a.redact_key) as server:
                print(f'Mock listening on http://127.0.0.1:{server.server_port} (GET/HEAD, all paths)',flush=True)
                try: server.serve_forever()
                except KeyboardInterrupt: pass
        elif a.command=='dashboard':
            from dashboard import create_dashboard
            with create_dashboard(a.directory,a.port,a.redact_key) as server:
                print(f'Dashboard listening on http://127.0.0.1:{server.server_port}',flush=True)
                try: server.serve_forever()
                except KeyboardInterrupt: pass
        elif a.command=='replay':
            with open(a.fixture,encoding='utf-8') as f: result=redact(validate_fixture(json.load(f)), a.redact_key)
            print(json.dumps(result,indent=2))
        else:
            with open(a.before,encoding='utf-8') as f: old=redact(json.load(f), a.redact_key)
            with open(a.after,encoding='utf-8') as f: new=redact(json.load(f), a.redact_key)
            result=differences(old,new);print(json.dumps(result,indent=2));return int(bool(result))
        return 0
    except (OSError,ValueError,KeyError) as exc:
        print(str(exc),file=sys.stderr);return 2
if __name__=='__main__': sys.exit(main())



