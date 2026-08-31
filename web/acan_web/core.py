from __future__ import annotations

import ipaddress
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse, urlunparse


SUPPORTED_HOSTS = (
    "youtube.com",
    "youtu.be",
    "bilibili.com",
    "b23.tv",
    "douyin.com",
    "iesdouyin.com",
    "xiaohongshu.com",
    "xhslink.com",
    "weibo.com",
    "weibo.cn",
    "mgtv.com",
    "hunantv.com",
    "mangotv.com",
)
DOWNLOADABLE_SUFFIXES = {
    ".mp4",
    ".mkv",
    ".mov",
    ".webm",
    ".m4a",
    ".mp3",
}
URL_PATTERN = re.compile(r"https?://[^\s<>'\"]+", re.IGNORECASE)
ANSI_PATTERN = re.compile(r"\x1b\[[0-9;]*m")
PERCENT_PATTERN = re.compile(r"(?P<value>\d+(?:\.\d+)?)%")
FILE_MARKER = "ACAN_FILEPATH="
PROGRESS_MARKER = "ACAN_PROGRESS="


class PublicUrlError(ValueError):
    pass


class CapacityError(RuntimeError):
    pass


def _is_supported_host(hostname: str) -> bool:
    hostname = hostname.lower().rstrip(".")
    return any(hostname == host or hostname.endswith(f".{host}") for host in SUPPORTED_HOSTS)


def normalize_public_video_url(raw_value: str) -> str:
    match = URL_PATTERN.search(raw_value or "")
    if not match:
        raise PublicUrlError("请粘贴一个完整的视频网页链接。")

    candidate = match.group(0).rstrip(".,，。!！?？;；)]}）】")
    parsed = urlparse(candidate)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        raise PublicUrlError("目前只支持 http 或 https 视频链接。")

    hostname = parsed.hostname.lower().rstrip(".")
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        address = None
    if address is not None and not address.is_global:
        raise PublicUrlError("不能访问本机或内网地址。")
    if not _is_supported_host(hostname):
        raise PublicUrlError("第一版仅支持 YouTube、B站、抖音、小红书、微博和芒果TV的公开链接。")

    return urlunparse((parsed.scheme.lower(), parsed.netloc, parsed.path or "/", parsed.params, parsed.query, ""))


def detect_platform(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    if host == "youtu.be" or host.endswith(".youtube.com") or host == "youtube.com":
        return "YouTube"
    if host == "b23.tv" or host.endswith(".bilibili.com") or host == "bilibili.com":
        return "B站"
    if "douyin.com" in host or host.endswith(".iesdouyin.com"):
        return "抖音"
    if "xiaohongshu.com" in host or host == "xhslink.com" or host.endswith(".xhslink.com"):
        return "小红书"
    if host == "weibo.cn" or host.endswith(".weibo.cn") or host == "weibo.com" or host.endswith(".weibo.com"):
        return "微博"
    if any(host == name or host.endswith(f".{name}") for name in ("mgtv.com", "hunantv.com", "mangotv.com")):
        return "芒果TV"
    return "未知平台"


def _yt_dlp_prefix() -> list[str]:
    configured = os.environ.get("ACAN_WEB_YTDLP", "").strip()
    if configured:
        return [configured]
    executable = shutil.which("yt-dlp")
    if executable:
        return [executable]
    return [sys.executable, "-m", "yt_dlp"]


def build_download_command(url: str, job_dir: Path) -> list[str]:
    platform = detect_platform(url)
    max_size = os.environ.get("ACAN_WEB_MAX_FILESIZE", "2G")
    output = str(job_dir / "%(title).180B_[%(id)s].%(ext)s")
    command = [
        *_yt_dlp_prefix(),
        "--newline",
        "--no-playlist",
        "--max-downloads",
        "1",
        "--continue",
        "--part",
        "--retries",
        "20",
        "--fragment-retries",
        "20",
        "--retry-sleep",
        "fragment:exp=1:10",
        "--retry-sleep",
        "http:exp=1:10",
        "--socket-timeout",
        "30",
        "--http-chunk-size",
        "2M",
        "--concurrent-fragments",
        "1",
        "--max-filesize",
        max_size,
        "--merge-output-format",
        "mp4",
        "--format",
        "bv*+ba/b",
        "--format-sort",
        "vcodec:h264,acodec:aac,ext:mp4:m4a,res,fps",
        "--no-mtime",
        "--progress-template",
        "download:ACAN_PROGRESS=%(progress._percent_str)s|%(progress._speed_str)s|%(progress._eta_str)s",
        "--print",
        f"after_move:{FILE_MARKER}%(filepath)s",
        "--output",
        output,
    ]
    if platform == "YouTube":
        command.extend(["--js-runtimes", "deno", "--remote-components", "ejs:github"])
    command.append(url)
    return command


def parse_progress_line(line: str) -> tuple[float | None, str, str] | None:
    clean = ANSI_PATTERN.sub("", line).strip()
    if PROGRESS_MARKER not in clean:
        return None
    payload = clean.split(PROGRESS_MARKER, 1)[1]
    parts = [part.strip() for part in payload.split("|", 2)]
    while len(parts) < 3:
        parts.append("")
    percent_match = PERCENT_PATTERN.search(parts[0])
    progress = float(percent_match.group("value")) if percent_match else None
    return progress, parts[1] if parts[1] != "NA" else "", parts[2] if parts[2] != "NA" else ""


def safe_download_file(job_dir: Path, candidate: str | Path) -> Path | None:
    try:
        root = job_dir.resolve()
        path = Path(candidate).resolve()
        path.relative_to(root)
    except (OSError, ValueError):
        return None
    if not path.is_file() or path.suffix.lower() not in DOWNLOADABLE_SUFFIXES or path.name.endswith(".part"):
        return None
    return path


@dataclass
class DownloadJob:
    id: str
    url: str
    platform: str
    status: str = "queued"
    progress: float = 0.0
    speed: str = ""
    eta: str = ""
    message: str = "等待开始"
    error: str = ""
    files: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    _log_lines: list[str] = field(default_factory=list, repr=False)
    _process: subprocess.Popen[str] | None = field(default=None, repr=False)

    def public_dict(self) -> dict:
        return {
            "id": self.id,
            "url": self.url,
            "platform": self.platform,
            "status": self.status,
            "progress": self.progress,
            "speed": self.speed,
            "eta": self.eta,
            "message": self.message,
            "error": self.error,
            "files": list(self.files),
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
        }


class DownloadJobManager:
    def __init__(
        self,
        data_dir: Path,
        max_workers: int = 2,
        max_pending_jobs: int = 8,
        retention_seconds: int = 7200,
        command_builder: Callable[[str, Path], list[str]] = build_download_command,
    ):
        self.data_dir = data_dir.resolve()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.max_pending_jobs = max_pending_jobs
        self.retention_seconds = retention_seconds
        self.command_builder = command_builder
        self._jobs: dict[str, DownloadJob] = {}
        self._lock = threading.RLock()
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="acan-web")

    def create_job(self, raw_url: str) -> DownloadJob:
        url = normalize_public_video_url(raw_url)
        self.cleanup_expired()
        with self._lock:
            active = sum(job.status in {"queued", "running"} for job in self._jobs.values())
            if active >= self.max_pending_jobs:
                raise CapacityError("当前使用人数较多，请稍后再试。")
            job = DownloadJob(id=uuid.uuid4().hex[:24], url=url, platform=detect_platform(url))
            self._jobs[job.id] = job
        (self.data_dir / job.id).mkdir(parents=True, exist_ok=False)
        self._executor.submit(self._run_job, job.id)
        return job

    def get_job(self, job_id: str) -> DownloadJob | None:
        self.cleanup_expired()
        with self._lock:
            return self._jobs.get(job_id)

    def get_file(self, job_id: str, filename: str) -> Path | None:
        job = self.get_job(job_id)
        if not job or filename not in job.files:
            return None
        return safe_download_file(self.data_dir / job_id, self.data_dir / job_id / filename)

    def cancel_job(self, job_id: str) -> bool:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job or job.status not in {"queued", "running"}:
                return False
            job.status = "cancelled"
            job.message = "任务已取消"
            job.updated_at = time.time()
            process = job._process
        if process and process.poll() is None:
            try:
                if os.name == "nt":
                    process.terminate()
                else:
                    os.killpg(process.pid, signal.SIGTERM)
            except (OSError, ProcessLookupError):
                process.terminate()
        return True

    def shutdown(self) -> None:
        with self._lock:
            running_ids = [job.id for job in self._jobs.values() if job.status in {"queued", "running"}]
        for job_id in running_ids:
            self.cancel_job(job_id)
        self._executor.shutdown(wait=True, cancel_futures=True)

    def cleanup_expired(self) -> None:
        cutoff = time.time() - self.retention_seconds
        expired: list[str] = []
        with self._lock:
            for job_id, job in self._jobs.items():
                if job.status not in {"queued", "running"} and job.updated_at < cutoff:
                    expired.append(job_id)
            for job_id in expired:
                self._jobs.pop(job_id, None)
        for job_id in expired:
            shutil.rmtree(self.data_dir / job_id, ignore_errors=True)
        with self._lock:
            known_ids = set(self._jobs)
        for child in self.data_dir.iterdir():
            if child.name in known_ids or not child.is_dir() or not re.fullmatch(r"[0-9a-f]{24}", child.name):
                continue
            try:
                is_expired = child.stat().st_mtime < cutoff
            except OSError:
                continue
            if is_expired:
                shutil.rmtree(child, ignore_errors=True)

    def _run_job(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job or job.status == "cancelled":
                return
            job.status = "running"
            job.message = "正在解析视频"
            job.updated_at = time.time()

        job_dir = self.data_dir / job_id
        command = self.command_builder(job.url, job_dir)
        env = os.environ.copy()
        env.setdefault("PYTHONUNBUFFERED", "1")
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=job_dir,
                env=env,
                start_new_session=True,
            )
            with self._lock:
                job._process = process
            assert process.stdout is not None
            with process.stdout:
                for raw_line in process.stdout:
                    self._handle_output(job, raw_line.rstrip())
                    with self._lock:
                        if job.status == "cancelled":
                            break
            return_code = process.wait()
        except FileNotFoundError:
            self._fail(job, "服务器缺少下载组件，请联系管理员。")
            return
        except Exception as exc:
            self._fail(job, f"任务执行失败：{exc}")
            return
        finally:
            with self._lock:
                job._process = None

        with self._lock:
            if job.status == "cancelled":
                return
        files = self._collect_files(job, job_dir)
        if return_code == 0 and files:
            with self._lock:
                job.files = files
                job.progress = 100.0
                job.status = "completed"
                job.message = "处理完成，可以下载"
                job.updated_at = time.time()
            return

        detail = self._friendly_error(job._log_lines)
        self._fail(job, detail)

    def _handle_output(self, job: DownloadJob, line: str) -> None:
        clean = ANSI_PATTERN.sub("", line).strip()
        if not clean:
            return
        with self._lock:
            job._log_lines.append(clean)
            del job._log_lines[:-120]
            job.updated_at = time.time()
            parsed = parse_progress_line(clean)
            if parsed:
                progress, speed, eta = parsed
                if progress is not None:
                    job.progress = max(0.0, min(progress, 100.0))
                job.speed = speed
                job.eta = eta
                job.message = "正在下载视频"
            elif "[Merger]" in clean or "Merging formats" in clean:
                job.message = "正在合并音频和画面"
            elif "[ExtractAudio]" in clean:
                job.message = "正在处理音频"

    def _collect_files(self, job: DownloadJob, job_dir: Path) -> list[str]:
        candidates: list[Path] = []
        for line in job._log_lines:
            if FILE_MARKER in line:
                candidates.append(Path(line.split(FILE_MARKER, 1)[1].strip()))
        candidates.extend(job_dir.iterdir())
        results: list[str] = []
        seen: set[Path] = set()
        for candidate in candidates:
            safe = safe_download_file(job_dir, candidate)
            if safe and safe not in seen:
                seen.add(safe)
                results.append(safe.name)
        return sorted(results)

    def _fail(self, job: DownloadJob, message: str) -> None:
        with self._lock:
            job.status = "failed"
            job.message = "处理失败"
            job.error = message
            job.updated_at = time.time()

    @staticmethod
    def _friendly_error(lines: list[str]) -> str:
        output = "\n".join(lines).lower()
        if "confirm you’re not a bot" in output or "confirm you're not a bot" in output:
            return "YouTube 要求验证是否为真人。为保护账号安全，网页版不会上传或共用个人 Cookie；请改用 ACAN Studio 桌面版，或先测试其他平台的公开链接。"
        if "login" in output or "cookie" in output or "sign in" in output:
            return "该内容需要登录或账号权限。网页版测试版只支持无需登录即可播放的公开内容。"
        if "drm" in output or "protected" in output:
            return "该内容受到平台保护，网页版不能处理。"
        if "unsupported url" in output:
            return "暂时无法解析这个页面，请确认粘贴的是具体视频播放页。"
        if "private video" in output or "video unavailable" in output:
            return "视频不可公开访问、已下架或仅限部分地区播放。"
        if "max-filesize" in output or "larger than max-filesize" in output:
            return "视频超过网页测试版允许的文件大小。"
        if "timed out" in output or "connection" in output or "ssl" in output:
            return "服务器连接视频平台失败，请稍后重新尝试。"
        errors = [line for line in lines if "ERROR:" in line]
        if errors:
            return errors[-1].replace("ERROR:", "").strip()[:300]
        return "没有成功生成视频文件，请稍后重试或更换一个公开链接。"
