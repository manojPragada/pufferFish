import json
import unittest
from threading import Thread
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from unittest.mock import patch
from replay_server import create_server,compile_routes

class ServerTests(unittest.TestCase):
    def fixture(self):
        return {'version':1,'response':{'status':200,'headers':{'Set-Cookie':'do-not-replay'},'body':{'token':'secret','private_key':'custom','ok':True}}}
    def request(self, server, method='GET',path='/any/path'):
        thread=Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            request=Request(f'http://127.0.0.1:{server.server_port}{path}',method=method)
            try: response=urlopen(request,timeout=2)
            except HTTPError as error:response=error
            with response:return response.status,dict(response.headers),response.read()
        finally:server.shutdown();server.server_close();thread.join()
    def test_redacted_body_and_safe_headers(self):
        code,headers,raw=self.request(create_server(self.fixture(),port=0,patterns=['private_*']))
        self.assertEqual(code,200);self.assertNotIn('Set-Cookie',headers)
        self.assertEqual(json.loads(raw),{'token':'[REDACTED]','private_key':'[REDACTED]','ok':True})
    def test_status_fault_and_requested_latency(self):
        with patch('replay_server.time.sleep') as sleep:
            code,_,_=self.request(create_server(self.fixture(),port=0,status=503,delay_ms=250))
            self.assertEqual(code,503);sleep.assert_called_once_with(.25)
    def test_head_and_no_content_are_bodyless(self):
        _,headers,raw=self.request(create_server(self.fixture(),port=0),method='HEAD')
        self.assertEqual(raw,b'');self.assertGreater(int(headers['Content-Length']),0)
        code,headers,raw=self.request(create_server(self.fixture(),port=0,status=204))
        self.assertEqual((code,raw),(204,b''));self.assertEqual(headers['Content-Length'],'0')
    def test_invalid_options_fail_before_binding(self):
        for options in [{'status':199},{'delay_ms':-1},{'delay_ms':30001},{'port':-1},{'status':True}]:
            with self.assertRaises(ValueError):create_server(self.fixture(),**options)
    def test_collection_matches_exact_method_and_path(self):
        first=self.fixture();first['request']={'method':'GET','path':'/users'};first['response']['body']={'route':'users'}
        second=self.fixture();second['request']={'method':'GET','path':'/health'};second['response']['body']={'route':'health'}
        collection={'version':1,'routes':[first,second]}
        code,_,raw=self.request(create_server(collection,port=0),path='/health?ignored=yes');self.assertEqual((code,json.loads(raw)),(200,{'route':'health'}))
        code,_,raw=self.request(create_server(collection,port=0),path='/missing');self.assertEqual(code,404);self.assertEqual(json.loads(raw)['path'],'/missing')
    def test_collection_rejects_duplicates_and_unsafe_routes(self):
        item=self.fixture();item['request']={'method':'GET','path':'/same'}
        with self.assertRaisesRegex(ValueError,'Duplicate'):compile_routes({'version':1,'routes':[item,item]})
        item['request']['path']='relative'
        with self.assertRaises(ValueError):compile_routes({'version':1,'routes':[item]})

