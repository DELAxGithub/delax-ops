# Data Contract & Shared Logic

本書は Premiere 版／Resolve 版両方で共通となるデータ契約とタイムライン生成アルゴリズムを定義するものです。既存 GAS + Python の挙動を基準にしつつ、オフライン環境でも同じ結果を再現できることを前提とします。

## 1. CSV 契約

| 順序 | 列名            | 必須 | 説明 |
|------|-----------------|------|------|
| 1    | `Speaker Name`  | 任意 | 発話者ラベル（空欄可） |
| 2    | `イン点`         | 必須 | `HH:MM:SS:FF`（`;` も許容 → `:` に正規化）。テンプレの `rate.timebase` / `ntsc` に合わせてフレームへ換算 |
| 3    | `アウト点`       | 必須 | `HH:MM:SS:FF`。`in < out` が必須 |
| 4    | `文字起こし`     | 任意 | テロップ生成・診断ログ用に保持 |
| 5    | `色選択`         | 必須 | Premiere ラベル名（`Rose` / `Violet` …）。過去互換色（`pink`, `cyan` など）はマップで正規化 |

- 先頭行は **TARGET_HEADERS** に一致すること。
- CSV 文字コードは UTF-8（BOM 無し推奨）。
- 空行、未記入行はスキップ。`GAP_n` 行はギャップ専用データとして扱う。

### 1.1 ギャップ定義

- CSV で `色選択 = GAP_xx` が出現した場合、`イン点`／`アウト点` の差分をギャップ尺とする。
- ギャップの前後にはテンプレ定義の `gap_seconds`（もしくは `gap_frames`）を追加する。
- 任意で `文字起こし` をギャップテロップに流用可能（Premiere: Graphics / Resolve: Title）。

### 1.2 色マップ

```
Rose, Violet, Mango, Yellow, Lavender, Caribbean, Tan, Forest,
Blue, Purple, Teal, Brown, Gray, Iris, Cerulean, Magenta
```

- 上記が標準ラベル。レガシー色（`pink`, `cyan`, `mint` など）は同名に正規化。
- Premiere では `labels/label2` にセット。Resolve では Clip Color または Marker Color で意味等価に表現。

## 2. テンプレ宣言

テンプレ情報は YAML / JSON で管理し、Premiere/Resolve 両方が同一データを参照する。

項目例：

```yaml
id: "nhk_news_v1.2.0"
version: 1.2.0
fps:
  timebase: 24
  ntsc: true
tracks:
  video:
    - name: "V1"
      source: "0619_0727.MXF"
    - name: "V2"
      source: "C4170.MP4"
  audio:
    - name: "A1"
      source: "0619_0727.MXF"
      channel: 1
    - name: "A2"
      source: "0619_0727.MXF"
      channel: 2
    - name: "A5"
      source: "C4170.MP4"
      channel: 1
  gaps:
    default_seconds: 5
color_map:
  pink: Rose
  cyan: Caribbean
path_map:
  mac: "/Volumes/..."
  win: "\\\nas\..."
```

- `fps` から実 FPS を算出（例：`timebase=24`, `ntsc=true` → `23.976`）。
- `tracks.video[*].source` がテンプレ XML 内 `file/@id` または `masterclipid` に対応。
- `path_map` で UNC やドライブレターの差異を吸収（大文字・全角半角も正規化）。

## 3. タイムライン生成アルゴリズム

1. CSV を読み取り、色ごと連続区間をブロック化。
2. 各ブロックの `start_frames`, `end_frames` をテンプレ FPS に換算。
3. ブロックの前後に `gap_seconds` 相当の余白を追加し、テンプレートに沿った V/A トラックへ配置。
4. `label2` / Clip Color を色マップで設定。
5. `pproTicks` = `frames / fps * 254016000000` を計算し、Premiere XML / Resolve メタに書き込む。
6. `GAP_n` 行は尺分の空白クリップとし、必要に応じてテロップ（Premiere Graphics / Resolve Title）を配置。
7. 出力 XML は Premiere 用だが、Resolve でもインポート可能なことを確認済み（2025/02/XX 現状）。

## 4. プリフライト（共通）

- ヘッダー一致チェック（ズレがあれば候補提示 or エラー）。
- 時間コード逆転、フォーマットエラー、FPS 非対応を検出。
- 色名がマップ外の場合は警告（必要に応じて修正候補を提示）。
- `GAP_n` の `n` が未指定ならデフォルトギャップを採用。
- 入出力ファイルの SHA-256 を計測し、ジョブログに記録。

## 5. ログ出力フォーマット

- `job.json`: `csv_sha`, `template_version`, `nle_version`, `timeline_uuid`, `block_count`, `gap_count`, `warnings`, `errors`。
- `errors.csv`: 致命エラー行を抽出。
- `diag.zip`: 上記＋テンプレ宣言、環境情報をまとめて保存（オフライン保管 30 日目安）。

## 6. 互換性メモ

- 現行の Premiere 用 XML は Resolve でも問題なくインポートできているため、当面は同一 XML 生成に統一する。
- 将来 UXP や Resolve API の仕様が変わった場合、テンプレ宣言とプリフライトはこのドキュメントを改訂して更新する。

