import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from app import differences


class ArrayDiffTests(unittest.TestCase):
    def test_nested_array_field_paths(self):
        old = {'items': [{'value': 1}, [True]]}
        new = {'items': [{'value': 2}, [1]]}
        self.assertEqual([item['path'] for item in differences(old, new)],
                         ['$["items"][0]["value"]', '$["items"][1][0]'])
        self.assertEqual(old['items'][0]['value'], 1)

    def test_added_and_removed_null_are_not_missing(self):
        self.assertEqual(differences([], [None]),
                         [{'path': '$[0]', 'kind': 'added', 'after': None}])
        self.assertEqual(differences([None], []),
                         [{'path': '$[0]', 'kind': 'removed', 'before': None}])

    def test_equal_and_type_changed_arrays(self):
        self.assertEqual(differences([{'a': []}], [{'a': []}]), [])
        self.assertEqual(differences([], {})[0]['path'], '$')

    def test_array_insertions_are_explicitly_positional(self):
        self.assertEqual([x['path'] for x in differences([1, 2], [0, 1, 2])],
                         ['$[0]', '$[1]', '$[2]'])

    def test_cli_redacts_nested_array_secrets_before_comparison(self):
        with tempfile.TemporaryDirectory() as directory:
            old, new = (Path(directory) / name for name in ('old.json', 'new.json'))
            old.write_text(json.dumps([{'token': 'old-secret', 'value': 1}]))
            new.write_text(json.dumps([{'token': 'new-secret', 'value': 2}]))
            result = subprocess.run([sys.executable, 'app.py', 'diff', str(old), str(new)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(json.loads(result.stdout),
                             [{'path': '$[0]["value"]', 'before': 1, 'after': 2}])
