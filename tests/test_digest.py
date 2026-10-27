import hashlib,tempfile,unittest
from pathlib import Path
from app import body_digest
class DigestTests(unittest.TestCase):
 def test_digest_matches_sha256_without_mutating_file(self):
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)/'body.json';raw=b'{"safe":true}';path.write_bytes(raw)
   self.assertEqual(body_digest(path),hashlib.sha256(raw).hexdigest());self.assertEqual(path.read_bytes(),raw)
 def test_digest_rejects_oversized_body(self):
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)/'large';path.write_bytes(b'x'*(1_048_577))
   with self.assertRaisesRegex(ValueError,'1 MiB'):body_digest(path)
