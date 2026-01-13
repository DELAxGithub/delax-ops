# Orion Pipeline v2 - 進捗状況

## 📊 現在の状態

**Phase**: MVP実装フェーズ（Phase 1-5 完了）

### ✅ 完了タスク

1. **調査フェーズ** (完了)
   - OrionEp11 不整合の根本原因特定
   - データフロー図・状態遷移図作成
   - 3段階の変質プロセス分析完了

2. **設計フェーズ** (完了)
   - `DESIGN.md` - 詳細設計仕様書作成
   - `README.md` - ユーザーガイド作成
   - `config/global.yaml` - グローバル設定作成
   - プロトタイプディレクトリ構造構築

3. **MVP Phase 1-5 実装** (完了)
   - `core/parsers/srt.py` - SRTパーサー & バリデーション ✅
   - `core/parsers/markdown.py` - Markdownナレ原稿パーサー ✅
   - `core/validator.py` - 入力・出力検証ロジック ✅
   - `pipeline/core.py` - メインオーケストレーター（Phase 1-5） ✅
   - `core/tts.py` - TTS生成エンジン（既存音声再利用） ✅
   - `core/timeline.py` - タイムライン計算エンジン（NTSC 29.97fps） ✅
   - `core/mapper.py` - 音声-字幕マッピング（文字数比按分） ✅
   - `core/writers/srt.py` - タイムコードSRT & マージSRT出力 ✅
   - `core/writers/csv.py` - タイムラインCSV出力 ✅
   - `core/writers/xml.py` - FCP7 XML出力（DaVinci Resolve対応） ✅
   - OrionEp11での動作確認: 85音声→102字幕マッピング、509.7秒、全出力生成 ✅

### 🚧 進行中タスク

- **Phase 6実装とドキュメント整備**

### 📅 次のステップ

1. **Phase 6: 出力検証実装** (0.5日)
   - [ ] `core.py` Phase 6 実装 - 出力ファイル検証
   - [ ] エントリ数一致確認（±5%許容）
   - [ ] テキスト類似度確認（>95%）

2. **テスト** (0.5日)
   - [ ] `tests/test_pipeline.py` - 統合テスト
   - [ ] OrionEp11での完全検証
   - [ ] 出力一致性確認

3. **ドキュメント** (0.5日)
   - [ ] `MIGRATION.md` - 既存プロジェクト移行手順
   - [ ] 旧実装のアーカイブ計画

---

## 🎯 成功基準

### 検証項目

| 項目 | 現状 | 目標 | 状態 |
|------|------|------|------|
| エントリ数一致 | 102 → 183 (79%増加) | 102 → 102 (±5%) | 🚧 |
| テキスト類似度 | 不明 | > 95% | 🚧 |
| 音声ファイル数 | 85/85 (既存再利用) | 85/85 | ✅ |
| パイプライン実行 | Phase 1-3 成功 | Phase 1-6 成功 + 検証 | 🚧 |
| 音声総尺 | 509.7秒 (8.5分) | - | ✅ |

### 期待される改善

1. **ep{N}.srt（テロップ原稿）の完全反映**
   - 現状: 無視される → 改善: 最優先ソース

2. **テキスト変質の排除**
   - 現状: スペース削除・文末付与 → 改善: テキスト不変

3. **SRTエントリ数の保持**
   - 現状: 102 → 183 → 改善: 102 → 102

---

## 📦 ファイル構成

```
ops/media/orion/
├── DESIGN.md           ✅ 設計仕様書
├── README.md           ✅ ユーザーガイド
├── STATUS.md           ✅ このファイル
├── MIGRATION.md        ⏳ 未作成
├── config/
│   └── global.yaml     ✅ グローバル設定
├── core/
│   ├── validator.py    ✅ 入力・出力検証実装
│   ├── mapper.py       ✅ 音声-字幕マッピング実装
│   ├── timeline.py     ✅ タイムライン計算実装
│   ├── parsers/
│   │   ├── srt.py       ✅ SRTパーサー実装
│   │   └── markdown.py  ✅ Markdownパーサー実装
│   └── writers/
│       ├── srt.py       ✅ タイムコードSRT & マージSRT出力
│       ├── csv.py       ✅ タイムラインCSV出力
│       └── xml.py       ✅ FCP7 XML出力
├── tts/
│   ├── tts.py           ✅ TTS生成（既存音声再利用）実装
│   ├── tts_config_loader.py
│   ├── orion_tts_generator.py
│   └── orion_ssml_builder.py
├── pipeline/
│   ├── core.py         ✅ Phase 1-5 実装完了
│   └── preprocess/
├── tests/              ⏳ 未実装
└── projects/
    └── OrionEp11/      ✅ 入力ファイル配置済み
```

---

## 🔄 実装方針

### Phase 1: Minimum Viable Pipeline (MVP)

**目標**: OrionEp11で動作する最小限のパイプライン

**実装優先度**:
1. SRTパーサー（テロップ原稿読み込み）
2. TTS生成（既存OrionTTSGenerator統合）
3. タイムコード計算（既存ロジック流用）
4. SRT出力（シンプルな出力）

**スキップ項目** (MVP後):
- XMLWriter（既存実装流用）
- CSVWriter（既存実装流用）
- SRTマージャー（既存実装流用）

### Phase 2: Validation & Robustness

**目標**: 入出力検証の完全実装

**実装項目**:
- 入力ファイルのスキーマ検証
- 出力一致性チェック
- エラーハンドリング・リトライロジック

### Phase 3: Migration & Documentation

**目標**: 既存プロジェクトの移行とドキュメント整備

**実装項目**:
- 移行スクリプト作成
- 既存Ep7-12の移行テスト
- ユーザードキュメント完成

---

## 💬 意思決定記録

### 設計判断

#### Q: なぜ既存パイプラインを完全リファクタリング？
**A**: 調査結果により、以下の根本的な問題が判明：
- ソース選択の優先順位が不明瞭（ep{N}.srtが無視される）
- convert_pauses_to_text()の意図しない変質（スペース削除・文末付与）
- _expand_subtitles()の過剰な分割（102 → 183エントリ）

**結論**: 部分修正では解決困難。Single Source of Truth原則に基づく再設計が必要。

#### Q: なぜep{N}.srtを最優先ソースに？
**A**:
- テロップは最終成果物として画面に表示される
- 人間が最後に確認・編集する唯一のファイル
- ナレ原稿は音声生成用の派生データ

**結論**: ep{N}.srtを「信頼できる唯一の情報源」とする。

#### Q: なぜプロトタイプをこのリポジトリ内に？
**A**:
- 既存実装との比較検証が容易
- テストデータ（OrionEp11）が既に存在
- 完成後に新リポジトリへ移行可能

**結論**: `prototype/orion-v2/`で開発 → 完成後に新リポジトリへ移行。

---

## 🚀 次回作業内容

### 優先度1（即着手）

```bash
# 1. SRTパーサー実装
vim core/parsers/srt.py

# 2. バリデーター実装
vim core/validator.py

# 3. コアパイプライン骨格作成
vim pipeline/core.py
```

### 実装順序

1. **core/parsers/srt.py**
   - parse_srt() 関数（既存srt_merge.pyから流用）
   - Subtitle dataclass定義
   - SRT構文検証

2. **core/validator.py**
   - validate_srt() - SRT構文・構造チェック
   - validate_output() - 出力一致性チェック

3. **pipeline/core.py**
   - PipelineContext dataclass（既存run_tts_pipeline.pyから流用）
   - main() オーケストレーター骨格

---

## 📝 メモ

### 調査で判明した重要な知見

1. **ep{N}.srt は解析されていない**
   - parse_script() は ep{N}nareyaml.yaml を優先解析
   - ep{N}.srt は merge_srt_files() で初めて登場

2. **convert_pauses_to_text() がテキストを変質させる**
   - スペース削除: `text.replace(" ", "")`
   - 文末付与: `if text.endswith("か"): text += "？"`

3. **_expand_subtitles() が改行で分割**
   - 2行字幕 → 2個のSubtitleエントリ
   - 102エントリ → 183エントリに増加

### 教訓

- **暗黙的な挙動は排除すべき**: 設定ファイルで明示的に制御
- **Single Source of Truthの重要性**: 複数の"原稿"が存在するとコンフリクト
- **出力検証の必要性**: パイプライン実行だけでは不整合に気づけない

---

## 🔗 関連リンク

- [調査レポート](../../docs/OrionEp11_Investigation_Report.md) - 問題分析詳細
- [既存パイプライン](../../scripts/run_tts_pipeline.py) - 既存実装
- [既存マージロジック](../../scripts/srt_merge.py) - 既存SRTマージ

---

最終更新: 2025-10-16
