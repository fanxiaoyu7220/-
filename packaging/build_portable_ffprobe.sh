#!/bin/zsh
set -e

cd "$(dirname "$0")/.."

TARGET_ARCH="${1:-$(uname -m)}"
DEPLOYMENT_TARGET="${2:-12.0}"
FFMPEG_VERSION="6.1.6"
SOURCE_SHA256="d4fcb164028dd3beee5d92c0ac72e46aac6973c75ea12dc14de07bf8f407370a"
SOURCE_CACHE="$PWD/.pyinstaller-cache/ffprobe-source"
SOURCE_ARCHIVE="$SOURCE_CACHE/ffmpeg-$FFMPEG_VERSION.tar.xz"
OUTPUT_DIR="$SOURCE_CACHE/output-$TARGET_ARCH"
OUTPUT_PATH="$OUTPUT_DIR/ffprobe"

case "$TARGET_ARCH" in
  arm64|x86_64)
    ;;
  *)
    echo "不支持的 ffprobe 架构：$TARGET_ARCH" >&2
    exit 64
    ;;
esac

ARCH_CONFIGURE_ARGS=()
if [ "$TARGET_ARCH" = "x86_64" ]; then
  ARCH_CONFIGURE_ARGS+=(--disable-x86asm)
fi

if [ -x "$OUTPUT_PATH" ] && file "$OUTPUT_PATH" | grep -q "$TARGET_ARCH"; then
  print -r -- "$OUTPUT_PATH"
  exit 0
fi

mkdir -p "$SOURCE_CACHE" "$OUTPUT_DIR"
if [ ! -f "$SOURCE_ARCHIVE" ] || [ "$(shasum -a 256 "$SOURCE_ARCHIVE" 2>/dev/null | awk '{print $1}')" != "$SOURCE_SHA256" ]; then
  temporary_archive="$SOURCE_ARCHIVE.download.$RANDOM"
  curl --http1.1 --retry 5 --retry-all-errors --fail --location --silent --show-error \
    -o "$temporary_archive" \
    "https://ffmpeg.org/releases/ffmpeg-$FFMPEG_VERSION.tar.xz"
  actual_sha256="$(shasum -a 256 "$temporary_archive" | awk '{print $1}')"
  if [ "$actual_sha256" != "$SOURCE_SHA256" ]; then
    echo "FFmpeg 源码校验失败：$actual_sha256" >&2
    exit 1
  fi
  mv "$temporary_archive" "$SOURCE_ARCHIVE"
fi

temporary_root="$(mktemp -d -t "acan-ffprobe-$TARGET_ARCH")"
source_dir="$temporary_root/source"
build_dir="$temporary_root/build"
mkdir -p "$source_dir" "$build_dir"
tar -xf "$SOURCE_ARCHIVE" -C "$source_dir" --strip-components=1

(
  cd "$build_dir"
  MACOSX_DEPLOYMENT_TARGET="$DEPLOYMENT_TARGET" "$source_dir/configure" \
    --cc=/usr/bin/clang \
    --arch="$TARGET_ARCH" \
    --target-os=darwin \
    "${ARCH_CONFIGURE_ARGS[@]}" \
    --extra-cflags="-arch $TARGET_ARCH -mmacosx-version-min=$DEPLOYMENT_TARGET" \
    --extra-ldflags="-arch $TARGET_ARCH -mmacosx-version-min=$DEPLOYMENT_TARGET" \
    --disable-shared \
    --enable-static \
    --disable-programs \
    --enable-ffprobe \
    --disable-doc \
    --disable-debug \
    --disable-network \
    --disable-autodetect \
    --disable-encoders \
    --disable-muxers \
    --disable-filters \
    --disable-devices >/dev/null
  make -s -j"$(sysctl -n hw.ncpu)" ffprobe
  cp ffprobe "$OUTPUT_PATH"
)

chmod +x "$OUTPUT_PATH"
rm -rf "$temporary_root"
print -r -- "$OUTPUT_PATH"
