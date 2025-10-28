# Premiere Auto-Cut Workspace

Premiere Pro の自動粗編集ワークフローを `premiere/` 以下に集約しました。`orion/` フォルダと同様に、仕様・ツール・エピソード素材をひとつのルートで完結させることを目的としています。

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
├── projects/                 # エピソード別素材（022, 024, young01 など）
│   └── <episode_id>/
│       ├── inputs/           # テンプレート XML / 最終指示 CSV など
│       └── outputs/          # 生成された FCPXML 等
└── tools/
    └── autocut/              # Google Sheets GAS と Python ツール群
```

## クイックスタート

1. Premiere からテンプレート XML と文字起こし CSV を書き出し、`premiere/projects/<episode_id>/inputs/` に配置する。  
2. Google Sheets 用スクリプト `premiere/tools/autocut/csv_premiere.js` を使って、最終 CSV を整形・抽出する。  
3. ターミナルで
   ```bash
   python premiere/tools/autocut/csv_xml_cutter.py \
       premiere/projects/<episode_id>/inputs/final.csv \
       premiere/projects/<episode_id>/inputs/template.xml
   ```
   を実行し、Premiere インポート用の FCPXML を生成する。  
4. 生成物は `premiere/projects/<episode_id>/outputs/` に保存し、Premiere へ読み込む。

詳細な進捗メモや運用ルールは `premiere/docs/autocut_progress.md` を参照してください。

