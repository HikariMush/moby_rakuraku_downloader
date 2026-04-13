#!/usr/bin/env python3
"""
moby_rakuraku_downloader - SoundCloud プレイリスト一括ダウンローダー
"""

import argparse
import json
import os
import platform
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import yt_dlp
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
)
from rich.rule import Rule
from rich.table import Table

console = Console()

# ファイル名に使えない文字をアンダースコアに置換する正規表現
INVALID_CHARS_RE = re.compile(r'[/\\:*?"<>|]')


def sanitize_filename(name: str) -> str:
    """ファイル名に使えない文字をアンダースコアに置換する。"""
    return INVALID_CHARS_RE.sub("_", name).strip()


def get_default_output_dir() -> Path:
    """OS に応じたデフォルト保存先を返す。"""
    if platform.system() == "Windows":
        return Path(os.environ.get("USERPROFILE", "C:/Users/user")) / "Downloads" / "SoundCloud"
    return Path.home() / "Downloads" / "SoundCloud"


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="moby_rakuraku_downloader",
        description="SoundCloud プレイリストを MP3 で一括ダウンロードします。",
    )
    parser.add_argument(
        "playlist_url",
        nargs="?",
        default=None,
        help="SoundCloud のプレイリスト URL",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help=f"保存先ディレクトリ（デフォルト: {get_default_output_dir()}）",
    )
    return parser.parse_args(argv)


def prompt_for_playlist_url() -> str:
    """コマンドライン実行時に URL を入力させる。"""
    playlist_url = input("SoundCloud プレイリストURLを入力してください: ").strip()
    if not playlist_url:
        console.print("[bold red]❌ プレイリスト URL が入力されませんでした。終了します。[/bold red]")
        sys.exit(1)
    return playlist_url


def fetch_playlist_info(playlist_url: str) -> dict:
    """プレイリストのメタデータ（楽曲リスト）を取得する。"""
    ydl_opts = {
        "extract_flat": True,
        "quiet": True,
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(playlist_url, download=False)
    return info


def build_filename(index: int, artist: str, title: str) -> str:
    """規則に従ったファイル名を生成する（拡張子なし）。"""
    artist_s = sanitize_filename(artist or "unknown_artist")
    title_s = sanitize_filename(title or "unknown_title")
    return f"{index:02d}_{artist_s} - {title_s}"


def download_track(track_url: str, output_path: str) -> None:
    """単一楽曲をダウンロードして MP3 に変換する。"""
    ydl_opts = {
        "format": "bestaudio/best",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "outtmpl": output_path,
        "quiet": True,
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([track_url])


def classify_error(error_msg: str) -> str:
    """エラーメッセージから失敗理由を分類する。"""
    msg_lower = error_msg.lower()
    if "download disabled" in msg_lower or "this track is not available" in msg_lower:
        return "download_disabled"
    if "region" in msg_lower or "country" in msg_lower or "geo" in msg_lower:
        return "region_restricted"
    if (
        "network" in msg_lower
        or "connection" in msg_lower
        or "timeout" in msg_lower
        or "urlopen" in msg_lower
    ):
        return "network_error"
    if "private" in msg_lower:
        return "private_track"
    return "unknown_error"


def save_metadata(output_dir: Path, data: dict) -> Path:
    """metadata.json を保存する。"""
    metadata_path = output_dir / "metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return metadata_path


def save_report(output_dir: Path, data: dict) -> Path:
    """download_report.txt を保存する。"""
    report_path = output_dir / "download_report.txt"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        "=== moby_rakuraku_downloader - Download Report ===",
        f"Date: {now_str}",
        f"Playlist: {data['playlist_title']}",
        f"URL: {data['playlist_url']}",
        "",
        f"[SUCCESS] {data['downloaded_count']} tracks downloaded",
        f"[SKIPPED] {data['skipped_count']} tracks",
        f"[ERROR]   {data['error_count']} tracks",
        "",
        "--- Skipped / Error Tracks ---",
    ]

    for track in data["tracks"]:
        if track["status"] == "skipped":
            lines.append(
                f"[SKIP]  {track.get('artist', '?')} - {track.get('title', '?')}  ({track.get('reason', '')})"
            )
        elif track["status"] == "error":
            lines.append(
                f"[ERROR] {track.get('artist', '?')} - {track.get('title', '?')}  ({track.get('reason', '')})"
            )

    lines += ["", "--- Downloaded Tracks ---"]
    for track in data["tracks"]:
        if track["status"] == "downloaded":
            lines.append(f"[OK] {track.get('filename', '')}")

    lines.append("")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return report_path


def print_summary(
    playlist_title: str,
    output_dir: Path,
    report_path: Path,
    downloaded: int,
    skipped: int,
    errors: int,
) -> None:
    """ターミナルに結果サマリーを表示する。"""
    console.print(Rule(style="bright_blue"))

    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold green")
    table.add_column()
    table.add_row("✅ 成功:", f"[bold green]{downloaded}[/bold green]曲")
    table.add_row("⏭️  スキップ:", f"[bold yellow]{skipped}[/bold yellow]曲 (ダウンロード不可)")
    table.add_row("❌ エラー:", f"[bold red]{errors}[/bold red]曲")

    console.print(table)
    console.print()
    console.print(f"📁 保存先: [cyan]{output_dir}[/cyan]")
    console.print(f"📄 レポート: [cyan]{report_path}[/cyan]")


def main() -> None:
    args = parse_args()
    playlist_url: str | None = args.playlist_url
    if playlist_url is None:
        playlist_url = prompt_for_playlist_url()

    output_base: Path = Path(args.output).expanduser() if args.output else get_default_output_dir()

    # ヘッダー表示
    console.print(Panel("[bold magenta]🎵 moby_rakuraku_downloader[/bold magenta]", expand=False))

    # プレイリスト情報取得
    console.print("🔍 プレイリスト情報を取得中...")
    try:
        playlist_info = fetch_playlist_info(playlist_url)
    except Exception as exc:
        console.print(f"[bold red]❌ プレイリストの取得に失敗しました: {exc}[/bold red]")
        sys.exit(1)

    playlist_title: str = playlist_info.get("title") or "Unknown Playlist"
    entries = playlist_info.get("entries") or []
    total = len(entries)

    console.print(f"📋 プレイリスト: [bold]{playlist_title}[/bold]")
    console.print(f"🔍 [bold]{total}[/bold]曲 を解析中...")
    console.print()

    # 保存先ディレクトリを作成
    playlist_dir = output_base / sanitize_filename(playlist_title)
    playlist_dir.mkdir(parents=True, exist_ok=True)

    # 結果を格納するリスト
    tracks_result: list[dict] = []
    downloaded_count = 0
    skipped_count = 0
    error_count = 0

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TextColumn("| {task.fields[track_info]}"),
        console=console,
        transient=False,
    ) as progress:
        task = progress.add_task(
            f"[{0:02d}/{total:02d}]",
            total=total,
            track_info="",
        )

        for idx, entry in enumerate(entries, start=1):
            track_url: str = entry.get("url") or entry.get("webpage_url") or ""
            raw_title: str = entry.get("title") or "Unknown Title"
            raw_artist: str = (
                entry.get("uploader")
                or entry.get("artist")
                or entry.get("creator")
                or "Unknown Artist"
            )
            duration: int | None = entry.get("duration")

            display_label = f"{raw_artist} - {raw_title}"
            progress.update(
                task,
                description=f"[{idx:02d}/{total:02d}]",
                track_info=display_label[:60],
            )

            # ファイル名生成
            base_name = build_filename(idx, raw_artist, raw_title)
            outtmpl = str(playlist_dir / base_name)  # yt-dlp が .mp3 を付加する

            try:
                download_track(track_url, outtmpl)
                filename = base_name + ".mp3"
                tracks_result.append(
                    {
                        "index": idx,
                        "title": raw_title,
                        "artist": raw_artist,
                        "url": track_url,
                        "status": "downloaded",
                        "filename": filename,
                        "duration_seconds": duration,
                    }
                )
                downloaded_count += 1
            except yt_dlp.utils.DownloadError as exc:
                reason = classify_error(str(exc))
                # スキップ扱い（download_disabled / region_restricted / private）か
                # エラー扱い（network_error / unknown）か判定
                if reason in ("download_disabled", "region_restricted", "private_track"):
                    status = "skipped"
                    skipped_count += 1
                else:
                    status = "error"
                    error_count += 1
                tracks_result.append(
                    {
                        "index": idx,
                        "title": raw_title,
                        "artist": raw_artist,
                        "url": track_url,
                        "status": status,
                        "reason": reason,
                    }
                )
            except Exception as exc:
                reason = classify_error(str(exc))
                error_count += 1
                tracks_result.append(
                    {
                        "index": idx,
                        "title": raw_title,
                        "artist": raw_artist,
                        "url": track_url,
                        "status": "error",
                        "reason": reason,
                    }
                )
            finally:
                progress.advance(task)

    # metadata.json 保存
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    metadata = {
        "playlist_url": playlist_url,
        "playlist_title": playlist_title,
        "downloaded_at": now_utc,
        "total_tracks": total,
        "downloaded_count": downloaded_count,
        "skipped_count": skipped_count,
        "error_count": error_count,
        "tracks": tracks_result,
    }
    save_metadata(playlist_dir, metadata)

    # download_report.txt 保存
    report_path = save_report(playlist_dir, metadata)

    # サマリー表示
    print_summary(
        playlist_title,
        playlist_dir,
        report_path,
        downloaded_count,
        skipped_count,
        error_count,
    )


if __name__ == "__main__":
    main()
