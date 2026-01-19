# Orion Pipeline v2

完全自動化された動画制作パイプライン for Orionシリーズ

## 概要

Orion Pipeline v2 は、スクリプトから DaVinci Resolve 用XMLまでを自動生成する動画制作パイプラインです。

**主な機能**:
- ✅ Gemini TTS による高品質音声生成
- ✅ 見出しマーカーによる自動ギャップ挿入
- ✅ 字幕とナレーションの自動マッピング
- ✅ FCP7 XML形式でのタイムライン出力
- ✅ エピソード番号指定による汎用化

## クイックスタート

事前に `ops/media/orion/` へ移動して実行します。

TTSだけ使う場合は `TTS_ONLY.md` を参照してください。
パイプラインを一発で回す場合は `PIPELINE_ONE_SHOT.md` を参照してください。

### 0. 脚本から下準備（フェーズ0）

```bash
# プロンプト生成（generated/ 以下に下書きを出力）
python pipeline/core.py --project OrionEp13 --generate-inputs
```

`projects/OrionEp13/generated/` に出力されるプロンプトを Sonnet 4.5 で処理し、
レビュー後に `--apply-generated-inputs` を付けて再実行すると `inputs/` へコピーされます。

```bash
python pipeline/core.py --project OrionEp13 --generate-inputs --apply-generated-inputs
```

### 1. 新しいエピソードの作成

```bash
# プロジェクトディレクトリ作成
mkdir -p projects/OrionEp13/{inputs,output/audio,exports}

# 必要なファイルを配置
# - inputs/ep13.srt
# - inputs/ep13nare.md
# - inputs/ep13nare.yaml
# - inputs/orinonep13.md
```

### 2. TTS音声生成

```bash
python generate_tts.py --episode 13 --delay 3.0
```

### 3. パイプライン実行

```bash
python pipeline/core.py --project OrionEp13
```

### 4. DaVinci Resolve インポート

**File → Import → Timeline → FCP7 XML** から `output/OrionEp13_timeline.xml` をインポート

---

## ディレクトリ構造

```
ops/media/orion/
├── README.md              # このファイル
├── WORKFLOW.md            # 完全ワークフローガイド
├── MODULES.md             # モジュール分割の方針
├── generate_tts.py        # 汎用TTS生成スクリプト
├── core/                  # パーサ/ライター/検証（API無し）
├── tts/                   # TTSエンジン（外部API境界）
├── pipeline/              # パイプラインオーケストレーター
│   ├── core.py
│   └── preprocess/
└── projects/              # エピソードごとのプロジェクト
    ├── OrionEp11/
    ├── OrionEp12/
    └── OrionEp13/
        ├── inputs/
        │   ├── ep13.srt
        │   ├── ep13nare.md
        │   ├── ep13nare.yaml
        │   └── orinonep13.md
        ├── generated/          # フェーズ0のプロンプト・下書き
        │   ├── prompts/
        │   └── status.json
        ├── output/
        │   ├── audio/
        │   ├── OrionEp13_timecode.srt
        │   ├── OrionEp13_timeline.csv
        │   └── OrionEp13_timeline.xml
        └── exports/
            └── orionep13_merged.srt
```

---
## モジュール分割について

オリオン系は「TTS」「字幕」「タイムライン生成」が混在しやすいため、保守性向上のため
段階的にモジュール分割を進める方針です。詳細は `MODULES.md` を参照してください。

---

## 入力ファイル

### `ep{N}.srt` - 字幕
標準SRT形式の字幕ファイル。複数行に分割可能。

### `ep{N}nare.md` - ナレーション原稿
1行 = 1音声ファイル。TTS生成の元テキスト。

### `ep{N}nare.yaml` - TTS設定
Gemini TTS の音声・スタイル・SSML設定。

```yaml
gemini_tts:
  segments:
    - speaker: ナレーター
      voice: kore
      text: "テキスト..."
      style_prompt: "スタイル指示..."
```
`segments` はトップレベルに置いても動作します（`gemini_tts.segments` と互換）。

### `orinonep{N}.md` - オリジナル脚本
見出しマーカー（`【HH:MM-HH:MM】セクション名`）で章立てを定義。

### `generated/` 以下のファイル
フェーズ0で生成されるプロンプトと下書き。レビュー後に `--apply-generated-inputs`
で `inputs/` へコピーします。

---

## 出力ファイル

### `OrionEp{N}_timecode.srt`
タイムコード付き字幕（音声タイミングに完全一致）

### `OrionEp{N}_timeline.csv`
タイムライン詳細（デバッグ用）

| index | audio_filename | duration_sec | start_timecode | end_timecode | is_scene_start | scene_lead_in_sec |
|-------|----------------|--------------|----------------|--------------|----------------|-------------------|
| 1     | OrionEp12_001.mp3 | 4.12 | 00:00:00:00 | 00:00:04:03 | NO | 0.00 |
| 11    | OrionEp12_011.mp3 | 6.81 | 00:01:04:03 | 00:01:11:04 | YES | 3.00 |

### `OrionEp{N}_timeline.xml`
DaVinci Resolve インポート用 FCP7 XML

---

## 主要機能

### 1. 見出しマーカーによる自動ギャップ

`orinonep{N}.md` の見出し（`【HH:MM-HH:MM】`）を自動検出し、該当位置に3秒ギャップを挿入。

**例**:
```markdown
【00:00-00:30】アバン
...

【00:30-01:30】日常への没入  ← ここで3秒ギャップ
...
```

### 2. 字幕とナレーションの自動マッピング

ナレーション原稿（`ep{N}nare.md`）と字幕（`ep{N}.srt`）をテキストマッチングで自動マッピング。

- 99字幕 → 80音声 のような不一致も自動処理
- 1音声に複数字幕を割り当て可能

### 3. Gemini TTS 統合

Google の Gemini TTS API を使用した高品質音声生成。

**対応音声**:
- `kore`, `aoede`, `charon`, `fenrir`, `puck`, `coral` など

**SSML対応**:
- `<sub alias='読み方'>表記</sub>` - 読み方指定
- `<break time='600ms'/>` - ポーズ挿入

---

## トラブルシューティング

### TTS生成が失敗する

**原因**: Gemini API Key未設定

**解決**:
```bash
# .env に追加
GEMINI_API_KEY=your_api_key_here
GEMINI_API_KEY_1=your_api_key_here  # optional: rotate keys on quota
GEMINI_API_KEY_2=your_api_key_here
GEMINI_API_KEY_3=your_api_key_here
```

### 字幕タイミングがズレる

**原因**: Nare原稿と字幕のマッピングミス

**解決**:
1. `ep{N}nare.md` の行数を確認
2. `ep{N}nare.yaml` のセグメント数が一致するか確認
3. パイプライン再実行

### XMLインポートエラー

**原因**: 音声ファイルパスが不正

**解決**: パイプライン実行時に `output/audio/` に音声ファイルが存在することを確認

---

## 開発者向け

### パイプラインアーキテクチャ

```
core.py
├── parsers/      # 入力ファイル解析
│   ├── srt.py
│   └── markdown.py
├── engines/      # コア処理
│   ├── tts.py
│   └── timeline.py
└── writers/      # 出力ファイル生成
    ├── srt.py
    ├── csv.py
    └── xml.py
```

### 拡張方法

**新しいTTSエンジン追加**:
1. `engines/tts.py` に新しいエンジンクラスを追加
2. `generate_tts.py` で切り替えロジックを実装

**新しい出力形式追加**:
1. `writers/` に新しいライターを追加
2. `core.py` の Phase 5 で呼び出し

---

## ライセンス

内部プロジェクト用

---

## 関連ドキュメント

- [WORKFLOW.md](WORKFLOW.md) - 完全ワークフローガイド
- [SRT_TIMECODE_REGENERATION.md](SRT_TIMECODE_REGENERATION.md) - SRTタイムコード再生成手順
- [引き継ぎ.md](../../引き継ぎ.md) - プロジェクト全体の引き継ぎ資料

---

## SRTタイムコード再生成

音声ファイルに基づいて正確なタイムコード付きSRTを生成：

```bash
# リポジトリルートで実行
python regenerate_srt_timecode.py OrionEp15
```

詳細は [SRT_TIMECODE_REGENERATION.md](SRT_TIMECODE_REGENERATION.md) を参照してください。

---

**最終更新**: 2025-10-24
