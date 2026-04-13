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
import threading
import tkinter as tk
from datetime import datetime, timezone
from pathlib import Path
from shutil import which
from tkinter import filedialog, messagebox, scrolledtext, ttk

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


def get_ffmpeg_binary_name() -> str:
    """OS に応じた ffmpeg 実行ファイル名を返す。"""
    return "ffmpeg.exe" if platform.system() == "Windows" else "ffmpeg"


def get_ffmpeg_path() -> Path | None:
    """バンドル済みの ffmpeg を優先して返す。なければ PATH 上の ffmpeg を探す。"""
    ffmpeg_name = get_ffmpeg_binary_name()
    bundle_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    bundled_ffmpeg = bundle_dir / ffmpeg_name
    if bundled_ffmpeg.exists():
        return bundled_ffmpeg

    system_ffmpeg = which(ffmpeg_name)
    if system_ffmpeg:
        return Path(system_ffmpeg)

    return None


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


def default_log(message: str) -> None:
    console.print(message)


def default_progress(current: int, total: int, track_info: str) -> None:
    console.print(f"[{current:02d}/{total:02d}] {track_info}")


def download_playlist(
    playlist_url: str,
    output_base: Path,
    ffmpeg_path: Path,
    log_callback=None,
    progress_callback=None,
) -> tuple[dict, Path]:
    if log_callback is None:
        log_callback = default_log
    if progress_callback is None:
        progress_callback = default_progress

    log_callback("🔍 プレイリスト情報を取得中...")
    playlist_info = fetch_playlist_info(playlist_url)

    playlist_title: str = playlist_info.get("title") or "Unknown Playlist"
    entries = playlist_info.get("entries") or []
    total = len(entries)

    log_callback(f"📋 プレイリスト: {playlist_title}")
    log_callback(f"🔍 {total} 曲 を解析中...")

    playlist_dir = output_base / sanitize_filename(playlist_title)
    playlist_dir.mkdir(parents=True, exist_ok=True)
    log_callback(f"📁 ダウンロード先: {playlist_dir}")

    tracks_result: list[dict] = []
    downloaded_count = 0
    skipped_count = 0
    error_count = 0

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
        progress_callback(idx, total, display_label[:80])

        base_name = build_filename(idx, raw_artist, raw_title)
        outtmpl = str(playlist_dir / base_name)

        try:
            download_track(track_url, outtmpl, ffmpeg_path)
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
    report_path = save_report(playlist_dir, metadata)

    log_callback("✅ ダウンロード処理が完了しました。")
    log_callback(f"📁 保存先: {playlist_dir}")
    log_callback(f"📄 レポート: {report_path}")

    return metadata, report_path


def run_gui() -> None:
    root = tk.Tk()
    root.title("moby_rakuraku_downloader")
    root.geometry("680x440")
    root.resizable(False, False)

    tk.Label(root, text="SoundCloud プレイリスト URL:", font=(None, 11)).pack(anchor="w", padx=12, pady=(12, 0))
    url_entry = tk.Entry(root, width=88)
    url_entry.pack(padx=12, pady=(4, 8))

    tk.Label(root, text="保存先フォルダ:", font=(None, 11)).pack(anchor="w", padx=12, pady=(4, 0))
    output_frame = tk.Frame(root)
    output_frame.pack(fill="x", padx=12, pady=(4, 8))
    output_var = tk.StringVar(value=str(get_default_output_dir()))
    output_entry = tk.Entry(output_frame, textvariable=output_var, width=75)
    output_entry.pack(side="left", fill="x", expand=True)

    def choose_output_dir() -> None:
        selected = filedialog.askdirectory(initialdir=str(Path.home()))
        if selected:
            output_var.set(selected)

    tk.Button(output_frame, text="選択", command=choose_output_dir, width=8).pack(side="right", padx=(8, 0))

    status_var = tk.StringVar(value="準備完了")
    status_label = tk.Label(root, textvariable=status_var, anchor="w")
    status_label.pack(fill="x", padx=12, pady=(0, 8))

    progress_bar = tk.ttk.Progressbar(root, mode="determinate")
    progress_bar.pack(fill="x", padx=12, pady=(0, 8))

    tk.Label(root, text="ログ:", font=(None, 11)).pack(anchor="w", padx=12, pady=(0, 0))
    log_text = scrolledtext.ScrolledText(root, state="disabled", wrap="word", height=12)
    log_text.pack(fill="both", padx=12, pady=(4, 12), expand=True)

    def append_log(message: str) -> None:
        log_text.config(state="normal")
        log_text.insert("end", message + "\n")
        log_text.see("end")
        log_text.config(state="disabled")

    def gui_log(message: str) -> None:
        root.after(0, lambda: append_log(message))

    def gui_progress(current: int, total: int, track_info: str) -> None:
        root.after(0, lambda: progress_bar.config(value=(current / total) * 100 if total else 0))
        root.after(0, lambda: status_var.set(f"{current}/{total} - {track_info}"))

    def set_controls(enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        start_button.config(state=state)
        url_entry.config(state=state)
        output_entry.config(state=state)

    def on_start() -> None:
        playlist_url = url_entry.get().strip()
        if not playlist_url:
            messagebox.showwarning("入力が必要です", "SoundCloud プレイリストURLを入力してください。")
            return

        output_base = Path(output_var.get()).expanduser()
        if not output_base.exists():
            try:
                output_base.mkdir(parents=True, exist_ok=True)
            except Exception as exc:
                messagebox.showerror("保存先エラー", f"保存先フォルダを作成できませんでした:\n{exc}")
                return

        set_controls(False)
        append_log("▶ ダウンロードを開始します。")
        status_var.set("ダウンロード中...")
        progress_bar.config(value=0)

        def worker() -> None:
            try:
                ffmpeg_path = get_ffmpeg_path()
                if ffmpeg_path is None:
                    raise RuntimeError("ffmpeg が見つかりません。実行ファイルの同梱ビルドを使用してください。")
                download_playlist(
                    playlist_url,
                    output_base,
                    ffmpeg_path,
                    log_callback=gui_log,
                    progress_callback=gui_progress,
                )
                root.after(0, lambda: messagebox.showinfo("完了", "ダウンロードが完了しました。ログを確認してください。"))
            except Exception as exc:
                root.after(0, lambda: messagebox.showerror("エラー", str(exc)))
                gui_log(f"❌ エラー: {exc}")
            finally:
                root.after(0, lambda: set_controls(True))

        threading.Thread(target=worker, daemon=True).start()

    start_button = tk.Button(root, text="ダウンロード開始", command=on_start, width=18)
    start_button.pack(pady=(0, 8))

    root.mainloop()


def fetch_playlist_info(playlist_url: str) -> dict:
    """プレイリストのメタデータ（楽曲リスト）を取得する。"""
    ydl_opts = {
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


def download_track(track_url: str, output_path: str, ffmpeg_path: Path | None = None) -> None:
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
    if ffmpeg_path is not None:
        ydl_opts["ffmpeg_location"] = str(ffmpeg_path)

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
    if len(sys.argv) == 1:
        run_gui()
        return

    args = parse_args()
    playlist_url: str | None = args.playlist_url
    if playlist_url is None:
        playlist_url = prompt_for_playlist_url()

    output_base: Path = Path(args.output).expanduser() if args.output else get_default_output_dir()

    ffmpeg_path = get_ffmpeg_path()
    if ffmpeg_path is None:
        console.print(
            "[bold red]❌ ffmpeg が見つかりません。ffmpeg.exe を同梱したビルドを使うか、ffmpeg をインストールしてください。[/bold red]"
        )
        sys.exit(1)

    console.print(Panel("[bold magenta]🎵 moby_rakuraku_downloader[/bold magenta]", expand=False))
    try:
        download_playlist(
            playlist_url,
            output_base,
            ffmpeg_path,
        )
    except Exception as exc:
        console.print(f"[bold red]❌ エラー: {exc}[/bold red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
