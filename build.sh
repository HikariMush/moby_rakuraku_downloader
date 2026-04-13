#!/bin/bash
set -e

echo "========================================"
echo " moby_rakuraku_downloader - Mac/Linux Build"
echo "========================================"
echo ""

echo "[1/2] 依存パッケージをインストール中..."
pip install -r requirements.txt

echo ""
echo "[2/2] バイナリをビルド中..."
FFMPEG_PATH=""
if [ -f "$(pwd)/ffmpeg" ]; then
  FFMPEG_PATH="$(pwd)/ffmpeg"
fi
if [ -z "$FFMPEG_PATH" ]; then
  FFMPEG_PATH="$(command -v ffmpeg 2>/dev/null || true)"
fi
if [ -z "$FFMPEG_PATH" ]; then
  echo "[WARN] ffmpeg が見つかりません。download_ffmpeg.py で自動取得します..."
  python download_ffmpeg.py
  if [ $? -ne 0 ]; then
    echo "[ERROR] ffmpeg の取得に失敗しました。"
    exit 1
  fi
  if [ -f "$(pwd)/ffmpeg" ]; then
    FFMPEG_PATH="$(pwd)/ffmpeg"
  fi
fi
if [ -z "$FFMPEG_PATH" ]; then
  echo "[ERROR] ffmpeg が見つかりません。リポジトリルートに ffmpeg を置くか、PATH に追加してください。"
  exit 1
fi

pyinstaller --onefile --add-binary "$FFMPEG_PATH:." --name moby_rakuraku_downloader --noconsole downloader.py

echo ""
echo "========================================"
echo " ビルド完了！"
echo " dist/moby_rakuraku_downloader"
echo "========================================"
echo ""
echo "実行権限を付与するには: chmod +x dist/moby_rakuraku_downloader"
echo ""
