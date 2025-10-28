# Resolve Script Specification (Menu Add-on + FCPXML Backup)

## 0. Summary

DaVinci Resolve 上で CSV → タイムライン再構築を行うメニュー拡張。Python/Lua スクリプトを `Scripts/` に配置するだけで使え、Premiere 生成の XML をそのまま Resolve へインポートする保険も提供する。

Premiere 向け XML が現状 Resolve でもインポート可能なため、基礎ロジックは共通化しつつ、Resolve 独自の Clip Color/Marker などで色を表現する。

## 1. 配布・導入

- 配布物：
  - `Scripts/User/AutoEdit/csv_timeline_builder.py`
  - `Templates/resolve/*.yaml`
  - `docs/operations/resolve_card.pdf`
- 導入：
  1. ZIP を NAS からコピー。
  2. Resolve の Scripts ディレクトリ（ユーザー領域）にフォルダごと配置。
  3. メニュー `Workspace > Scripts > Update` を実行。
- 署名・ハッシュは同梱ドキュメントに記載（SOC 対応）。

## 2. メニューフロー

1. `Scripts > CSV Timeline Builder` を起動。
2. CSV ファイルを選択。
3. プリフライト（Premiere 版と同等）。
4. テンプレ選択（YAML）。
5. 生成：
   - Media Pool にテンプレで指定された Bin/Clip を作成。
   - 既存素材はプロジェクト内から再利用（再リンクルールはテンプレ `path_map`）。
   - 新規タイムラインを作り、ブロック・ギャップを配置。
   - 色表現は Clip Color、または Marker を使用。ラベル名は `comment` として保持。
   - `diag.zip` 保存。
6. オプション：FCPXML/EDL も並行して生成。

## 3. ロジック

- `common/data_contract.md` に定義された CSV 契約とテンプレ宣言を利用。
- タイムライン配置は Premiere 版と共通。ギャップは `Generator > Solid Color` や `Titles > Text` を使用。
- テロップ用文字列（CSV `文字起こし`）をタイトルに流し込むモジュールを用意（任意）。
- `diag.zip` に環境情報（Resolve バージョン・OS）を含める。

## 4. FCPXML / EDL 併用

- Resolve スクリプトに加えて、同一 CSV から FCPXML を出力し、手動インポートでも同じ結果になることを保証。
- Premiere / Resolve 両方が同一 XML を受け入れられるため、FCPXML は冗長化手段として提供。

## 5. 受け入れ条件（概要）

- CSV + テンプレ → Premiere 版 XML → Resolve でインポート → スクリプト生成タイムラインと結果一致。
- ギャップ・色・ブロック開始位置がフレーム単位で一致。
- オフライン環境での動作を確認。
- プリフライトが `common/data_contract.md` のルールを全て検査。

## 6. ログ & バージョン管理

- `job.json`, `errors.csv`, `diag.zip` を Premiere 版と同様に生成。
- Resolve スクリプト自身のバージョンは `<program>_vMAJOR.MINOR.PATCH` とし、`job.json` に記録。

## 7. 未決事項 / TODO

- [ ] Resolve API でマーカー色を「Premiere ラベル名」とマッピングする最適な UI 表現を決定。
- [ ] タイトル生成処理（CSV `文字起こし` → テキスト）を実装するか要判断。
- [ ] FCPXML/EDL 出力モジュールは Python で共通化予定。

