#!/bin/zsh
set -e

cd "$(dirname "$0")"

TARGET_ARCH="${1:-arm64}"
VERSION="${ACAN_VERSION:-1.1.9}"
BUILD_LOCK_DIR="$PWD/.pyinstaller-cache/macos-compat-build.lock"
PYTHON_VERSION="3.12.6"
PYTHON_PACKAGE="$PWD/.pyinstaller-cache/universal-python/python-${PYTHON_VERSION}-macos11.pkg"
PYTHON_PACKAGE_MD5="9fe25ae8e0dfea2854e6bce62e69a3dd"
PYTHON_RUNTIME="$PWD/.pyinstaller-cache/universal-python/runtime-v1"
PYTHON_FRAMEWORK="$PYTHON_RUNTIME/Python.framework/Versions/3.12"
PYTHON_BASE="$PYTHON_FRAMEWORK/bin/python3.12"
PYTHON_WRAPPER="$PWD/packaging/python_arch_wrapper.sh"
VENV_DIR="$PWD/.venv-macos-$TARGET_ARCH"
REQUIREMENTS_FILE="$PWD/requirements-macos-compat.txt"

mkdir -p "$PWD/.pyinstaller-cache"
if ! mkdir "$BUILD_LOCK_DIR" 2>/dev/null; then
  EXISTING_BUILD_PID="$(cat "$BUILD_LOCK_DIR/pid" 2>/dev/null || true)"
  if [[ "$EXISTING_BUILD_PID" != <-> ]] || ! kill -0 "$EXISTING_BUILD_PID" 2>/dev/null; then
    rm -f "$BUILD_LOCK_DIR/pid"
    rmdir "$BUILD_LOCK_DIR" 2>/dev/null || true
    if ! mkdir "$BUILD_LOCK_DIR" 2>/dev/null; then
      echo "已有一个 macOS 兼容版正在构建，请等待它完成后再试。"
      exit 75
    fi
  else
    echo "已有一个 macOS 兼容版正在构建，请等待它完成后再试。"
    exit 75
  fi
fi
print -r -- "$$" > "$BUILD_LOCK_DIR/pid"
trap 'rm -f "$BUILD_LOCK_DIR/pid"; rmdir "$BUILD_LOCK_DIR" 2>/dev/null || true' EXIT

case "$TARGET_ARCH" in
  arm64|x86_64)
    ;;
  *)
    echo "用法：./build_macos_compat_dmg.sh [arm64|x86_64]"
    exit 64
    ;;
esac

mkdir -p "$PWD/.pyinstaller-cache/universal-python"
if [ ! -f "$PYTHON_PACKAGE" ] || [ "$(md5 -q "$PYTHON_PACKAGE" 2>/dev/null || true)" != "$PYTHON_PACKAGE_MD5" ]; then
  temporary_package="$PYTHON_PACKAGE.download.$RANDOM"
  echo "正在下载 Python $PYTHON_VERSION Universal2..."
  curl --fail --location --silent --show-error \
    -o "$temporary_package" \
    "https://www.python.org/ftp/python/$PYTHON_VERSION/python-$PYTHON_VERSION-macos11.pkg"
  actual_md5="$(md5 -q "$temporary_package")"
  if [ "$actual_md5" != "$PYTHON_PACKAGE_MD5" ]; then
    echo "Python 安装包校验失败。"
    echo "期望：$PYTHON_PACKAGE_MD5"
    echo "实际：$actual_md5"
    exit 1
  fi
  mv "$temporary_package" "$PYTHON_PACKAGE"
fi

if [ ! -x "$PYTHON_BASE" ]; then
  expanded_package="$PWD/.pyinstaller-cache/universal-python/expanded.runtime.$RANDOM.$RANDOM"
  echo "正在解包隔离的 Universal2 Python 运行时..."
  pkgutil --expand-full "$PYTHON_PACKAGE" "$expanded_package"
  mkdir -p "$PYTHON_RUNTIME/Python.framework"
  ditto "$expanded_package/Python_Framework.pkg/Payload" "$PYTHON_RUNTIME/Python.framework"
fi

export DYLD_FRAMEWORK_PATH="$PYTHON_RUNTIME"
export DYLD_LIBRARY_PATH="$PYTHON_FRAMEWORK/lib"
export SSL_CERT_FILE="/etc/ssl/cert.pem"
export ACAN_RUNTIME_FRAMEWORK_PATH="$PYTHON_RUNTIME"
export ACAN_RUNTIME_LIBRARY_PATH="$PYTHON_FRAMEWORK/lib"
export ACAN_RUNTIME_TCL_LIBRARY="$PYTHON_FRAMEWORK/lib/tcl8.6"
export ACAN_RUNTIME_TK_LIBRARY="$PYTHON_FRAMEWORK/lib/tk8.6"
export ACAN_RUNTIME_SSL_CERT_FILE="/etc/ssl/cert.pem"
export ACAN_PYTHON_LIBRARY_DIR="$PYTHON_FRAMEWORK/lib"
export TCL_LIBRARY="$ACAN_RUNTIME_TCL_LIBRARY"
export TK_LIBRARY="$ACAN_RUNTIME_TK_LIBRARY"
export ACAN_PYTHON_ARCH="$TARGET_ARCH"
export ACAN_REAL_PYTHON="$PYTHON_BASE"
chmod +x "$PYTHON_WRAPPER"

if ! "$PYTHON_WRAPPER" -c 'import platform; print(platform.machine())' >/dev/null 2>&1; then
  if [ "$TARGET_ARCH" = "x86_64" ]; then
    echo "Intel 构建需要 Rosetta 2。请先运行：softwareupdate --install-rosetta --agree-to-license"
  else
    echo "无法启动 $TARGET_ARCH Python 构建环境。"
  fi
  exit 1
fi

if [ ! -x "$VENV_DIR/bin/python3.12" ]; then
  echo "正在创建 $TARGET_ARCH Python 依赖环境..."
  "$PYTHON_WRAPPER" -m venv "$VENV_DIR"
fi

export ACAN_REAL_PYTHON="$VENV_DIR/bin/python3.12"
"$PYTHON_WRAPPER" -m ensurepip --upgrade >/dev/null
"$PYTHON_WRAPPER" -m pip install --disable-pip-version-check -r "$REQUIREMENTS_FILE"

export ACAN_PYTHON_BIN="$PYTHON_WRAPPER"
export ACAN_REQUIREMENTS_FILE="$REQUIREMENTS_FILE"
export ACAN_TARGET_ARCH="$TARGET_ARCH"
export ACAN_MACOSX_DEPLOYMENT_TARGET="12.0"
export ACAN_VERSION="$VERSION"
export ACAN_PYINSTALLER_CONFIG_DIR="$PWD/.pyinstaller-cache/$TARGET_ARCH"

echo "正在构建 ACAN Studio $VERSION（$TARGET_ARCH，macOS 12+）..."
./build_dmg.sh
