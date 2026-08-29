#!/bin/zsh
set -e

cd "$(dirname "$0")"

APP_NAME="ACAN Studio"
VERSION="${ACAN_VERSION:-1.1.8}"
TARGET_ARCH="${ACAN_TARGET_ARCH:-$(uname -m)}"
APP_BUNDLE="dist/$APP_NAME.app"
DMG_PATH="$PWD/dist/ACAN-Studio-${VERSION}-${TARGET_ARCH}.dmg"
EMBEDDED_TOOLS_DIR="$PWD/.pyinstaller-cache/embedded-tools"

echo "正在准备内置后台工具..."
./prepare_embedded_tools.sh

echo "正在生成可分发的 $APP_NAME.app..."
ACAN_BUNDLED_TOOLS_DIR="$EMBEDDED_TOOLS_DIR" ACAN_SKIP_INSTALL=1 ./build_app.sh

if [ ! -d "$APP_BUNDLE" ]; then
  echo "打包失败：没有找到 $APP_BUNDLE"
  exit 1
fi

STAGING_DIR="$(mktemp -d -t acan-studio-dmg)"
STAGED_APP_BUNDLE="$STAGING_DIR/$APP_NAME.app"
trap 'rm -rf "$STAGING_DIR"' EXIT

# The workspace may be managed by a file provider that immediately re-adds
# FinderInfo attributes. Copy into a temporary local directory without extended
# attributes before signing, otherwise codesign rejects the bundle.
ditto --noextattr --noqtn --norsrc "$APP_BUNDLE" "$STAGED_APP_BUNDLE"

if command -v xattr >/dev/null 2>&1; then
  xattr -cr "$STAGED_APP_BUNDLE" || true
fi

/usr/libexec/PlistBuddy -c "Set :CFBundleShortVersionString $VERSION" "$STAGED_APP_BUNDLE/Contents/Info.plist" >/dev/null 2>&1 || \
  /usr/libexec/PlistBuddy -c "Add :CFBundleShortVersionString string $VERSION" "$STAGED_APP_BUNDLE/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Set :CFBundleVersion $VERSION" "$STAGED_APP_BUNDLE/Contents/Info.plist" >/dev/null 2>&1 || \
  /usr/libexec/PlistBuddy -c "Add :CFBundleVersion string $VERSION" "$STAGED_APP_BUNDLE/Contents/Info.plist"

echo "正在执行本地完整性签名..."
codesign --force --deep --sign - "$STAGED_APP_BUNDLE"
codesign --verify --deep --strict --verbose=2 "$STAGED_APP_BUNDLE"

ln -s /Applications "$STAGING_DIR/Applications"

rm -f "$DMG_PATH"
echo "正在生成 $DMG_PATH..."
hdiutil create \
  -volname "$APP_NAME" \
  -srcfolder "$STAGING_DIR" \
  -ov \
  -format UDZO \
  "$DMG_PATH"

echo ""
echo "DMG 构建完成：$DMG_PATH"
echo "目标架构：$TARGET_ARCH"
echo "测试方式：双击 DMG，将 $APP_NAME.app 拖到 Applications。"
