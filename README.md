# 🎵 moby_rakuraku_downloader

SoundCloud のプレイリストURLを渡すだけで、ダウンロード可能な楽曲を自動判定して MP3 で一括保存するツールです。

---

## 必要なもの

| ツール | バージョン | 入手先 |
|--------|-----------|--------|
| Python | 3.10 以上 | https://www.python.org/downloads/ |
| ffmpeg | 最新版 | 下記参照 |

### ffmpeg のインストール

**Windows:**
1. https://ffmpeg.org/download.html からダウンロード
2. `ffmpeg.exe` を `moby_rakuraku_downloader.exe` と同じフォルダに置く

**Mac:**
```bash
brew install ffmpeg
```

**Ubuntu / Linux:**
```bash
sudo apt install ffmpeg
```

---

## セットアップ（開発者・ビルド担当者向け）

```bash
# 1. リポジトリをクローン
git clone https://github.com/xxx/moby_rakuraku_downloader
cd moby_rakuraku_downloader

# 2. 依存パッケージをインストール
pip install -r requirements.txt

# 3. .exe をビルド（Windows）
build.bat

# 3. バイナリをビルド（Mac / Linux）
bash build.sh
```

ビルド完了後、`dist/` フォルダに実行ファイルが生成されます。

---

## 使い方

### .exe をダブルクリックして使う（友人向け・かんたん手順）

1. `moby_rakuraku_downloader.exe` をダブルクリック
2. 黒いターミナル画面が開く
3. SoundCloud のプレイリストURLを貼り付けて **Enter**
4. 自動でダウンロードが始まる
5. 完了したらターミナルを閉じてOK

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
