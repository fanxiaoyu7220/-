import unittest
from pathlib import Path
from unittest.mock import patch

from main import ACANCreatorApp


class YouTubeResilienceTests(unittest.TestCase):
    def setUp(self):
        self.app = object.__new__(ACANCreatorApp)
        self.app._cookie_args = lambda: ["--cookies-from-browser", "chrome"]
        self.app._find_tool = lambda name: {
            "curl": "/usr/bin/curl",
            "deno": "/bundle/deno",
        }.get(name)
        self.platform = {"name": "YouTube"}
        self.engine = {"name": "Engine A：yt-dlp"}

    @patch("main.getproxies", return_value={"https": "http://127.0.0.1:7890"})
    def test_download_attempts_switch_transport_and_keep_resume(self, _getproxies):
        attempts = self.app._build_yt_dlp_download_attempts(
            self.platform,
            "https://youtu.be/HZguePfneD8",
            Path("/tmp/ACAN Test"),
            self.engine,
        )

        self.assertEqual(len(attempts), 3)
        first_command = attempts[0][1]
        second_command = attempts[1][1]
        curl_command = attempts[2][1]

        self.assertIn("2M", first_command)
        self.assertIn("512K", second_command)
        self.assertIn("--continue", first_command)
        self.assertIn("--continue", second_command)
        self.assertNotIn("infinite", first_command)
        self.assertNotIn("infinite", second_command)
        self.assertIn("http:/usr/bin/curl", curl_command)
        self.assertEqual(curl_command[curl_command.index("--proxy") + 1], "http://127.0.0.1:7890")
        self.assertIn("--retry-all-errors", curl_command[curl_command.index("--downloader-args") + 1])

    def test_ssl_error_has_specific_chinese_suggestion(self):
        suggestion = self.app._platform_stage_suggestion(
            "YouTube",
            "下载",
            "[SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol",
        )

        self.assertIn("分块断点续传", suggestion)
        self.assertIn(".part", suggestion)


if __name__ == "__main__":
    unittest.main()
