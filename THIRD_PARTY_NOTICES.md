# Third-party runtime notices

The optional embedded-runtime DMG includes third-party command-line tools. They
remain under their own licenses and are not relicensed by ACAN Studio.

- yt-dlp: Unlicense. Project: <https://github.com/yt-dlp/yt-dlp>
- FFmpeg: GPL-3.0-or-later for the Homebrew build used by the packaging script.
  Project and source: <https://ffmpeg.org/>
- Tesseract OCR: Apache-2.0. Project: <https://github.com/tesseract-ocr/tesseract>
- Tesseract language data: Apache-2.0. Project: <https://github.com/tesseract-ocr/tessdata_fast>

The exact versions bundled into a build are recorded by the build machine's
Homebrew and Python package versions. Rebuild the DMG when updating these tools.
