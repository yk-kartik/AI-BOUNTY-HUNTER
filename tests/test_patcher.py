import tempfile
import unittest
from pathlib import Path

from utils.patcher import apply_patch


class PatcherTests(unittest.TestCase):
    def test_exact_search_replace(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.py"
            path.write_text("def hello():\n    return 'old'\n", encoding="utf-8")
            patch = """FILE: sample.py
<<<< SEARCH
def hello():
    return 'old'
====
def hello():
    return 'new'
>>>> REPLACE"""
            self.assertTrue(apply_patch(str(path), patch))
            self.assertEqual(path.read_text(encoding="utf-8"), "def hello():\n    return 'new'\n")

    def test_duplicate_match_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.py"
            path.write_text("x = 1\nx = 1\n", encoding="utf-8")
            patch = """FILE: sample.py
<<<< SEARCH
x = 1
====
x = 2
>>>> REPLACE"""
            self.assertFalse(apply_patch(str(path), patch))

    def test_multiple_file_headers_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.py"
            path.write_text("x = 1\n", encoding="utf-8")
            patch = """FILE: sample.py
FILE: other.py
<<<< SEARCH
x = 1
====
x = 2
>>>> REPLACE"""
            self.assertFalse(apply_patch(str(path), patch))

    def test_placeholder_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.py"
            path.write_text("x = 1\n", encoding="utf-8")
            patch = """FILE: sample.py
<<<< SEARCH
x = 1
====
...
>>>> REPLACE"""
            self.assertFalse(apply_patch(str(path), patch))


if __name__ == "__main__":
    unittest.main()
