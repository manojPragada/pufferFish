"""Local JSON HTTP fixtures with conservative credential redaction."""
import argparse
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
    if old != new: return [{'path':path,'before':old,'after':new}]
    return []
def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    r=sub.add_parser('record');r.add_argument('url');r.add_argument('output')
    r=sub.add_parser('replay',help='Print a saved response offline; sends no requests');r.add_argument('fixture')
    r=sub.add_parser('diff');r.add_argument('before');r.add_argument('after')
    r=sub.add_parser('serve',help='Serve a saved JSON body on loopback only');r.add_argument('fixture');r.add_argument('--port',type=int,default=8766);r.add_argument('--status',type=int);r.add_argument('--delay-ms',type=int,default=0)
    for command in sub.choices.values():
        command.add_argument('--redact-key', action='append', default=[], metavar='GLOB', help='Additional case-insensitive key glob; repeatable and additive to built-ins')
    a=p.parse_args()
    try:
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


