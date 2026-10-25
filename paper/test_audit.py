"""Evidence checks must reject missing or modified frozen dependencies."""
import tempfile
import unittest
from pathlib import Path

from audit import sha, verify_dependency_hashes


class DependencyHashTests(unittest.TestCase):
    def test_repository_and_record_relative_dependencies(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            study = root / 'study'
            study.mkdir()
            dependency = study / 'input.json'
            dependency.write_text('{}')
            record = study / 'verification.json'
            digest = sha(dependency)
            verify_dependency_hashes(
                {'source_sha256': {'study/input.json': digest}}, record, root)
            verify_dependency_hashes(
                {'source_sha256': {'input.json': digest}}, record, root)
            dependency.write_text('{"changed": true}')
            with self.assertRaises(AssertionError):
                verify_dependency_hashes(
                    {'source_sha256': {'input.json': digest}}, record, root)
            dependency.unlink()
            with self.assertRaises(AssertionError):
                verify_dependency_hashes(
                    {'source_sha256': {'input.json': digest}}, record, root)


if __name__ == '__main__':
    unittest.main()
