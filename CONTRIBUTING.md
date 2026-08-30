# Contributing to ACAN Studio

Thank you for helping make ACAN Studio a dependable, open-source media
workspace for creators.

## Development setup

ACAN Studio currently targets macOS 12 or newer. The source application uses
Python 3.11 or newer, CustomTkinter, FFmpeg, yt-dlp, and optional OCR and
Whisper components.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

The dependency-light core tests do not need the desktop or media dependencies.
Run them from the repository root:

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q main.py ui_v2.py acan_studio tests
```

## Code organization

- `main.py` contains the existing desktop application and task orchestration.
- `ui_v2.py` contains the CustomTkinter layout.
- `acan_studio/core/` contains GUI-independent media, downloader, and error
  handling helpers. New pure logic should go here when practical.
- `tests/` contains fast tests that can run without downloading real media.
- `packaging/` and the shell scripts contain macOS packaging support.

Please preserve working behavior in `main.py` when extracting code. Avoid
large rewrites unless a change is necessary for correctness, security, or
maintainability.

## Pull requests

Before opening a pull request:

1. Explain the user problem and the smallest useful change.
2. Add or update tests for pure logic and edge cases.
3. Run the commands above.
4. Do not include media files, browser cookies, `Cookies.txt`, logs, local
   settings, API keys, or packaged application binaries.
5. Update `CHANGELOG.md` and `ROADMAP.md` when the change affects users or the
   planned release sequence.

Use a focused pull request. A change that touches platform download behavior
should include the exact platform, link type, and sanitized error output used
for verification.

## Commit style

Use a short imperative subject, for example:

```text
Add SRT parsing edge-case coverage
Fix opt-in cookie handling for Douyin downloads
```

## Responsible use

ACAN Studio does not bypass DRM, paywalls, or platform access controls. Only
download or process media that you are authorized to access and use. Report
security issues privately as described in [SECURITY.md](SECURITY.md).
