import json,tempfile,unittest
from pathlib import Path
from threading import Thread
from urllib.request import urlopen
from urllib.error import HTTPError
from dashboard import create_dashboard,fixture_files,load_fixture

class DashboardTests(unittest.TestCase):
    def write(self,root,name,body): Path(root,name).write_text(json.dumps({'version':1,'response':{'status':200,'headers':{},'body':body}}))
    def test_lists_json_and_redacts_loaded_fixture(self):
        with tempfile.TemporaryDirectory() as root:
            self.write(root,'one.json',{'token':'never-show','ok':True});Path(root,'note.txt').write_text('skip')
            self.assertEqual(fixture_files(root),['one.json']);self.assertEqual(load_fixture(root,'one.json')['response']['body']['token'],'[REDACTED]')
            for name in ['../one.json','note.txt']:
                with self.assertRaises(ValueError):load_fixture(root,name)
    def test_loopback_api_lists_and_diffs(self):
        with tempfile.TemporaryDirectory() as root:
            self.write(root,'before.json',{'value':1});self.write(root,'after.json',{'value':2})
            server=create_dashboard(root,0);thread=Thread(target=server.serve_forever,daemon=True);thread.start();base=f'http://127.0.0.1:{server.server_port}'
            try:
                with urlopen(base+'/api/fixtures') as response:self.assertEqual(json.load(response)['fixtures'],['after.json','before.json'])
                with urlopen(base+'/api/diff?before=before.json&after=after.json') as response:self.assertEqual(json.load(response)['changes'][0]['path'],'$["response"]["body"]["value"]')
                with self.assertRaises(HTTPError):urlopen(base+'/api/fixture?name=../before.json')
            finally:server.shutdown();server.server_close();thread.join()
