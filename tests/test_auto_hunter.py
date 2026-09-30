import unittest

from auto_hunter import classify_result


class AutoHunterTests(unittest.TestCase):
    def test_success_requires_pull_request_message(self):
        self.assertEqual(
            classify_result(0, "Pull Request live at: https://github.com/example/repo/pull/1", False)[0],
            "completed",
        )

    def test_failed_zero_exit_without_pr_is_not_completed(self):
        self.assertEqual(
            classify_result(0, "Pipeline finished but no PR was created", False)[0],
            "failed",
        )

    def test_timeout_is_failed(self):
        self.assertEqual(
            classify_result(None, "", True)[0],
            "failed",
        )


if __name__ == "__main__":
    unittest.main()
