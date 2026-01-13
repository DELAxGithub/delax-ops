# Premiere Auto-Cut Workspace

Premiere Pro の自動粗編集ワークフローを `premiere/` 以下に集約しました。
このモジュールは **独立ツールとして固定** し、実データや素材は別リポで管理します。

## ディレクトリ構成

```
premiere/
├── README.md                 # 本ファイル
├── docs/                     # AutoCut の背景資料・運用メモ
├── nle_autoedit/             # CSV→FCPXML コアロジックと仕様
│   ├── common/               # 共有 Python モジュール
│   ├── specs/                # Premiere / Resolve 共通仕様
│   ├── premiere/             # Premiere パネル実装枠
│   └── resolve/              # Resolve スクリプト実装枠
└── tools/
    └── autocut/              # Google Sheets GAS と Python ツール群
```

## クイックスタート

1. Premiere からテンプレート XML と文字起こし CSV を書き出す。  
2. Google Sheets 用スクリプト `premiere/tools/autocut/csv_premiere.js` を使って、最終 CSV を整形・抽出する。  
3. ターミナルで
   ```bash
   python premiere/tools/autocut/csv_xml_cutter.py \
       /path/to/final.csv \
       /path/to/template.xml
   ```
   を実行し、Premiere インポート用の FCPXML を生成する。  
4. 生成物を Premiere へ読み込む。

詳細な進捗メモや運用ルールは `premiere/docs/autocut_progress.md` を参照してください。
