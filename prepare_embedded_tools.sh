#!/bin/zsh
set -e

cd "$(dirname "$0")"

PYTHON_BIN=".venv/bin/python"
BUNDLE_ROOT="$PWD/.pyinstaller-cache/embedded-tools"
YTDLP_ENTRY="$PWD/packaging/yt_dlp_entry.py"
YTDLP_BUILD_DIR="$PWD/.pyinstaller-cache/yt-dlp-tool-build"

if [ ! -x "$PYTHON_BIN" ]; then
  python3 -m venv .venv
fi

"$PYTHON_BIN" -m pip install --disable-pip-version-check -r requirements.txt

if ! command -v dylibbundler >/dev/null 2>&1; then
  echo "缺少 dylibbundler。请先运行：brew install dylibbundler"
  exit 1
fi

if ! command -v brew >/dev/null 2>&1; then
  echo "缺少 Homebrew。构建内置工具需要 Homebrew 提供本机版本的音视频和 OCR 工具。"
  exit 1
fi

TESSERACT_LANG_PREFIX="$(brew --prefix tesseract-lang 2>/dev/null || true)"
if [ -z "$TESSERACT_LANG_PREFIX" ] || [ ! -f "$TESSERACT_LANG_PREFIX/share/tessdata/chi_sim.traineddata" ]; then
  echo "缺少中文 OCR 数据。请先运行：brew install tesseract-lang"
  exit 1
fi

for tool_name in ffmpeg ffprobe tesseract; do
  if ! command -v "$tool_name" >/dev/null 2>&1; then
    echo "缺少 $tool_name。请先安装后再构建。"
    exit 1
  fi
done

rm -rf "$BUNDLE_ROOT" "$YTDLP_BUILD_DIR"
mkdir -p "$BUNDLE_ROOT/tools" "$BUNDLE_ROOT/tessdata"

echo "正在生成独立 yt-dlp..."
"$PYTHON_BIN" -m PyInstaller \
  --onefile \
  --noconfirm \
  --clean \
  --name yt-dlp \
  --distpath "$BUNDLE_ROOT/tools" \
  --workpath "$YTDLP_BUILD_DIR" \
  --specpath "$PWD/.pyinstaller-cache" \
  --collect-all yt_dlp \
  "$YTDLP_ENTRY"

for tool_name in ffmpeg ffprobe tesseract; do
  cp -L "$(command -v "$tool_name")" "$BUNDLE_ROOT/tools/$tool_name"
  chmod +x "$BUNDLE_ROOT/tools/$tool_name"
done

SEARCH_ARGS=()
while IFS= read -r search_path; do
  SEARCH_ARGS+=(-s "$search_path")
done < <(find -L /opt/homebrew/opt /opt/homebrew/Cellar -type d -name lib 2>/dev/null)

mkdir -p "$BUNDLE_ROOT/tools/lib"
for tool_name in ffmpeg ffprobe tesseract; do
  echo "正在收集 $tool_name 的动态库..."
  dylibbundler \
    -cd \
    -b \
    -of \
    -x "$BUNDLE_ROOT/tools/$tool_name" \
    -d "$BUNDLE_ROOT/tools/lib" \
    -p "@loader_path/../lib" \
    "${SEARCH_ARGS[@]}"
done

TESSERACT_DATA_DIR="$(brew --prefix tesseract)/share/tessdata"
for language_file in eng.traineddata osd.traineddata snum.traineddata; do
  cp -L "$TESSERACT_DATA_DIR/$language_file" "$BUNDLE_ROOT/tessdata/"
done
cp -L "$TESSERACT_LANG_PREFIX/share/tessdata/chi_sim.traineddata" "$BUNDLE_ROOT/tessdata/"
cp -R "$TESSERACT_DATA_DIR/configs" "$BUNDLE_ROOT/tessdata/"
cp -R "$TESSERACT_DATA_DIR/tessconfigs" "$BUNDLE_ROOT/tessdata/"

if command -v xattr >/dev/null 2>&1; then
  xattr -cr "$BUNDLE_ROOT" || true
fi

echo "内置工具准备完成：$BUNDLE_ROOT"
