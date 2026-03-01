@echo off
echo ========================================
echo  moby_rakuraku_downloader - Windows Build
echo ========================================
echo.

echo [1/2] 依存パッケージをインストール中...
pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo [ERROR] pip install に失敗しました。Python がインストールされているか確認してください。
    pause
    exit /b 1
)

echo.
echo [2/2] .exe をビルド中...
pyinstaller --onefile --name moby_rakuraku_downloader --console downloader.py
if %ERRORLEVEL% neq 0 (
    echo [ERROR] ビルドに失敗しました。
    pause
    exit /b 1
)

echo.
echo ========================================
echo  ビルド完了！
echo  dist\moby_rakuraku_downloader.exe
echo ========================================
echo.
echo ※ ffmpeg.exe を dist\ フォルダに一緒に置いてから配布してください。
echo.
pause
