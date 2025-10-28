# SRT タイムコード再生成手順（新パイプライン対応版）

Orion Pipeline v2 で生成した音声ファイルに対し、正確なタイムコード付きSRTファイルを再生成する手順です。

**新パイプライン対応**:
- ✅ YAML narration優先読み込み (`ep{N}nare.yaml`)
- ✅ TimelineCalculator統合（29.97fps, 3.0s lead-in）
- ✅ AudioSegment + NarrationSegment連携

## 概要

### 問題の背景

- **元の問題**: YAMLナレーション台本とSRT字幕のテキスト不一致により、一部の字幕が未割り当てになる
- **解決策**: 音声ファイルの実尺に基づく比例配分アルゴリズム + フォールバック機構

### 新ロジックの特徴

1. **YAML優先読み込み**: `ep{N}nare.yaml` からナレーションセグメントを読み込み（Markdownにフォールバック可）
2. **TimelineCalculator統合**: 正しいFPS（29.97）とlead-in（3.0s）でタイムライン生成
3. **テキストマッチング**: YAMLナレーション台本とSRT字幕のテキストを突き合わせ
4. **音声尺ベース配分**: マッチングできなかった字幕を音声の長さに比例して配分
5. **最大剰余法**: 残りを公平に配り切る（各音声クリップに最低1字幕保証）

実装場所: `orion/pipeline/writers/srt.py`
- `_segment_durations()` (L74-80): 音声セグメント尺の計算
- `_distribute_counts_by_duration()` (L83-133): 比例配分ロジック
- フォールバック処理 (L239-269): 未割り当て字幕の補充

## 前提条件

### 必須ツール

```bash
# ffprobe（音声尺取得用）
brew install ffmpeg

# Python 3.11以上
python3 --version
```

### 必須ファイル

各エピソードのプロジェクトディレクトリに以下が必要：

```
orion/projects/OrionEpXX/
├── inputs/
│   ├── epXXnare.yaml        # ナレーションYAML（優先）
│   ├── EpXX.md              # ナレーション台本（YAMLない場合のフォールバック）
│   └── epXX.srt             # 元SRT（generated/teleop_raw.srt がない場合）
├── generated/
│   └── teleop_raw.srt       # プロンプト生成SRT（優先）
└── output/
    └── audio/
        ├── OrionEpXX_001.mp3
        ├── OrionEpXX_002.mp3
        └── ...              # すべての音声ファイル
```

## 再生成手順

### 基本的な使い方

```bash
# リポジトリルートで実行
python regenerate_srt_timecode.py OrionEp15
```

### 出力（新パイプライン版）

```
📖 Using generated SRT: orion/projects/OrionEp15/generated/teleop_raw.srt
📖 Loading subtitles from: orion/projects/OrionEp15/generated/teleop_raw.srt
✅ Loaded 105 subtitles
📄 Loading narration YAML: orion/projects/OrionEp15/inputs/ep15nare.yaml
✅ Loaded 70 narration segments from YAML

📂 Building audio segments from files...
✅ Built 70 audio segments

🔧 Calculating timeline (29.97 fps, 3.0s lead-in)...
✅ Timeline: 70 segments
⏱️  Total duration: 458.85s (7:38)

🔧 Generating timecode SRT...
  → Loaded 70 Nare lines from narration segments
  → Mapped 105 subtitles to 70 segments

✅ Complete: orion/projects/OrionEp15/output/OrionEp15_timecode.srt
📊 Subtitles: 105
📊 Audio segments: 70
⏱️  Total: 7:38
```

### ログの見方

| ログメッセージ | 意味 |
|--------------|------|
| `Loading narration YAML: ...` | YAML narration読み込み成功（優先） |
| `Loading narration Markdown: ...` | Markdown読み込み（YAMLがない場合） |
| `Calculating timeline (29.97 fps, 3.0s lead-in)` | TimelineCalculatorでタイムライン生成中 |
| `Loaded XX Nare lines from narration segments` | ナレーションセグメント読み込み成功 |
| `Text match covered XX/YY subtitles` | YY字幕中XX個がテキストマッチング成功 |
| `switching to sequential duration mapping` | 残りを音声尺ベースで配分 |
| `⚠️ XX subtitles unassigned...` | XX個の字幕をフォールバックで配分中 |
| `Mapped YY subtitles to ZZ segments` | 最終的にYY字幕がZZセグメントに配分完了 |

### 成果物

`orion/projects/OrionEpXX/output/OrionEpXX_timecode.srt`

- 各字幕エントリに実際の音声ファイル尺に基づく正確なタイムコードが付与
- DaVinci Resolve へのインポート準備完了

## 検証方法

### タイムコードの正確性確認

```bash
# 音声ファイル002の実尺を確認
ffprobe -v error -show_entries format=duration \
  -of default=noprint_wrappers=1:nokey=1 \
  orion/projects/OrionEp15/output/audio/OrionEp15_002.mp3
# 出力例: 5.765625

# SRTで該当区間を確認
grep -A 3 "^3$" orion/projects/OrionEp15/output/OrionEp15_timecode.srt
# 出力例:
# 3
# 00:00:06,505 --> 00:00:12,271
# 知識は光なのか
# それとも新たな闇を生むのか

# 計算: 12.271 - 6.505 = 5.766秒 ✅ 一致
```

### 総時間の確認

```bash
# SRTの最終エントリ
tail -5 orion/projects/OrionEp15/output/OrionEp15_timecode.srt

# 音声ファイル総時間
python3 << 'EOF'
from pathlib import Path
import subprocess
audio_dir = Path("orion/projects/OrionEp15/output/audio")
total = sum(
    float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(f)],
        capture_output=True, text=True
    ).stdout.strip())
    for f in sorted(audio_dir.glob("OrionEp15_*.mp3"))
)
print(f"{int(total//60)}:{int(total%60):02d}.{int((total%1)*1000):03d}")
EOF
```

## 他エピソードへの適用

### Ep14の例

```bash
python regenerate_srt_timecode.py OrionEp14
```

### 一括再生成

```bash
for ep in 13 14 15; do
  echo "Processing Episode $ep..."
  python regenerate_srt_timecode.py OrionEp$(printf "%02d" $ep)
done
```

## トラブルシューティング

### エラー: No source SRT found

**原因**: `generated/teleop_raw.srt` も `inputs/epXX.srt` も存在しない

**対処**:
1. Phase 0 でプロンプトベースSRT生成を実行
2. または既存のSRTファイルを `inputs/epXX.srt` に配置

### エラー: No audio files found

**原因**: `output/audio/` に音声ファイルがない

**対処**:
1. パイプラインでTTS生成を実行
2. または既存の音声ファイルを配置

### 警告: Narration markdown not found

**意味**: テキストマッチングができず、音声尺のみで配分

**対処**:
- テキストマッチングを使いたい場合は `inputs/EpXX.md` を配置
- 音声尺ベースのみで問題なければ無視してOK

### 字幕数とセグメント数の不一致

**正常動作**: 1音声セグメント = 1〜複数字幕

例: OrionEp15
- 音声セグメント: 70個
- SRT字幕: 105個
- 比率: 1.5字幕/セグメント

これは正常です。長いナレーションが複数行に分割されているためです。

## 仕様詳細

### 配分アルゴリズム（新パイプライン版）

1. **ナレーション読み込み**:
   - 優先: YAML narration (`ep{N}nare.yaml`) から NarrationSegment として読み込み
   - フォールバック: Markdown (`Ep{N}.md`) から解析

2. **タイムライン生成**:
   - TimelineCalculator使用（29.97fps, 3.0s lead-in）
   - AudioSegment と NarrationSegment を連携してタイムライン計算

3. **テキストマッチング** (優先):
   - ナレーションセグメントとSRT字幕のテキストを正規化して比較
   - 類似度の高いものを優先的にマッチング

4. **音声尺ベース配分** (フォールバック):
   - 各音声セグメントの長さを計算
   - 総字幕数を音声尺の比率で配分
   - 最大剰余法で端数を公平に配分
   - 各セグメントに最低1字幕を保証

5. **ラウンドロビン** (最終手段):
   - まだ残っている字幕を全セグメントに順番に配る

### タイムコード計算

各音声セグメント内で字幕を均等分散：

```
セグメント開始時刻 = 前セグメントの終了時刻
セグメント終了時刻 = 開始時刻 + 音声ファイル尺
字幕1開始 = セグメント開始時刻
字幕1終了 = 開始時刻 + (セグメント尺 / 字幕数)
字幕2開始 = 字幕1終了
...
```

## 参考情報

### 関連ファイル

- `regenerate_srt_timecode.py`: SRT再生成スクリプト（新パイプライン対応）
- `orion/pipeline/writers/srt.py`: SRT生成ロジック（比例配分 + フォールバック）
- `orion/pipeline/parsers/srt.py`: SRT解析
- `orion/pipeline/parsers/markdown.py`: Markdown/YAML台本解析
- `orion/pipeline/engines/timeline.py`: タイムライン計算
- `orion/pipeline/engines/tts.py`: AudioSegment定義

### 実装履歴

**Phase 1**: 比例配分ロジック実装
- 音声セグメント尺に基づく比例配分ヘルパー関数追加
- テキストマッチング失敗時のフォールバック機構
- 最大剰余法による公平な字幕配分

**Phase 2**: 新パイプライン統合（本バージョン）
- YAML narration優先読み込み (`parse_narration_yaml`)
- TimelineCalculator統合（29.97fps, 3.0s lead-in）
- AudioSegment + NarrationSegment連携
- `regenerate_srt_timecode.py` 完全リファクタリング

### 既知の制限

- YAMLナレーション台本に重複・分割がある場合、テキストマッチング精度が下がる
  → 音声尺ベースのフォールバックで補完
- 音声ファイル名は `{ProjectName}_001.mp3` 形式を前提
- ffprobeが必要（FFmpeg同梱）

### 新パイプライン対応状況

| 機能 | 対応状況 |
|------|---------|
| YAML narration読み込み | ✅ 完全対応 |
| Markdown fallback | ✅ 完全対応 |
| TimelineCalculator統合 | ✅ 完全対応 |
| AudioSegment生成 | ✅ 完全対応 |
| 比例配分アルゴリズム | ✅ 完全対応 |
| フォールバック機構 | ✅ 完全対応 |

**動作確認済みエピソード**:
- OrionEp13: 76セグメント → 76字幕（1対1マッピング）
- OrionEp15: 70セグメント → 105字幕（1.5倍マッピング）
