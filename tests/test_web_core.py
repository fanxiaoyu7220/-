import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock


from acan_web.core import (
    PublicUrlError,
    DownloadJobManager,
    build_download_command,
    detect_platform,
    normalize_public_video_url,
    parse_progress_line,
    safe_download_file,
)


class WebCoreTests(unittest.TestCase):
    def test_extracts_supported_url_from_share_text(self):
        value = normalize_public_video_url("分享视频\nhttps://youtu.be/abc123?t=4\n快来看看")
        self.assertEqual(value, "https://youtu.be/abc123?t=4")
        self.assertEqual(detect_platform(value), "YouTube")

    def test_rejects_local_and_unsupported_urls(self):
        with self.assertRaises(PublicUrlError):
            normalize_public_video_url("http://127.0.0.1/private")
        with self.assertRaises(PublicUrlError):
            normalize_public_video_url("https://example.com/video")

    @mock.patch("acan_web.core._yt_dlp_prefix", return_value=["yt-dlp"])
    def test_command_is_single_public_job_without_cookie_flags(self, _prefix):
        command = build_download_command("https://www.youtube.com/watch?v=abc", Path("/tmp/job"))
        self.assertIn("--no-playlist", command)
        self.assertIn("--max-filesize", command)
        self.assertIn("--continue", command)
        self.assertIn("--js-runtimes", command)
        self.assertNotIn("--cookies", command)
        self.assertNotIn("--cookies-from-browser", command)

    def test_progress_and_safe_result_parsing(self):
        parsed = parse_progress_line("ACAN_PROGRESS= 42.5%|3.2MiB/s|00:21")
        self.assertEqual(parsed, (42.5, "3.2MiB/s", "00:21"))
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            video = root / "video.mp4"
            video.write_bytes(b"video")
            self.assertEqual(safe_download_file(root, video), video.resolve())
            self.assertIsNone(safe_download_file(root, root.parent / "other.mp4"))

    def test_job_runs_and_exposes_completed_download(self):
        def fake_command(_url, job_dir):
            script = (
                "from pathlib import Path; "
                f"p=Path({str(job_dir / 'result.mp4')!r}); "
                "print('ACAN_PROGRESS=55.0%|1MiB/s|00:01', flush=True); "
                "p.write_bytes(b'video'); "
                "print('ACAN_FILEPATH=' + str(p), flush=True)"
            )
            import sys
            return [sys.executable, "-c", script]

        with tempfile.TemporaryDirectory() as temp:
            manager = DownloadJobManager(Path(temp), command_builder=fake_command)
            try:
                job = manager.create_job("https://youtu.be/abc123")
                deadline = time.time() + 5
                while job.status in {"queued", "running"} and time.time() < deadline:
                    time.sleep(0.02)
                self.assertEqual(job.status, "completed")
                self.assertEqual(job.public_dict()["progress"], 100.0)
                self.assertEqual(job.files, ["result.mp4"])
                self.assertEqual(manager.get_file(job.id, "result.mp4").read_bytes(), b"video")
            finally:
                manager.shutdown()

    def test_expired_orphan_directory_is_removed_safely(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            orphan = root / ("a" * 24)
            unrelated = root / "keep-me"
            orphan.mkdir()
            unrelated.mkdir()
            old = time.time() - 30
            import os
            os.utime(orphan, (old, old))
            manager = DownloadJobManager(root, retention_seconds=1)
            try:
                manager.cleanup_expired()
                self.assertFalse(orphan.exists())
                self.assertTrue(unrelated.exists())
            finally:
                manager.shutdown()

    def test_youtube_bot_check_has_safe_guidance(self):
        message = DownloadJobManager._friendly_error(
            ["ERROR: Sign in to confirm you're not a bot. Use --cookies-from-browser"]
        )
        self.assertIn("真人", message)
        self.assertIn("不会上传或共用个人 Cookie", message)


if __name__ == "__main__":
    unittest.main()
