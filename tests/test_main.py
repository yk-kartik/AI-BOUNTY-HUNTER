import tempfile
import unittest
from pathlib import Path

from main import find_target_file


class TargetFileTests(unittest.TestCase):
    def test_exact_relative_path_is_used(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "src" / "worker.py"
            target.parent.mkdir()
            target.write_text("print('ok')", encoding="utf-8")
            self.assertEqual(
                Path(find_target_file(str(root), "src/worker.py")).resolve(),
                target.resolve(),
            )

    def test_missing_path_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(find_target_file(tmp, "missing.py"))

    def test_parent_path_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(find_target_file(tmp, "../outside.py"))


if __name__ == "__main__":
    unittest.main()
