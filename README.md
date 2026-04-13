# 🎵 moby_rakuraku_downloader

SoundCloud のプレイリストURLを渡すだけで、ダウンロード可能な楽曲を自動判定して MP3 で一括保存するツールです。

> 最も簡単なのは、ビルド済みの単体実行ファイルを配布することです。
> `dist/moby_rakuraku_downloader.exe` / `dist/moby_rakuraku_downloader` は Python と ffmpeg を内包できるため、ユーザー側に別途インストールを要求しません。
> ダブルクリックだけで GUI が起動し、コマンドライン不要で操作できます。

---

## 必要なもの

| ツール | バージョン | 入手先 |
|--------|-----------|--------|
| Python | 3.10 以上 | https://www.python.org/downloads/ |
| ffmpeg | 最新版 | 下記参照 |

### ffmpeg のインストール

**Windows:**
1. `python download_ffmpeg.py` を実行して `ffmpeg.exe` を自動取得できます。
2. あるいは https://ffmpeg.org/download.html からダウンロードして、リポジトリルートに `ffmpeg.exe` を置くか、PATH に追加してください。

ビルド済みの Windows `.exe` は `ffmpeg.exe` を同梱できるようになっており、`dist/moby_rakuraku_downloader.exe` は単体で動作します。

**Mac:**
```bash
brew install ffmpeg
```

**Ubuntu / Linux:**
```bash
sudo apt install ffmpeg
```

`download_ffmpeg.py` は Windows / Linux / macOS のビルド向けに、最新の ffmpeg ビルドを自動で取得します。ソースから実行したい場合は、`ffmpeg` が PATH にある必要があります。

---

## セットアップ（開発者・ビルド担当者向け）

```bash
# 1. リポジトリをクローン
git clone https://github.com/xxx/moby_rakuraku_downloader
cd moby_rakuraku_downloader

# 2. 依存パッケージをインストール
pip install -r requirements.txt

# 3. ffmpeg を自動取得
python download_ffmpeg.py

# 4. .exe をビルド（Windows）
build.bat

# 4. バイナリをビルド（Mac / Linux）
bash build.sh
```

ビルド完了後、`dist/` フォルダに実行ファイルが生成されます。

`dist/moby_rakuraku_downloader.exe` / `dist/moby_rakuraku_downloader` は Python を内包した単体実行ファイルです。配布先ユーザーは Python の追加インストール不要で実行できます。

## 配布（デプロイ）

1. `main` ブランチを最新にしておく
2. 新しいタグを作成して GitHub にプッシュする

```bash
git tag v1.0.0
git push origin v1.0.0
```

3. GitHub Actions が `v*` タグのプッシュを検知してビルドを実行する
4. ビルドが完了すると GitHub Releases に `moby_rakuraku_downloader.exe` がアップロードされる
5. リリースページから `moby_rakuraku_downloader.exe` をダウンロードする

このリリース配布物は `ffmpeg` を同梱した単体実行ファイルです。
ユーザーは `.exe` をダブルクリックするだけで GUI が起動し、コマンドライン操作は不要です。

---

## 使い方

### .exe をダブルクリックして使う（友人向け・かんたん手順）

1. `moby_rakuraku_downloader.exe` をダブルクリック
2. GUI ウィンドウが開きます
3. SoundCloud のプレイリストURLを貼り付ける
4. 保存先を確認して「ダウンロード開始」をクリック
5. 進捗とログを見ながら待つ
6. 完了メッセージが出たらウィンドウを閉じてOK

### コマンドラインで使う（開発者向け）

```bash
# 基本実行（デフォルト保存先：~/Downloads/SoundCloud/）
python downloader.py https://soundcloud.com/user/sets/playlist-name

# 保存先を指定する場合
python downloader.py https://soundcloud.com/user/sets/playlist-name --output ~/Music/References
```

---

## 出力ファイル

実行後、以下の構造でファイルが保存されます：

```
~/Downloads/SoundCloud/
  └── {プレイリスト名}/
      ├── 01_artist name - song title.mp3
      ├── 02_artist name - song title.mp3
      ├── ...
      ├── metadata.json          ← プレイリスト・楽曲情報の記録
      └── download_report.txt    ← ダウンロード結果レポート
```

### download_report.txt の見方

```
[SUCCESS]  ダウンロード成功した曲数
[SKIPPED]  アーティストがDL不可に設定している曲（入手不可）
[ERROR]    ネットワーク等の一時的なエラーで失敗した曲（再実行で取得できる場合あり）
```

---

## トラブルシューティング

| 症状 | 原因 | 対処 |
|------|------|------|
| `ffmpeg が見つからない` と表示される | ffmpeg が未インストール | 上記の ffmpeg インストール手順を実行 |
| 曲が1曲もダウンロードされない | URLが間違っている可能性 | SoundCloud でプレイリストページを開き、URLをコピーし直す |
| 途中でエラーが出て止まった | ネットワーク接続の問題 | 再度 .exe を実行すると続きからではなく最初からになるが、すでにDL済みのファイルは上書きされる |

---

## ライセンス

個人利用・楽曲制作の参考用途に限り使用してください。
著作権で保護されたコンテンツのダウンロードは、各サービスの利用規約および著作権法に従って行ってください。
