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
pyinstaller --onefile --name moby_rakuraku_downloader --console downloader.py

echo ""
echo "========================================"
echo " ビルド完了！"
echo " dist/moby_rakuraku_downloader"
echo "========================================"
echo ""
echo "実行権限を付与するには: chmod +x dist/moby_rakuraku_downloader"
echo ""
