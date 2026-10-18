import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from app import redact, safe_url, differences, record, validate_fixture
class Tests(unittest.TestCase):
    def test_nested_redaction(self):
        self.assertEqual(redact({'items':[{'Token':'abc'}]}),{'items':[{'Token':'[REDACTED]'}]})
    def test_url(self):
        self.assertNotIn('abc',safe_url('https://example.com/a?token=abc&x=1'))
        with self.assertRaises(ValueError):safe_url('https://user:pass@example.com')
    def test_structural_diff(self):
        self.assertEqual(differences({'a':1},{'a':2})[0]['path'],'$["a"]')
        self.assertEqual(differences({'a':1},{'a':1}),[])
        self.assertEqual(differences({}, {'a':None})[0]['kind'],'added')
    def test_local_record(self):
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200);self.send_header('Set-Cookie','secret');self.end_headers();self.wfile.write(b'{"token":"secret","ok":true}')
            def log_message(self,*args):pass
        server=HTTPServer(('127.0.0.1',0),Handler);thread=Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            response=record(f'http://127.0.0.1:{server.server_port}/')['response']
            self.assertEqual(response['body']['token'],'[REDACTED]')
            self.assertEqual(response['headers']['Set-Cookie'],'[REDACTED]')
        finally:server.shutdown();server.server_close();thread.join()


    def test_custom_globs_are_recursive_additive_and_case_insensitive(self):
        value={'client_secret':'x','PASSWORD':'y','nested':[{'Private-Key':'z','public':'keep'}]}
        self.assertEqual(redact(value,['*_secret','private-*']),{'client_secret':'[REDACTED]','PASSWORD':'[REDACTED]','nested':[{'Private-Key':'[REDACTED]','public':'keep'}]})
        self.assertEqual(value['client_secret'],'x')
    def test_custom_url_redaction(self):
        self.assertNotIn('secretvalue',safe_url('https://example.com/?client_secret=secretvalue&x=1',['*_secret']))
    def test_fixture_validation(self):
        good={'version':1,'response':{'status':200,'headers':{},'body':None}}
        self.assertIsNone(validate_fixture(good)['body'])
        for bad in [[],{}, {'version':True,'response':good['response']}, {'version':1,'response':[]}, {'version':1,'response':{'status':True,'headers':{},'body':{}}}, {'version':1,'response':{'status':600,'headers':{},'body':{}}}, {'version':1,'response':{'status':200,'headers':[],'body':{}}}]:
            with self.assertRaises(ValueError):validate_fixture(bad)
    def test_replay_rejects_malformed_fixture_without_traceback(self):
        import subprocess,sys,tempfile,json
        from pathlib import Path
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'bad.json';path.write_text(json.dumps({'version':1,'response':[]}))
            result=subprocess.run([sys.executable,'app.py','replay',str(path)],capture_output=True,text=True)
            self.assertEqual(result.returncode,2);self.assertNotIn('Traceback',result.stderr)
    def test_diff_cli_does_not_expose_custom_secret(self):
        import subprocess,sys,tempfile,json
        from pathlib import Path
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/'a.json';b=Path(d)/'b.json'
            a.write_text(json.dumps({'client_secret':'oldvalue','public':1}));b.write_text(json.dumps({'client_secret':'newvalue','public':2}))
            result=subprocess.run([sys.executable,'app.py','diff',str(a),str(b),'--redact-key','*_secret'],capture_output=True,text=True)
            self.assertEqual(result.returncode,1);self.assertNotIn('oldvalue',result.stdout);self.assertNotIn('newvalue',result.stdout);self.assertIn('public',result.stdout)
