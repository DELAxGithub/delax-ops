# Orion v2 Pipeline - 別Mac移植ガイド

## 概要

Orion v2パイプラインを別のMacで使用するための完全ガイドです。

**実測値**:
- パイプライン全体（プロジェクト含む）: **5.5MB**（zip圧縮後）
- 展開後のディレクトリサイズ: **11MB**

---

## パターンA: パイプラインのみ移植（新規プロジェクト用）

### 必要なファイル

```
orion/
├── generate_tts.py                    # TTS生成スクリプト
├── core/                              # パーサ/ライター/検証（API無し）
│   ├── validator.py
│   ├── mapper.py
│   ├── timeline.py
│   ├── parsers/
│   │   ├── markdown.py
│   │   └── srt.py
│   └── writers/
│       ├── csv.py
│       ├── srt.py
│       └── xml.py
├── tts/                               # TTSエンジン（外部API境界）
│   ├── tts.py
│   ├── tts_config_loader.py
│   ├── orion_tts_generator.py
│   └── orion_ssml_builder.py
├── pipeline/                          # パイプラインオーケストレーター
│   ├── core.py
│   └── preprocess/
├── config/
│   └── global.yaml                    # グローバル設定
├── README.md                          # 使い方
├── WORKFLOW.md                        # ワークフローガイド
└── projects/                          # 空ディレクトリ（新規作成）
```

**サイズ**: 約150KB（Pythonコード + ドキュメント）

---

## パターンB: 既存プロジェクト含めて移植（作業続行）

### 必要なファイル

パターンAの全ファイル ＋ 以下：

```
orion/projects/OrionEp01/
├── inputs/
│   ├── ep1.srt                       # 字幕（必須）
│   ├── ep1nare.md                    # ナレーション原稿（必須）
│   ├── ep1nare.yaml                  # TTS設定（必須）
│   └── orinonep1.md                  # オリジナル脚本（見出しマーカー用）
├── output/
│   └── audio/
│       ├── OrionEp01_001.mp3        # 生成済み音声（93ファイル）
│       ├── OrionEp01_002.mp3
│       └── ... (全93ファイル)
└── exports/                          # パイプライン出力用（空）
```

**サイズ**:
- パイプラインコア: ~150KB
- プロジェクト入力: ~50KB
- 生成済み音声: ~5MB（93ファイル）
- **合計**: ~5.2MB（zip圧縮後: 5.5MB）

---

## 不要なファイル（移植しない）

```
❌ orion/test_*.py                    # テストファイル
❌ orion/__pycache__/                 # Pythonキャッシュ
❌ orion/projects/OrionEp11/          # 他のエピソード
❌ orion/projects/OrionEp12/          # 他のエピソード
❌ orion/DESIGN.md                    # 開発用ドキュメント
❌ orion/STATUS.md                    # 開発ステータス
```

---

## 環境構築手順（移植先Mac）

### 1. ディレクトリ作成
```bash
mkdir -p ~/orion-pipeline
cd ~/orion-pipeline
```

### 2. ファイル転送

**方法1: rsyncで転送（ネットワーク経由）**
```bash
# 転送元Macで実行
rsync -avz --exclude='__pycache__' \
  --exclude='test_*.py' \
  --exclude='OrionEp11' \
  --exclude='OrionEp12' \
  orion/ user@target-mac:~/orion-pipeline/orion/
```

**方法2: zipで転送（USB/AirDrop）**
```bash
# 転送元Macで実行
cd /path/to/davinciauto
zip -r orion-pipeline.zip orion/ \
  -x "orion/__pycache__/*" \
  -x "orion/*/*/__pycache__/*" \
  -x "orion/*/*/*/__pycache__/*" \
  -x "orion/test_*.py" \
  -x "orion/projects/OrionEp11/*" \
  -x "orion/projects/OrionEp12/*" \
  -x "orion/DESIGN.md" \
  -x "orion/STATUS.md"

# 転送先Macで実行
unzip orion-pipeline.zip
```

**方法3: Gitで管理（推奨）**
```bash
# 転送元Macで実行
cd /path/to/davinciauto
git add orion/
git commit -m "Add Orion v2 pipeline"
git push

# 転送先Macで実行
git clone <repository-url>
cd davinciauto
```

### 3. Python環境構築
```bash
# Python 3.11以上推奨
python3 --version

# 仮想環境作成
python3 -m venv .venv
source .venv/bin/activate

# 依存パッケージインストール
pip install google-cloud-texttospeech pyyaml
```

### 4. 環境変数設定
```bash
# .envファイル作成（orion/ ディレクトリ内）
cat << 'ENV' > orion/.env
GEMINI_API_KEY=your_api_key_here
GEMINI_API_KEY_1=your_api_key_here  # optional: rotate keys on quota
GEMINI_API_KEY_2=your_api_key_here
GEMINI_API_KEY_3=your_api_key_here
ENV

# または直接exportで設定
export GEMINI_API_KEY="your_api_key_here"
export GEMINI_API_KEY_1="your_api_key_here"
export GEMINI_API_KEY_2="your_api_key_here"
export GEMINI_API_KEY_3="your_api_key_here"
```

### 5. 動作確認
```bash
# TTS生成テスト（3セグメントのみ）
cd ~/orion-pipeline
python orion/generate_tts.py --episode 1 --limit 3

# パイプライン実行テスト
python orion/pipeline/core.py --project OrionEp01
```

---

## 新規エピソード作成手順

別のMacで新しいエピソードを作成する場合：

```bash
# プロジェクトディレクトリ作成
mkdir -p orion/projects/OrionEp02/{inputs,output/audio,exports}

# 入力ファイルを配置
cd orion/projects/OrionEp02/inputs/
# 以下の4ファイルを作成・配置:
# - ep2.srt              （字幕）
# - ep2nare.md           （ナレーション原稿：1行=1音声）
# - ep2nare.yaml         （Gemini TTS設定）
# - orinonep2.md         （オリジナル脚本：見出しマーカー用）

# TTS生成実行
cd ~/orion-pipeline
python orion/generate_tts.py --episode 2 --delay 3.0

# パイプライン実行
python orion/pipeline/core.py --project OrionEp02
```

---

## 最小構成（パイプラインのみ）

新規プロジェクトで使う場合、以下で十分：

```
orion/
├── generate_tts.py       (~7KB)
├── pipeline/             (~90KB)
├── config/global.yaml    (~2KB)
├── README.md             (~6KB)
├── WORKFLOW.md           (~12KB)
└── projects/             (空ディレクトリ)
```

**合計**: **~120KB**

---

## ファイルサイズ早見表

| 項目 | サイズ |
|------|--------|
| パイプラインコア（Pythonコード） | ~90KB |
| ドキュメント（README + WORKFLOW） | ~30KB |
| 設定ファイル（config/global.yaml） | ~2KB |
| プロジェクト入力ファイル（4ファイル） | ~50KB |
| 生成済み音声（93ファイル） | ~5MB |
| **最小構成合計** | **~120KB** |
| **プロジェクト含む合計（圧縮前）** | **~5.2MB** |
| **プロジェクト含む合計（zip圧縮後）** | **~5.5MB** |

---

## 依存パッケージ

### 必須
- `google-cloud-texttospeech` - Gemini TTS API
- `pyyaml` - YAML設定ファイル解析

### オプション
- `ffprobe` - 音声ファイルのメタデータ取得（システムツール）

### インストール
```bash
pip install google-cloud-texttospeech pyyaml
```

---

## トラブルシューティング

### TTS生成が失敗する
**原因**: Gemini API Key未設定

**解決**:
```bash
# 環境変数を確認
echo $GEMINI_API_KEY
echo $GEMINI_API_KEY_1

# .envファイルを確認
cat orion/.env

# 正しく設定
export GEMINI_API_KEY="your_actual_api_key"
export GEMINI_API_KEY_1="your_actual_api_key"
```

### パイプライン実行時にモジュールが見つからない
**原因**: PYTHONPATHが未設定

**解決**:
```bash
# PYTHONPATHを明示的に指定
python orion/pipeline/core.py --project OrionEp01
```

### 音声ファイルが見つからない
**原因**: プロジェクトディレクトリのパスが違う

**解決**:
```bash
# プロジェクトディレクトリを確認
ls -la orion/projects/

# generate_tts.pyの実行ディレクトリを確認
pwd
# → /path/to/orion-pipeline であることを確認
```

---

## まとめ

**別のMacで使うために渡すべきファイル**:

1. **最小構成**: `orion/`ディレクトリ全体（約120KB）
   - 新規プロジェクトで使う場合

2. **プロジェクト含む**: `orion/`ディレクトリ全体（約5.5MB zip圧縮後）
   - 既存の作業を続行する場合

**推奨転送方法**:
- Gitリポジトリで管理（バージョン管理も可能）
- zip圧縮してAirDrop/USB転送

**セットアップ時間**: 約5分
1. ファイル転送: 1分
2. Python環境構築: 2分
3. 環境変数設定: 1分
4. 動作確認: 1分

---

**最終更新**: 2025-10-18
