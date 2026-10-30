import unittest
from app import append_route, route_fixture
from replay_server import compile_routes
FIXTURE={'version':1,'response':{'status':200,'headers':{},'body':{'ok':True}}}
class RouteFixtureTests(unittest.TestCase):
 def test_builds_safe_single_route_collection(self):
  result=route_fixture(FIXTURE,'get','/health');self.assertEqual(result['routes'][0]['request']['method'],'GET');self.assertEqual(compile_routes(result)[0][:2],('GET','/health'))
 def test_digest_requires_post_and_lowercase_sha(self):
  with self.assertRaises(ValueError):route_fixture(FIXTURE,'GET','/','0'*64)
 def test_digest_is_written_where_replay_compiler_reads_it(self):
  result=route_fixture(FIXTURE,'POST','/submit','0'*64);self.assertEqual(compile_routes(result)[0][3],'0'*64)
 def test_appends_without_mutating_source_collection(self):
  original=route_fixture(FIXTURE,'GET','/first');result=append_route(original,FIXTURE,'POST','/second','0'*64)
  self.assertEqual(len(original['routes']),1);self.assertEqual(len(compile_routes(result)),2)
 def test_rejects_duplicate_route_matcher(self):
  original=route_fixture(FIXTURE,'GET','/same')
  with self.assertRaisesRegex(ValueError,'Duplicate route'):append_route(original,FIXTURE,'GET','/same')
