# moby_rakuraku_downloader - はじめてガイド

このツールは SoundCloud のプレイリストをまとめてダウンロードし、MP3 形式で保存するためのものです。

## 使い方のポイント

- ダウンロード前に各曲の著作権／ライセンス情報を確認できます。
- GUI では曲ごとにチェックボックスを使って、個別または一括ダウンロードを選択できます。

## 法的な注意

- このツールを使って楽曲をダウンロードする際は、必ず SoundCloud の利用規約と著作権法を遵守してください。
- 著作権で保護された音源をダウンロードするには、権利者の許可が必要です。
- 本ツールは、合法的な用途での利用を前提としています。

## 何ができるの?

- SoundCloud のプレイリスト URL を入力すると、曲を一括ダウンロード
- ダウンロードした曲は MP3 形式で保存される
- Windows なら GUI で簡単に操作できる

## はじめに準備するもの

1. Windows の `.exe` を使う場合は、`moby_rakuraku_downloader.exe` だけをダウンロードすれば OK です。
2. Python 版を使う場合のみ、このリポジトリをダウンロードして `python downloader.py` を実行します。
3. Python 版（ソース実行）を使う場合は `ffmpeg` が必要です。
   - Windows のソース版では `download_ffmpeg.py` で自動取得できます。
   - `.exe` 配布版には `ffmpeg` を同梱しているため、別途インストールは不要です。

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
