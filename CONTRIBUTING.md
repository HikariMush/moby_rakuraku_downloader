# Contributing Guidelines

このリポジトリで開発を行う場合は、以下のルールに従ってください。

## 目的

- リリース時に `README` のリンクを必ず含める
- 追加された機能を `RELEASE_NOTES.md` に記載する
- リリース本文を GitHub Actions で自動生成させる
- 著作権と利用規約の遵守に十分留意し、ドキュメントに明示する

## 開発フロー

1. 変更内容を実装
2. `RELEASE_NOTES.md` の `### 新機能` セクションに追加内容を追記
3. 必要に応じて `README_BEGINNER.md` / `README_DEVELOPER.md` を更新
4. `main` ブランチにマージする前に以下を確認
   - `RELEASE_NOTES.md` が最新である
   - ドキュメントに必要な説明が追加されている
   - `README_DEVELOPER.md` にリリース手順が記載されている

## リリースルール

- タグは `vX.Y.Z` の形式で作成する
- タグをリモートにプッシュすると GitHub Actions がリリースを自動生成する
- 自動生成されるリリース本文には以下を含める
  - `README_BEGINNER.md` へのリンク
  - `README_DEVELOPER.md` へのリンク
  - `RELEASE_NOTES.md` の `### 新機能` セクション

## 仕組み

- `.github/workflows/build.yml` で `v*` タグのプッシュをトリガーにビルド・リリースを実行
- リリース本文は `release_body.md` を生成して作成される
- 追加機能は `RELEASE_NOTES.md` から自動抽出される

## PR 作成時のチェックリスト

- [ ] `RELEASE_NOTES.md` を更新した
- [ ] 新機能や変更点を正しく記載した
- [ ] 必要なら `README_BEGINNER.md` / `README_DEVELOPER.md` を更新した
- [ ] 著作権と利用規約の注意事項をドキュメントに含めた
- [ ] GitHub Actions によるリリース自動化の仕組みに問題がないか確認した
