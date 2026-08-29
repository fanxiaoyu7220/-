# Third-party runtime notices

The optional embedded-runtime DMG includes third-party command-line tools. They
remain under their own licenses and are not relicensed by ACAN Studio.

- yt-dlp: Unlicense. Project: <https://github.com/yt-dlp/yt-dlp>
- yt-dlp-ejs: Unlicense with bundled components under MIT and ISC. Project:
  <https://github.com/yt-dlp/ejs>
- Deno: MIT. Project: <https://github.com/denoland/deno>. The exact license is
  included in the app's `licenses` directory.
- FFmpeg/FFprobe: GPL-3.0-or-later static builds distributed by ffmpeg-static.
  Project and source: <https://ffmpeg.org/>. Binary build project:
  <https://github.com/eugeneware/ffmpeg-static>. The exact binary README and
  license are included in the app's `licenses` directory.
- faster-whisper: MIT. Project: <https://github.com/SYSTRAN/faster-whisper>
- CTranslate2: MIT. Project: <https://github.com/OpenNMT/CTranslate2>
- faster-whisper base model: MIT. Project: <https://huggingface.co/Systran/faster-whisper-base>

ACAN Studio uses Apple's built-in Vision framework for OCR on macOS; no separate
OCR executable or Homebrew installation is needed in the compatibility build.
