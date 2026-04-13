# moby_rakuraku_downloader - はじめてガイド

このツールは SoundCloud のプレイリストをまとめてダウンロードし、MP3 形式で保存するためのものです。

## 何ができるの?

- SoundCloud のプレイリスト URL を入力すると、曲を一括ダウンロード
- ダウンロードした曲は MP3 形式で保存される
- Windows なら GUI で簡単に操作できる

## はじめに準備するもの

1. Windows で使う場合は、`moby_rakuraku_downloader.exe` だけをダウンロードすれば OK です。
2. Python 版を使う場合のみ、このリポジトリをダウンロードして `python downloader.py` を実行します。
3. `ffmpeg` が必要です。Windows の `.exe` 配布版には `ffmpeg` を同梱しています。
   - ソース版を使う場合は `download_ffmpeg.py` で自動取得できます。

## 使い方（Windows の場合）

1. `moby_rakuraku_downloader.exe` をダブルクリック
2. 表示されたウィンドウに SoundCloud のプレイリスト URL を貼り付ける
3. 保存先を指定して「ダウンロード開始」をクリック
4. 完了メッセージが出たら保存先を開いて確認する

## 使い方（コマンドライン）

1. ターミナルを開く
2. このリポジトリのフォルダに移動する
3. 次のコマンドを実行する

```bash
python downloader.py https://soundcloud.com/user/sets/playlist-name
```

- MP3 320kbps にしたい場合:

```bash
python downloader.py https://soundcloud.com/user/sets/playlist-name --format mp3 --bitrate 320
```

- WAV 出力にしたい場合:

```bash
python downloader.py https://soundcloud.com/user/sets/playlist-name --format wav
```

## よくあるトラブルと対処

- `ffmpeg が見つからない` と表示されたら
  - `download_ffmpeg.py` を実行するか、`ffmpeg` を PATH に追加する
- URL を間違えている場合は、SoundCloud でプレイリスト画面を開き直してコピーし直す
- ダウンロードできない曲がある場合は、楽曲の公開設定や地域制限が原因の場合があります

## サポート

- 使い方がわからない場合は、`README.md` の「使い方」のセクションも確認してください。
