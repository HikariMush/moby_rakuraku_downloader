#!/usr/bin/env python3
"""
moby_rakuraku_downloader - SoundCloud プレイリスト一括ダウンローダー

このツールは著作権法および SoundCloud の利用規約を遵守して使用してください。
著作権で保護された楽曲のダウンロードは、権利者の許可がある場合に限ります。
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
    parser.add_argument(
        "--format",
        "-f",
        choices=["mp3", "wav"],
        default="mp3",
        help="出力音声形式（mp3 または wav）",
    )
    parser.add_argument(
        "--bitrate",
        "-b",
        choices=["128", "192", "256", "320"],
        default="192",
        help="MP3 出力時のビットレート（kbps）",
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
    audio_format: str = "mp3",
    audio_bitrate: str = "192",
    playlist_info: dict | None = None,
    selected_track_indices: list[int] | None = None,
    log_callback=None,
    progress_callback=None,
) -> tuple[dict, Path]:
    if log_callback is None:
        log_callback = default_log
    if progress_callback is None:
        progress_callback = default_progress

    if playlist_info is None:
        log_callback("🔍 プレイリスト情報を取得中...")
        playlist_info = fetch_playlist_info(playlist_url)

    playlist_title: str = playlist_info.get("title") or "Unknown Playlist"
    entries = playlist_info.get("entries") or []
    total = len(entries)
    selected_set = set(selected_track_indices) if selected_track_indices is not None else None

    log_callback(f"📋 プレイリスト: {playlist_title}")
    log_callback(f"🔍 {total} 曲 を解析中...")

    playlist_dir = output_base / sanitize_filename(playlist_title)
    playlist_dir.mkdir(parents=True, exist_ok=True)
    log_callback(f"📁 ダウンロード先: {playlist_dir}")

    tracks_result: list[dict] = []
    downloaded_count = 0
    skipped_count = 0
    not_selected_count = 0
    error_count = 0

    for idx, entry in enumerate(entries, start=1):
        if selected_set is not None and idx not in selected_set:
            raw_title = entry.get("title") or "Unknown Title"
            raw_artist = (
                entry.get("uploader")
                or entry.get("artist")
                or entry.get("creator")
                or "Unknown Artist"
            )
            display_label = f"{raw_artist} - {raw_title}"
            progress_callback(idx, total, display_label[:80])
            log_callback(f"⏭️ {display_label} はユーザーによりスキップされました。")
            tracks_result.append(
                {
                    "index": idx,
                    "title": raw_title,
                    "artist": raw_artist,
                    "url": entry.get("url") or entry.get("webpage_url") or "",
                    "status": "not_selected",
                    "reason": "user_not_selected",
                }
            )
            not_selected_count += 1
            continue

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
            track_info = fetch_track_info(track_url, ffmpeg_path)
            source_format = track_info.get("ext") or "unknown"
            source_bitrate = track_info.get("abr") or track_info.get("tbr")
            if source_bitrate is not None:
                source_desc = f"{source_format} {int(source_bitrate)}kbps"
            else:
                source_desc = source_format
            log_callback(f"🎧 原音源: {source_desc}")
            download_track(track_url, outtmpl, ffmpeg_path, audio_format, audio_bitrate)
            filename = base_name + f".{audio_format}"
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
        "not_selected_count": not_selected_count,
        "error_count": error_count,
        "tracks": tracks_result,
    }
    save_metadata(playlist_dir, metadata)
    report_path = save_report(playlist_dir, metadata)

    log_callback("✅ ダウンロード処理が完了しました。")
    log_callback(f"📁 保存先: {playlist_dir}")
    log_callback(f"📄 レポート: {report_path}")

    return metadata, report_path

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
            track_info = fetch_track_info(track_url, ffmpeg_path)
            source_format = track_info.get("ext") or "unknown"
            source_bitrate = track_info.get("abr") or track_info.get("tbr")
            if source_bitrate is not None:
                source_desc = f"{source_format} {int(source_bitrate)}kbps"
            else:
                source_desc = source_format
            log_callback(f"🎧 原音源: {source_desc}")
            download_track(track_url, outtmpl, ffmpeg_path, audio_format, audio_bitrate)
            filename = base_name + f".{audio_format}"
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

    options_frame = tk.Frame(root)
    options_frame.pack(fill="x", padx=12, pady=(0, 8))

    tk.Label(options_frame, text="出力形式:", font=(None, 11)).grid(row=0, column=0, sticky="w")
    format_var = tk.StringVar(value="mp3")
    format_select = ttk.Combobox(options_frame, textvariable=format_var, values=["mp3", "wav"], state="readonly", width=8)
    format_select.grid(row=0, column=1, sticky="w", padx=(8, 16))

    tk.Label(options_frame, text="ビットレート:", font=(None, 11)).grid(row=0, column=2, sticky="w")
    bitrate_var = tk.StringVar(value="192")
    bitrate_select = ttk.Combobox(options_frame, textvariable=bitrate_var, values=["128", "192", "256", "320"], state="readonly", width=6)
    bitrate_select.grid(row=0, column=3, sticky="w", padx=(8, 0))

    def update_bitrate_state(event=None) -> None:
        if format_var.get() == "wav":
            bitrate_select.config(state="disabled")
        else:
            bitrate_select.config(state="readonly")

    format_select.bind("<<ComboboxSelected>>", update_bitrate_state)
    update_bitrate_state()

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

    def show_track_selection_dialog(playlist_info: dict) -> list[int] | None:
        entries = playlist_info.get("entries") or []
        if not entries:
            messagebox.showerror("エラー", "プレイリストに曲が含まれていません。")
            return None

        dialog = tk.Toplevel(root)
        dialog.title("ダウンロードする曲を選択")
        dialog.geometry("700x520")
        dialog.resizable(False, False)
        dialog.grab_set()

        info_label = tk.Label(dialog, text="ダウンロードする曲を選択してください。著作権情報を確認して選択できます。", anchor="w", justify="left", wraplength=680)
        info_label.pack(fill="x", padx=12, pady=(12, 8))

        button_frame = tk.Frame(dialog)
        button_frame.pack(fill="x", padx=12, pady=(0, 8))
        tk.Button(button_frame, text="すべて選択", command=lambda: [var.set(1) for var in checkbox_vars]).pack(side="left")
        tk.Button(button_frame, text="すべて解除", command=lambda: [var.set(0) for var in checkbox_vars]).pack(side="left", padx=(8, 0))

        canvas = tk.Canvas(dialog)
        scrollbar = tk.Scrollbar(dialog, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas)

        scroll_frame.bind(
            "<Configure>",
            lambda event: canvas.configure(scrollregion=canvas.bbox("all")),
        )

        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True, padx=(12, 0), pady=(0, 12))
        scrollbar.pack(side="right", fill="y", pady=(0, 12), padx=(0, 12))

        checkbox_vars: list[tk.IntVar] = []
        for idx, entry in enumerate(entries, start=1):
            title = entry.get("title") or "Unknown Title"
            artist = entry.get("uploader") or entry.get("artist") or entry.get("creator") or "Unknown Artist"
            license_info = get_track_license(entry)
            label_text = f"{idx}. {artist} - {title}  [{license_info}]"
            var = tk.IntVar(value=1)
            checkbox = tk.Checkbutton(scroll_frame, text=label_text, variable=var, anchor="w", justify="left", wraplength=640)
            checkbox.pack(fill="x", padx=4, pady=2)
            checkbox_vars.append(var)

        selected_indices: list[int] = []

        def on_ok() -> None:
            nonlocal selected_indices
            selected_indices = [idx + 1 for idx, var in enumerate(checkbox_vars) if var.get()]
            if not selected_indices:
                messagebox.showwarning("選択が必要です", "少なくとも1つの曲を選択してください。")
                return
            dialog.destroy()

        def on_cancel() -> None:
            dialog.destroy()

        action_frame = tk.Frame(dialog)
        action_frame.pack(fill="x", padx=12, pady=(0, 12))
        tk.Button(action_frame, text="ダウンロード開始", command=on_ok, width=16).pack(side="right")
        tk.Button(action_frame, text="キャンセル", command=on_cancel, width=10).pack(side="right", padx=(0, 8))

        root.wait_window(dialog)
        return selected_indices if selected_indices else None

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
        append_log("▶ プレイリスト情報を取得中...")
        status_var.set("プレイリスト情報取得中...")

        try:
            playlist_info = fetch_playlist_info(playlist_url)
        except Exception as exc:
            messagebox.showerror("エラー", f"プレイリスト情報の取得に失敗しました:\n{exc}")
            set_controls(True)
            return

        selected_indices = show_track_selection_dialog(playlist_info)
        if selected_indices is None:
            set_controls(True)
            append_log("⏹️ ダウンロードはキャンセルされました。")
            status_var.set("準備完了")
            return

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
                    audio_format=format_var.get(),
                    audio_bitrate=bitrate_var.get(),
                    playlist_info=playlist_info,
                    selected_track_indices=selected_indices,
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


def fetch_track_info(track_url: str, ffmpeg_path: Path | None = None) -> dict:
    """楽曲のメタ情報を取得する。"""
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
    }
    if ffmpeg_path is not None:
        ydl_opts["ffmpeg_location"] = str(ffmpeg_path)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(track_url, download=False)


def get_track_license(entry: dict) -> str:
    """楽曲のライセンス情報を取得する。"""
    return (
        entry.get("license")
        or entry.get("track_license")
        or entry.get("license_url")
        or entry.get("copyright")
        or "不明"
    )


def parse_track_selection_input(selection: str, total: int) -> list[int]:
    """ユーザー入力から選択されたトラック番号のリストを作成する。"""
    selection = selection.strip().lower()
    if not selection or selection in ("all", "a"):
        return list(range(1, total + 1))

    indices: set[int] = set()
    for part in selection.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            bounds = part.split("-", 1)
            if len(bounds) != 2:
                raise ValueError(f"無効な選択形式です: {part}")
            start_str, end_str = bounds
            start = int(start_str)
            end = int(end_str)
            if start > end:
                raise ValueError(f"範囲の開始が終了より大きいです: {part}")
            indices.update(range(start, end + 1))
        else:
            indices.add(int(part))

    selected = sorted(i for i in indices if 1 <= i <= total)
    if not selected:
        raise ValueError("有効なトラック番号が選択されませんでした。")
    return selected


def prompt_track_selection(entries: list[dict]) -> list[int]:
    """CLI で個別または一括ダウンロードするトラックを選択する。"""
    total = len(entries)
    if total == 0:
        raise ValueError("プレイリストに曲が含まれていません。")

    console.print("\n📋 ダウンロードする曲を選択してください。\n")
    for idx, entry in enumerate(entries, start=1):
        title = entry.get("title") or "Unknown Title"
        artist = entry.get("uploader") or entry.get("artist") or entry.get("creator") or "Unknown Artist"
        license_info = get_track_license(entry)
        console.print(f"{idx}. {artist} - {title}  [{license_info}]")

    console.print(
        "\nすべてダウンロードする場合は Enter を押してください。"
        "\n特定の曲を選択する場合は、番号をカンマ区切りまたは範囲指定で入力してください。例: 1,3-5"
    )
    selection = input("選択: ")
    return parse_track_selection_input(selection, total)


def build_filename(index: int, artist: str, title: str) -> str:
    """規則に従ったファイル名を生成する（拡張子なし）。"""
    artist_s = sanitize_filename(artist or "unknown_artist")
    title_s = sanitize_filename(title or "unknown_title")
    return f"{index:02d}_{artist_s} - {title_s}"


def validate_audio_settings(audio_format: str, audio_bitrate: str | None) -> str | None:
    """オーディオ出力設定を検証し、MP3 の場合はビットレートを返す。"""
    if audio_format not in ("mp3", "wav"):
        raise ValueError(f"Unsupported audio format: {audio_format}")

    if audio_format == "wav":
        return None

    if audio_bitrate is None:
        audio_bitrate = "192"

    if audio_bitrate not in ("128", "192", "256", "320"):
        raise ValueError(f"Invalid MP3 bitrate: {audio_bitrate}")

    return audio_bitrate


def download_track(
    track_url: str,
    output_path: str,
    ffmpeg_path: Path | None = None,
    audio_format: str = "mp3",
    audio_bitrate: str = "192",
) -> None:
    """単一楽曲をダウンロードして指定形式に変換する。"""
    validated_bitrate = validate_audio_settings(audio_format, audio_bitrate)

    postprocessor = {
        "key": "FFmpegExtractAudio",
        "preferredcodec": audio_format,
    }
    if validated_bitrate is not None:
        postprocessor["preferredquality"] = validated_bitrate

    ydl_opts = {
        "format": "bestaudio/best",
        "postprocessors": [postprocessor],
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
        f"[NOT_SELECTED] {data.get('not_selected_count', 0)} tracks",
        f"[ERROR]   {data['error_count']} tracks",
        "",
        "--- Skipped / Error / Unselected Tracks ---",
    ]

    for track in data["tracks"]:
        if track["status"] == "skipped":
            lines.append(
                f"[SKIP]  {track.get('artist', '?')} - {track.get('title', '?')}  ({track.get('reason', '')})"
            )
        elif track["status"] == "not_selected":
            lines.append(
                f"[NOT_SELECTED] {track.get('artist', '?')} - {track.get('title', '?')}  ({track.get('reason', '')})"
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
        playlist_info = fetch_playlist_info(playlist_url)
        selected_indices = prompt_track_selection(playlist_info.get("entries") or [])
        download_playlist(
            playlist_url,
            output_base,
            ffmpeg_path,
            audio_format=args.format,
            audio_bitrate=args.bitrate,
            playlist_info=playlist_info,
            selected_track_indices=selected_indices,
        )
    except ValueError as exc:
        console.print(f"[bold yellow]⚠️ 入力エラー: {exc}[/bold yellow]")
        sys.exit(1)
    except Exception as exc:
        console.print(f"[bold red]❌ エラー: {exc}[/bold red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
