"""Download command construction shared by ACAN Studio interfaces."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse, urlunparse


MGTV_SVIP_FILTERS = (
    "mgtv_purview = 200",
    "!mgtv_access_hint",
    "mgtv_access_hint !*= SVIP",
)


def clean_url_parameters(url: str) -> str:
    """Remove query and fragment parameters from a URL."""

    parsed = urlparse(url or "")
    if not parsed.scheme or not parsed.netloc:
        return url
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))


def build_youtube_network_args(platform, chunk_size: str, retries: int) -> list[str]:
    """Build resilient YouTube transport options."""

    if platform.get("name") != "YouTube":
        return []
    return [
        "--force-ipv4",
        "--extractor-retries", "10",
        "--retries", str(retries),
        "--fragment-retries", str(retries),
        "--retry-sleep", "http:linear=1:5:1",
        "--retry-sleep", "fragment:linear=1:5:1",
        "--retry-sleep", "extractor:linear=1:5:1",
        "--http-chunk-size", chunk_size,
        "--socket-timeout", "30",
        "--continue",
    ]


def build_yt_dlp_download_attempts(
    platform,
    url: str,
    destination_dir: str | Path,
    engine,
    *,
    cookie_args=(),
    deno_path: str | None = None,
    curl_path: str | None = None,
    proxy_url: str = "",
) -> list[tuple[str, list[str]]]:
    """Build ordered yt-dlp attempts without executing external commands.

    ``cookie_args`` is supplied by the caller only after the user enables a
    cookie source. This keeps the default path privacy-preserving.
    """

    platform_name = platform.get("name", "Other")
    engine_name = engine.get("name", "Engine A：yt-dlp")
    destination_dir = Path(destination_dir)
    output_template = str(
        destination_dir
        / "%(uploader|未知作者).100B"
        / "%(upload_date|未知日期)s_%(title).200B_[%(id|未知ID)s].%(ext)s"
    )
    javascript_args = []
    if platform_name == "YouTube" and deno_path:
        javascript_args = ["--js-runtimes", f"deno:{deno_path}"]

    base_command = [
        "yt-dlp",
        *javascript_args,
        "--merge-output-format", "mp4",
        "--no-mtime",
        "--no-simulate",
        "--print", "before_dl:ACAN_EXPECTED_DURATION=%(duration|0)s",
        "--print", "after_move:ACAN_DOWNLOADED_FILE=%(filepath)s",
        "-o", output_template,
        url,
    ]
    cookies = list(cookie_args or ())

    if platform_name == "YouTube":
        attempts = [
            (
                f"{engine_name}：YouTube 分块断点续传",
                ["yt-dlp", *cookies, *build_youtube_network_args(platform, "2M", 20), *base_command[1:]],
            ),
            (
                f"{engine_name}：YouTube 小分块备用续传",
                ["yt-dlp", *cookies, *build_youtube_network_args(platform, "512K", 40), *base_command[1:]],
            ),
        ]

        if curl_path:
            proxy_args = ["--proxy", proxy_url] if proxy_url else []
            attempts.append(
                (
                    f"{engine_name}：YouTube curl 备用传输",
                    [
                        "yt-dlp",
                        *cookies,
                        *proxy_args,
                        "--force-ipv4",
                        "--extractor-retries", "10",
                        "--retries", "30",
                        "--retry-sleep", "extractor:linear=1:5:1",
                        "--socket-timeout", "30",
                        "--continue",
                        "--downloader", f"http:{curl_path}",
                        "--downloader-args",
                        "curl:--retry-all-errors --retry-delay 1 --connect-timeout 30 --speed-time 30 --speed-limit 1024 --http1.1 --fail",
                        *base_command[1:],
                    ],
                )
            )
        return attempts

    if platform_name == "抖音":
        attempts = [(f"{engine_name}：直接下载", base_command)]
        if cookies:
            attempts.append((f"{engine_name}：使用设置中的 Cookie 重试", ["yt-dlp", *cookies, *base_command[1:]]))
        return attempts

    if platform_name == "微博":
        cleaned_base_command = [*base_command[:-1], clean_url_parameters(url)]
        attempts = [
            (f"{engine_name}：微博第一次尝试：原始链接", base_command),
            (f"{engine_name}：微博第二次尝试：清理 URL 参数", cleaned_base_command),
        ]
        if cookies:
            attempts.extend(
                [
                    (f"{engine_name}：微博第三次尝试：使用设置中的 Cookie", ["yt-dlp", *cookies, *base_command[1:]]),
                    (f"{engine_name}：微博第四次尝试：清理 URL 参数 + Cookie", ["yt-dlp", *cookies, *cleaned_base_command[1:]]),
                ]
            )
        return attempts

    if platform_name == "芒果TV":
        browser_headers = [
            "--referer", "https://www.mgtv.com/",
            "--user-agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
        ]
        access_filter = [item for expression in MGTV_SVIP_FILTERS for item in ("--match-filter", expression)]
        attempts = []
        if cookies:
            attempts.append(
                (
                    f"{engine_name}：芒果TV第一次尝试：使用设置中的登录态",
                    ["yt-dlp", *cookies, *browser_headers, *access_filter, *base_command[1:]],
                )
            )
        attempts.append(
            (
                f"{engine_name}：芒果TV标准下载",
                ["yt-dlp", *browser_headers, *access_filter, *base_command[1:]],
            )
        )
        return attempts

    return [(engine_name, ["yt-dlp", *cookies, *base_command[1:]] if cookies else base_command)]
