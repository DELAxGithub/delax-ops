# Premiere Panel Specification (CEP → UXP Migration Ready)

## 0. Summary

CSV（GAS出力互換）とテンプレ XML/YAML から Premiere シーケンスを自動再構築するパネル。ネット遮断・ユーザー権限環境でも導入できるよう、署名付き ZXP とオフラインツールチェーンを提供する。

Resolve でも同じ XML が取り込めることが確認できているため、Premiere 向け生成を基準にする。

## 1. 配布・導入

- 形式：署名済み ZXP + オフライン `ExManCmd` スクリプト一式。
- 導入手順
  1. ZIP を NAS からコピー。
  2. `install.sh`（mac）または `install.bat`（Win）をユーザー権限で実行。
  3. 成功時に `logs/install_*.txt` を出力。
- 監査用：ZXP の署名情報と SHA-256 ハッシュを `docs/rfi/` に同梱。

## 2. パネル UI フロー

1. **CSV ドロップエリア**
   - 拡張子/文字コード/ヘッダー検査。
   - OK → `プリフライト` ボタン活性。
2. **プリフライト結果**
   - `OK / Warning / Error` で表示。
   - 警告：色マップ補正、GAP デフォルト適用など。
   - エラー：欠損、時間逆転、FPS 非対応 → `errors.csv` を即時出力。
3. **テンプレ選択**
   - `templates/premiere/*.yaml` を一覧表示。
   - 各テンプレは `id`, `version`, `fps`, `track_map`, `gap_seconds` などを持つ。
4. **オプション**（折り畳み）
   - ギャップ秒数の上書き。
   - テロップ用グラフィックテンプレの追加（任意）。
5. **生成**
   - テンプレ XML を読み込み → ブロック配置 → 新シーケンス生成。
   - 完了後、シーケンスをアクティブ化。
6. **診断パネル**
   - `job.json` の内容を表示。
   - `diag.zip` へのリンク（CSV・テンプレ・ログを同梱）。

## 3. 技術構成

- **Runtime**：CEP (TypeScript + React-lite) → 将来 UXP への移行を見据えて WebView DOM 依存を最低限に。
- **Core Logic**：タイムライン構築は `common/` で TypeScript 実装。テンプレ読み込み → ブロック分割 → XML 生成。
- **XML Writer**：現行 Python の出力に合わせ、`pproTicks` や `label2` を正確に書き込む。Resolve でも利用できるよう現行フォーマットを踏襲。
- **プリフライト**：`common/data_contract.md` のルールに準拠。CSV → JSON 変換 → バリデーション。
- **ログ**：`job.json` / `errors.csv` / `diag.zip` を `project_root/_autoedit_logs/<date>/` に保存。

## 4. 主要ユースケース

| シナリオ | 入力 | 出力 |
|----------|------|------|
| ニュース尺の一括編集 | GAS から出力されたリスト（色分け済み） | シーケンス（ラベル・ギャップ付き） |
| 再編集 | 既存 CSV + 新テンプレ (v1→v2) | 新シーケンス。旧バージョンとの差分は `job.json` に記録 |
| ギャップのみ更新 | `GAP_n` のみ変更した CSV | 既存シーケンスに上書き（実装 TBD） |

## 5. プリフライト詳細

- **ヘッダー検査**：完全一致必須。ズレは候補提示 (`イン点` → `イン点（全角）` など)。
- **TC 妥当性**：フォーマット／逆転／fps 非一致を検出。
- **色検査**：マップ外は警告で正規化候補を提示。ユーザー選択後に適用。
- **ギャップ検査**：`GAP_n` ・尺、テンプレ定義との整合性。
- **ファイルパス検査**：テンプレ宣言の `path_map` で UNC/SMB/ドライブレターを正規化。

## 6. 出力フォーマット

- `xmeml` シーケンス。既存 Python 出力と同等の要素順序を保持。
- Premiere プロジェクトに直接追加。Resolve でもインポート可能。
- `diag.zip`
  - `job.json`
  - `errors.csv`（エラー時のみ）
  - 元 CSV コピー
  - 使用テンプレ YAML
  - `plugin_version.txt`

## 7. UAT 条件（詳細は `specs/qa/uat_checklist.md`）

- 同一 CSV + テンプレ → シーケンス完全一致（フレーム単位）。
- `GAP_n` → 指定秒数の空白＆テロップが V1 に配置される。
- ラベル → 色マップ通り。
- オフライン環境（Air-gapped Mac/Win）でインストール・実行が可能。

## 8. 将来リスク

- **CEP 廃止**：コアロジックを TS/WASM で実装し、UXP へ移植しやすくする。
- **ラベルセット差異**：Premiere のカスタムラベルセットで色名が変わった場合はテンプレ側にマップを追記し吸収。
- **テンプレ更新**：非互換変更は MAJOR バージョンを increment。`job.json` にテンプレバージョンを記録。

