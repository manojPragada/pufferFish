import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from app import redact, safe_url, differences, record
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
