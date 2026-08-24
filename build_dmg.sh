#!/bin/zsh
set -e

cd "$(dirname "$0")"

APP_NAME="ACAN Studio"
VERSION="1.0.0"
APP_BUNDLE="dist/$APP_NAME.app"
DMG_PATH="$PWD/dist/ACAN-Studio-${VERSION}.dmg"

echo "正在生成可分发的 $APP_NAME.app..."
ACAN_SKIP_INSTALL=1 ./build_app.sh

if [ ! -d "$APP_BUNDLE" ]; then
  echo "打包失败：没有找到 $APP_BUNDLE"
  exit 1
fi

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
