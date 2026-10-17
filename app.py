"""Local JSON HTTP fixtures with conservative credential redaction."""
import argparse
import json
import sys
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError
SENSITIVE = {'authorization', 'cookie', 'set-cookie', 'password', 'token', 'access_token', 'refresh_token', 'api_key', 'x-api-key', 'secret'}
def redact(value):
    if isinstance(value, dict):
        return {k: '[REDACTED]' if k.lower() in SENSITIVE else redact(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    return value
def safe_url(url):
    parts = urlsplit(url)
    if parts.scheme not in {'http', 'https'} or not parts.hostname or parts.username or parts.password:
        raise ValueError('Use an HTTP(S) URL without embedded credentials')
    query = urlencode([(k, '[REDACTED]' if k.lower() in SENSITIVE else v) for k,v in parse_qsl(parts.query, keep_blank_values=True)])
    return urlunsplit((parts.scheme, parts.netloc, parts.path, query, ''))
class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def record(url):
    sanitized = safe_url(url)
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
                'response':{'status':response.code, 'headers':redact(dict(response.headers)), 'body':redact(body)}}
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
    a=p.parse_args()
    try:
        if a.command=='record':
            result=record(a.url)
            # Exclusive creation prevents accidental fixture replacement.
            with open(a.output,'x',encoding='utf-8') as f: json.dump(result,f,indent=2)
        elif a.command=='replay':
            with open(a.fixture,encoding='utf-8') as f: result=json.load(f)['response']
            print(json.dumps(result,indent=2))
        else:
            with open(a.before,encoding='utf-8') as f: old=redact(json.load(f))
            with open(a.after,encoding='utf-8') as f: new=redact(json.load(f))
            result=differences(old,new);print(json.dumps(result,indent=2));return int(bool(result))
        return 0
    except (OSError,ValueError,KeyError) as exc:
        print(str(exc),file=sys.stderr);return 2
if __name__=='__main__': sys.exit(main())
