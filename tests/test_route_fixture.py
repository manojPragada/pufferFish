import unittest
from app import route_fixture
FIXTURE={'version':1,'response':{'status':200,'headers':{},'body':{'ok':True}}}
class RouteFixtureTests(unittest.TestCase):
 def test_builds_safe_single_route_collection(self):self.assertEqual(route_fixture(FIXTURE,'get','/health')['routes'][0]['method'],'GET')
 def test_digest_requires_post_and_lowercase_sha(self):
  with self.assertRaises(ValueError):route_fixture(FIXTURE,'GET','/','0'*64)
