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
set "FFMPEG_PATH="
if exist "%~dp0ffmpeg.exe" set "FFMPEG_PATH=%~dp0ffmpeg.exe"
if "%FFMPEG_PATH%"=="" (
    for /f "delims=" %%I in ('where ffmpeg 2^>nul') do (
        set "FFMPEG_PATH=%%I"
        goto :found_ffmpeg
    )
)
:found_ffmpeg
if "%FFMPEG_PATH%"=="" (
    echo [WARN] ffmpeg.exe が見つかりません。download_ffmpeg.py で自動取得します...
    python "%~dp0download_ffmpeg.py"
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] ffmpeg の取得に失敗しました。
        pause
        exit /b 1
    )
    if exist "%~dp0ffmpeg.exe" set "FFMPEG_PATH=%~dp0ffmpeg.exe"
)

if "%FFMPEG_PATH%"=="" (
    echo [ERROR] ffmpeg.exe が見つかりません。リポジトリルートに ffmpeg.exe を置くか、PATH に追加してください。
    pause
    exit /b 1
)

pyinstaller --onefile --add-binary "%FFMPEG_PATH%;." --name moby_rakuraku_downloader --noconsole downloader.py
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
pause
