# Orion Production Pipeline v2 - 設計仕様書

## 概要

調査結果（OrionEp11不整合分析）を踏まえた、堅牢な番組制作パイプライン。
番組シリーズ（Orion Ep7-12...）に対応する汎用的な制作ワークフローエンジン。

---

## 入出力仕様

### 📥 インプット（4種類）

#### 1. **脚本MD** - `orinonep{N}.md`
- **役割**: 番組の全体構成・演出指示・シーン区切り
- **形式**: Markdown（見出し、対話形式、YAML埋め込み可）
- **例**: `projects/OrionEp11/inputs/orinonep11.md`
- **特徴**:
  - `【00:00-01:00】アバン` などのシーン区切り
  - `上司（男声・真剣に）：` などの話者指定
  - `【テロップ】` などの演出指示

#### 2. **テロップ原稿SRT** - `ep{N}.srt`
- **役割**: 画面表示用字幕の確定文言（タイムコードは仮）
- **形式**: SubRip (.srt)
- **例**: `projects/OrionEp11/inputs/ep11.srt`
- **重要性**: ⭐⭐⭐ **信頼できる唯一の情報源（Single Source of Truth）**
- **特徴**:
  - 102エントリ（OrionEp11の場合）
  - 改行による2行表示字幕を含む
  - タイムコードは仮（00:00:00,000から順番）

#### 3. **ナレーション原稿** - `ep{N}nare.md` or `ep{N}nareyaml.yaml`
- **役割**: TTS読み上げ用のテキスト（1行1セグメント）
- **形式**: Markdown or YAML
- **例**:
  - `projects/OrionEp11/inputs/ep11nare.md`
  - `projects/OrionEp11/inputs/ep11nareyaml.yaml`
- **特徴**:
  - 話者（ナレーター/上司/内なる声）を指定
  - SSML的な間調整 `(間0.7)`
  - 95セグメント程度に統合済み

#### 4. **TTS調整YAML** - `orionep{N}_tts.yaml`
- **役割**: 音声合成の細かい調整（声・速度・ピッチ・プロンプト）
- **形式**: YAML
- **例**: `projects/OrionEp11/inputs/orionep11_tts.yaml`
- **設定項目**:
  - `voices`: 話者ごとの音声モデル・パラメータ
  - `gemini_dialogue`: Gemini TTS設定
  - `style_prompts`: 読み上げスタイル指示
  - `pronunciation_hints`: 読み仮名辞書

#### 5. **スクリプトCSV（オプショナル）** - `orionep{N}_script.csv`
- **役割**: セグメント単位のテキストオーバーライド
- **形式**: CSV (`no,text`)
- **用途**: TTSで読ませる文言を個別調整（ナレ原稿より優先）

---

### 📤 アウトプット

#### output/
1. **音声ファイル** - `audio/OrionEp{N}_001.mp3`, `_002.mp3`, ...
   - TTS合成された音声（セグメント単位）
   - 命名規則: `{project}_{連番3桁}.mp3`
   - 95ファイル程度

2. **タイムコードSRT** - `OrionEp{N}_timecode.srt`
   - 音声デュレーション + シーン切り替え間を反映したタイムコード付きSRT
   - エントリ数: 95（ナレ原稿と同じ）

3. **タイムラインCSV** - `OrionEp{N}_timeline.csv`
   - 編集用タイムライン情報
   - 列: Speaker Name, イン点, アウト点, 文字起こし, 色選択, filename, role, character, voice_direction, text, timeline_in, timeline_out, duration_sec, original_in, original_out

4. **タイムラインXML** - `OrionEp{N}_timeline.xml`
   - FCP7形式のXMLタイムライン（DaVinci Resolveインポート用）

#### exports/
1. **マージ済みSRT** - `orion_ep{N}_merged.srt`
   - テロップ原稿SRT（ep{N}.srt）+ タイムコードSRT（timecode.srt）のマージ
   - エントリ数: 183程度（改行分割により増加）
   - **問題**: 現状は不整合が発生している

2. **編集用XML** - `timelines/OrionEp{N}_timeline.xml`
   - exportsディレクトリ用のXMLコピー

---

## 現在の問題点（調査結果より）

### 🔴 Critical Issues

#### 1. **ソース選択の優先順位が不明瞭**
- `parse_script()` は ep{N}.srt（テロップ原稿）を解析せず、ep{N}nareyaml.yaml を優先解析
- **結果**: テロップ原稿が無視される

#### 2. **convert_pauses_to_text() による意図しない変質**
```python
# 問題のある処理
text = text.replace(" ", "")  # スペース削除 → 2文が連結
if text.endswith("か"):
    text += "？"  # 文末自動付与 → 意図しない疑問符化
```

#### 3. **_expand_subtitles() による過剰な分割**
- テロップ原稿の改行（2行表示用）を個別エントリに分割
- 102エントリ → 183エントリに増加

---

## v2設計方針

### 🎯 原則

1. **Single Source of Truth**: `ep{N}.srt`（テロップ原稿）を信頼できる唯一の情報源とする
2. **Immutable Text**: テキストの正規化・変換は最小限（スペース削除禁止）
3. **Explicit Configuration**: 暗黙的な挙動を排除、すべて設定ファイルで制御
4. **Fail Fast Validation**: 入力検証・出力検証を徹底、エラーは即座に報告

### 🏗️ アーキテクチャ

```
┌─────────────────┐
│  Input Layer    │  - Validator: 入力ファイルの構文・構造チェック
│  (Validation)   │  - Parser: SRT/MD/YAML/CSVパーサー
└────────┬────────┘
         │
┌────────▼────────┐
│  Core Pipeline  │  - Segment Manager: セグメント統合・分割ロジック
│  (Orchestrator) │  - TTS Engine: 音声合成オーケストレーター
│                 │  - Timeline Calculator: タイムコード計算
└────────┬────────┘
         │
┌────────▼────────┐
│  Output Layer   │  - Writer: SRT/CSV/XML出力
│  (Generation)   │  - Merger: SRTマージ処理
│                 │  - Validator: 出力一致性検証
└─────────────────┘
```

### 📋 処理フロー

```mermaid
flowchart TB
    subgraph Input["📥 Input Layer"]
        I1[ep{N}.srt<br/>テロップ原稿]
        I2[orinonep{N}.md<br/>脚本]
        I3[ep{N}nare.md<br/>ナレ原稿]
        I4[orionep{N}_tts.yaml<br/>TTS設定]
        I5[orionep{N}_script.csv<br/>オーバーライド]
    end

    subgraph Validation["🛡️ Validation"]
        V1[SRT構文検証]
        V2[YAML設定検証]
        V3[ファイル存在確認]
    end

    subgraph Core["⚙️ Core Pipeline"]
        C1[Segment Manager<br/>セグメント統合]
        C2[TTS Engine<br/>音声合成]
        C3[Timeline Calculator<br/>タイムコード計算]
    end

    subgraph Output["📤 Output Layer"]
        O1[audio/*.mp3<br/>音声ファイル]
        O2[timecode.srt<br/>タイムコード付きSRT]
        O3[timeline.csv<br/>タイムライン]
        O4[timeline.xml<br/>FCP7 XML]
    end

    subgraph Export["📦 Export Layer"]
        E1[merged.srt<br/>マージ済みSRT]
        E2[timelines/*.xml<br/>編集用XML]
    end

    I1 --> V1
    I2 --> V3
    I3 --> V3
    I4 --> V2
    I5 --> V3

    V1 --> C1
    V2 --> C1
    V3 --> C1

    C1 --> C2
    C2 --> C3

    C3 --> O1
    C3 --> O2
    C3 --> O3
    C3 --> O4

    I1 --> E1
    O2 --> E1
    O4 --> E2

    style I1 fill:#ff9999
    style C1 fill:#99ccff
    style E1 fill:#99ff99
```

---

## 新パイプラインの特徴

### ✅ 改善点

#### 1. **明示的なソース優先順位**
```yaml
source_priority:
  - ep{N}.srt           # テロップ原稿（最優先）
  - ep{N}nare.md        # ナレ原稿（セグメント化）
  - orionep{N}_script.csv  # オーバーライド
```

#### 2. **テキスト不変性の保証**
```python
# 禁止: スペース削除
# text = text.replace(" ", "")  # ❌

# 許可: SSMLタグ → 句読点変換のみ
text = PAUSE_PATTERN.sub(repl, raw)  # (間0.7) → 。
```

#### 3. **出力一致性検証**
```python
assert len(output_srt) == len(source_srt)  # エントリ数一致
assert text_similarity > 0.95  # テキスト類似度95%以上
```

#### 4. **デバッグ可能性**
- 各ステージの中間ファイル出力（`debug/`）
- 詳細ログ（処理時間、変換内容、検証結果）
- テスト用モックTTS（音声合成スキップ）

---

## プロジェクト構造（v2）

```
prototype/orion-v2/
├── pipeline/
│   ├── core.py              # メインオーケストレーター
│   ├── validator.py         # 入出力検証
│   ├── parsers/
│   │   ├── srt.py          # SRT専用パーサー
│   │   ├── markdown.py     # Markdown脚本パーサー
│   │   └── yaml_config.py  # TTS設定パーサー
│   ├── engines/
│   │   ├── tts.py          # TTS生成エンジン
│   │   └── timeline.py     # タイムコード計算
│   └── writers/
│       ├── srt.py          # SRT出力
│       ├── csv.py          # CSV出力
│       ├── xml.py          # FCP7 XML出力
│       └── merger.py       # SRTマージ処理
├── tests/
│   ├── test_pipeline.py
│   ├── test_validator.py
│   ├── test_parsers.py
│   └── fixtures/
│       └── OrionEp11/      # テストデータ
├── config/
│   ├── global.yaml         # グローバル設定
│   └── schema.yaml         # 設定スキーマ定義
├── projects/
│   └── OrionEp11/          # プロトタイプ用プロジェクト
│       ├── inputs/
│       │   ├── ep11.srt
│       │   ├── orinonep11.md
│       │   ├── ep11nare.md
│       │   └── orionep11_tts.yaml
│       ├── output/
│       │   ├── audio/
│       │   ├── OrionEp11_timecode.srt
│       │   ├── OrionEp11_timeline.csv
│       │   └── OrionEp11_timeline.xml
│       └── exports/
│           ├── orion_ep11_merged.srt
│           └── timelines/
├── DESIGN.md               # この設計書
├── MIGRATION.md            # 既存プロジェクトの移行ガイド
└── README.md               # 使い方
```

---

## 実装計画

### Phase 1: 基盤実装（1-2日）
- [ ] ディレクトリ構造作成
- [ ] Input Layer: SRT/YAML/Markdownパーサー
- [ ] Validator: 入力検証ロジック
- [ ] Core: Segment Manager基本実装

### Phase 2: コアパイプライン（2-3日）
- [ ] TTS Engine: OrionTTSGenerator統合
- [ ] Timeline Calculator: タイムコード計算
- [ ] Output Layer: SRT/CSV/XML Writer

### Phase 3: 統合テスト（1-2日）
- [ ] OrionEp11での完全テスト
- [ ] 出力一致性検証
- [ ] デバッグログ・エラーハンドリング

### Phase 4: ドキュメント・移行（1日）
- [ ] MIGRATION.md: 既存プロジェクト移行手順
- [ ] README.md: 使い方ガイド
- [ ] 旧実装のアーカイブ計画

---

## 検証基準

### ✅ 成功条件

1. **エントリ数一致**: `len(ep11.srt) == len(merged.srt)` (102エントリ)
2. **テキスト類似度**: `similarity(ep11.srt, merged.srt) > 0.95`
3. **音声ファイル数**: `len(audio/*.mp3) == len(segments)` (95ファイル)
4. **タイムコード連続性**: `srt[i].end_time == srt[i+1].start_time`
5. **XML妥当性**: DaVinci Resolveでインポート成功

### 🔍 検証ツール

```bash
# パイプライン実行
python3 pipeline/core.py --project OrionEp11

# 検証レポート生成
python3 pipeline/validator.py --project OrionEp11 --report

# 期待される出力:
# ✅ Input validation: PASS
# ✅ SRT entry count: 102 == 102
# ✅ Text similarity: 0.98 > 0.95
# ✅ Audio files: 95 == 95
# ✅ Timecode continuity: PASS
# ✅ XML validity: PASS
```

---

## 移行戦略

### 🔄 既存プロジェクトの扱い

1. **プロトタイプ検証後**:
   - `projects/OrionEp7-12/` を新構造に移行
   - 移行スクリプト: `scripts/migrate_project.py`

2. **旧実装のアーカイブ**:
   ```
   davinciauto/
   ├── archive/
   │   ├── old-scripts/
   │   │   ├── run_tts_pipeline.py
   │   │   ├── srt_merge.py
   │   │   └── orion_tts_generator.py
   │   └── old-projects/
   │       └── OrionEp7-12/
   └── orion-v2/          # 新実装
   ```

3. **新リポジトリへの移行**（オプション）:
   - プロトタイプ完成後
   - `orion-production-pipeline` リポジトリ作成
   - CI/CD整備

---

## 参考: 既存実装の問題分析

- 調査レポート: `docs/OrionEp11_Investigation_Report.md`
- データフロー図: `docs/diagrams/current_pipeline_flow.mermaid`
- 状態遷移図: `docs/diagrams/state_transition.puml`
