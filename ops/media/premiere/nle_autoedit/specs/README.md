# nle_autoedit Specs

このディレクトリは、Premiere／DaVinci Resolve 向け「オフライン自動編集キット」の仕様を集約する場所です。既存 Python / GAS ロジックを出発点に、NHK 的制約（ネット遮断・ユーザー権限インストール）でも再現性の高いツールを提供することを目的とします。

## 進め方（cckiro流）

1. **Specification First** – 仕様を Markdown に落とし込み、TODO/TBD を明確にした状態でレビューしてから実装へ進みます。
2. **Prototype & Fit-Gap** – 既存 CSV → XML 変換ロジックを `premiere/prototype/`, `resolve/prototype/` で検証し、仕様との差分を `specs/common/data_contract.md` に反映します。
3. **Implementation** – 仕様合意後、Premiere CEP/UXP パネルと Resolve スクリプトをそれぞれ `premiere/src/`, `resolve/src/` 配下に実装します。
4. **Diagnostics & Logs** – 共通のジョブレシート／診断 zip を `common` ユーティリティとして設計し、両NLEで再利用します。
5. **UAT & Docs** – `specs/qa/uat_checklist.md` に沿って再現性テストを実施し、稟議用 1 枚資料・運用カードを `docs/` 配下に整備します。

## ディレクトリ構成

- `premiere/`
  - `prototype/` – 既存 Python ロジックの検証／サンプルデータ
  - `design/` – CEP/UXP UI、モジュール構成案
  - `src/` – TypeScript 等の本実装（署名付き ZXP を生成）
- `resolve/`
  - `prototype/` – Resolve API での動作検証、FCPXML 雛形
  - `design/` – メニュー構成・Bin 設計
  - `src/` – Lua/Python + FCPXML 併用実装
- `templates/` – 番組ごとのテンプレ宣言（Premiere/Resolve 共通）
- `specs/`
  - `common/` – CSV 契約・テンプレ定義・プリフライト仕様
  - `premiere/`, `resolve/` – 各 NLE 向け詳細仕様
  - `qa/` – 受け入れ条件、テストケース
- `docs/`
  - `rfi/` – 稟議・監査提出用資料
  - `operations/` – 日常運用手順、ログ保管ポリシー

## 現在のタスク

- [ ] `specs/common/data_contract.md` を作成し、CSV契約・ギャップ・ラベル変換を明文化する。
- [ ] `specs/premiere/panel_spec.md` にパネルフローとプリフライト要件を整理する。
- [ ] `specs/resolve/script_spec.md` に Resolve スクリプトの挙動を整理し、XML 互換性（Premiere生成XMLがResolveで利用可能）も明記する。
- [ ] `specs/qa/uat_checklist.md` に受け入れ基準と診断ログ出力要件をまとめる。

