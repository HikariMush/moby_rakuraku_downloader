# moby_rakuraku_downloader - 開発者向けドキュメント

このファイルは、ソースコードの開発・ビルド・テストを行う開発者向けの手順です。

## 開発環境のセットアップ

1. リポジトリをクローン

```bash
git clone https://github.com/HikariMush/moby_rakuraku_downloader
cd moby_rakuraku_downloader
```

2. Python の依存ライブラリをインストール

```bash
pip install -r requirements.txt
```

3. ffmpeg の用意

- Windows: `python download_ffmpeg.py`
- macOS: `brew install ffmpeg`
- Ubuntu/Linux: `sudo apt install ffmpeg`

`ffmpeg` が PATH にない場合は、`download_ffmpeg.py` で取得してください。

## ビルド方法

### Windows 用ビルド

```bash
build.bat
```

### macOS / Linux 用ビルド

```bash
bash build.sh
```

ビルド後、`dist/` フォルダに単体実行ファイルが生成されます。

## CLI の使い方

`downloader.py` はコマンドラインオプションで動作を切り替えられます。

- `--format` / `-f`: `mp3` または `wav`
- `--bitrate` / `-b`: `128`, `192`, `256`, `320` (MP3 出力時のみ有効)

例:

```bash
python downloader.py https://soundcloud.com/user/sets/playlist-name --format mp3 --bitrate 320
```

## テスト実行

ユニットテストは Python の `unittest` で実行できます。

```bash
python -m unittest tests.test_downloader
```

## リリース手順

このリポジトリでは、タグを `v*` 形式でプッシュすると GitHub Actions が自動的にビルドとリリースを作成します。

1. 変更をコミット
2. `RELEASE_NOTES.md` の `### 新機能` セクションを更新
3. 必要なら `README_BEGINNER.md` / `README_DEVELOPER.md` を更新
4. 新しいタグを作成

```bash
git tag v1.1.0
git push origin main
git push origin v1.1.0
```

5. GitHub Actions が `.exe` をビルドし、リリース本文を自動生成してリリースを作成します。

- リリース本文には `README_BEGINNER.md` / `README_DEVELOPER.md` のリンクが含まれます。
- `RELEASE_NOTES.md` の `### 新機能` セクションから、追加された機能の説明も自動的に挿入されます。

## CONTRIBUTING ガイドライン

開発は `CONTRIBUTING.md` に記載したルールに従ってください。

## 変更履歴とリリースノート

3. GitHub Actions が `.exe` をビルドし、リリース本文を自動生成してリリースを作成します。

- リリース本文には `README_BEGINNER.md`/`README_DEVELOPER.md` のリンクが含まれます。
- `RELEASE_NOTES.md` の `### 新機能` セクションから、追加された機能の説明も自動的に挿入されます。

## 変更履歴とリリースノート

- 主要な変更は `RELEASE_NOTES.md` にまとめています。
- 今回は `mp3/wav` 対応、`320kbps` MP3 出力対応、GUI と CLI 両対応の出力設定、元音源メタ情報のログ表示を追加しています。
