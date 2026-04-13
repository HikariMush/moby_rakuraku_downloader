#!/usr/bin/env python3
"""Download latest ffmpeg build into the repository root."""

import argparse
import json
import os
import platform
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
GITHUB_API_URL = "https://api.github.com/repos/BtbN/FFmpeg-Builds/releases/latest"

ASSET_MAP = {
    "Windows": "win64-gpl.zip",
    "Linux": "linux64-gpl.tar.xz",
    "Darwin": "macos64-gpl.zip",
}

OUTPUT_MAP = {
    "Windows": "ffmpeg.exe",
    "Linux": "ffmpeg",
    "Darwin": "ffmpeg",
}


def log(message: str) -> None:
    print(message, file=sys.stderr)


def fetch_latest_release() -> dict:
    req = urllib.request.Request(GITHUB_API_URL, headers={"User-Agent": "moby_rakuraku_downloader"})
    with urllib.request.urlopen(req) as resp:
        if resp.status != 200:
            raise RuntimeError(f"GitHub API request failed: {resp.status}")
        return json.load(resp)


def choose_asset(release_data: dict, target_name: str) -> dict:
    for asset in release_data.get("assets", []):
        if target_name in asset.get("name", ""):
            return asset
    raise RuntimeError(f"対応する ffmpeg ビルドが見つかりません: {target_name}")


def download_asset(url: str, dest_path: Path) -> None:
    log(f"Downloading {url}")
    with urllib.request.urlopen(url) as response:
        response.raise_for_status()
        with open(dest_path, "wb") as out_file:
            while True:
                chunk = response.read(8192)
                if not chunk:
                    break
                out_file.write(chunk)


def extract_ffmpeg_from_zip(zip_path: Path, output_name: str) -> Path:
    with zipfile.ZipFile(zip_path, "r") as zf:
        candidates = [name for name in zf.namelist() if name.endswith(output_name)]
        if not candidates:
            raise RuntimeError(f"{output_name} がアーカイブ内に見つかりませんでした")
        source_name = candidates[0]
        dest_path = REPO_ROOT / output_name
        with zf.open(source_name) as src, open(dest_path, "wb") as dst:
            dst.write(src.read())
    return dest_path


def extract_ffmpeg_from_tar(tar_path: Path, output_name: str) -> Path:
    with tarfile.open(tar_path, "r:xz") as tf:
        members = [m for m in tf.getmembers() if m.name.endswith(output_name) and m.isfile()]
        if not members:
            raise RuntimeError(f"{output_name} がアーカイブ内に見つかりませんでした")
        member = members[0]
        dest_path = REPO_ROOT / output_name
        with tf.extractfile(member) as src, open(dest_path, "wb") as dst:
            dst.write(src.read())
    return dest_path


def set_executable(path: Path) -> None:
    if platform.system() != "Windows":
        mode = path.stat().st_mode
        path.chmod(mode | 0o111)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download ffmpeg into the repository root.")
    parser.add_argument("--force", action="store_true", help="既存のファイルを上書きして再取得する")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    system_name = platform.system()
    if system_name not in ASSET_MAP:
        log(f"このOSには未対応です: {system_name}")
        return 1

    output_name = OUTPUT_MAP[system_name]
    output_path = REPO_ROOT / output_name
    if output_path.exists() and not args.force:
        log(f"既に ffmpeg が存在します: {output_path}")
        return 0

    release_data = fetch_latest_release()
    asset = choose_asset(release_data, ASSET_MAP[system_name])
    with tempfile.NamedTemporaryFile(suffix=Path(asset["name"]).suffix, delete=False) as tmp_file:
        archive_path = Path(tmp_file.name)
    try:
        download_asset(asset["browser_download_url"], archive_path)
        if archive_path.suffix == ".zip":
            extracted_path = extract_ffmpeg_from_zip(archive_path, output_name)
        elif archive_path.suffix == ".xz":
            extracted_path = extract_ffmpeg_from_tar(archive_path, output_name)
        else:
            raise RuntimeError(f"未対応のアーカイブ形式: {archive_path.suffix}")
        set_executable(extracted_path)
        log(f"ffmpeg を作成しました: {extracted_path}")
        return 0
    finally:
        if archive_path.exists():
            archive_path.unlink()


if __name__ == "__main__":
    raise SystemExit(main())
