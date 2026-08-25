#!/bin/zsh
set -e

cd "$(dirname "$0")"

APP_NAME="ACAN Studio"
VERSION="1.1.0"
APP_BUNDLE="dist/$APP_NAME.app"
DMG_PATH="$PWD/dist/ACAN-Studio-${VERSION}.dmg"
EMBEDDED_TOOLS_DIR="$PWD/.pyinstaller-cache/embedded-tools"

echo "正在准备内置后台工具..."
./prepare_embedded_tools.sh

echo "正在生成可分发的 $APP_NAME.app..."
ACAN_BUNDLED_TOOLS_DIR="$EMBEDDED_TOOLS_DIR" ACAN_SKIP_INSTALL=1 ./build_app.sh

if [ ! -d "$APP_BUNDLE" ]; then
  echo "打包失败：没有找到 $APP_BUNDLE"
  exit 1
fi

if command -v xattr >/dev/null 2>&1; then
  xattr -cr "$APP_BUNDLE" || true
fi

/usr/libexec/PlistBuddy -c "Set :CFBundleShortVersionString $VERSION" "$APP_BUNDLE/Contents/Info.plist" >/dev/null 2>&1 || true
/usr/libexec/PlistBuddy -c "Set :CFBundleVersion $VERSION" "$APP_BUNDLE/Contents/Info.plist" >/dev/null 2>&1 || true

STAGING_DIR="$(mktemp -d -t acan-studio-dmg)"
trap 'rm -rf "$STAGING_DIR"' EXIT

cp -R "$APP_BUNDLE" "$STAGING_DIR/"
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
echo "测试方式：双击 DMG，将 $APP_NAME.app 拖到 Applications。"
