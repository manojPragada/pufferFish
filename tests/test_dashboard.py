import json,tempfile,unittest
from pathlib import Path
from threading import Thread
from urllib.request import urlopen
from urllib.error import HTTPError
from dashboard import check_fixture,create_dashboard,diff_summary,fixture_files,load_fixture

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
                with urlopen(base+'/api/diff?before=before.json&after=after.json') as response:
                    result=json.load(response);self.assertEqual(result['changes'][0]['path'],'$["response"]["body"]["value"]');self.assertEqual(result['summary'],{'total':1,'added':0,'removed':0,'changed':1})
                with urlopen(base+'/api/check?name=before.json') as response:self.assertEqual(json.load(response),{'kind':'legacy fixture','routes':1,'methods':['GET','HEAD']})
                with self.assertRaises(HTTPError):urlopen(base+'/api/fixture?name=../before.json')
            finally:server.shutdown();server.server_close();thread.join()
    def test_content_free_dashboard_check(self):
        with tempfile.TemporaryDirectory() as root:
            self.write(root,'private.json',{'token':'never-show','path':'/private'})
            summary=check_fixture(root,'private.json')
            self.assertEqual(summary,{'kind':'legacy fixture','routes':1,'methods':['GET','HEAD']})
            self.assertNotIn('never-show',json.dumps(summary));self.assertNotIn('/private',json.dumps(summary))
    def test_diff_summary_counts_kinds_without_values_or_paths(self):
        changes=[{'path':'$["private"]','before':'never-show','after':'changed'},{'path':'$["new"]','kind':'added','after':'secret'},{'path':'$["old"]','kind':'removed','before':'secret'}]
        summary=diff_summary(changes)
        self.assertEqual(summary,{'total':3,'added':1,'removed':1,'changed':1})
        serialized=json.dumps(summary)
        self.assertNotIn('never-show',serialized);self.assertNotIn('private',serialized)
