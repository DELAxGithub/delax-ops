# UAT Checklist

本チェックリストは Premiere パネル版と Resolve スクリプト版の双方で満たすべき受け入れ条件を定義します。

## 1. テスト入力

- GAS 生成 CSV 4 件（現案件の残り 4 件）
- 各 CSV に対応するテンプレ YAML + テンプレ XML
- ギャップのみのケース（GAP_n のみを含む CSV）

## 2. 共通確認項目

- [ ] ヘッダー完全一致検証（変換前に警告／エラーを出す）
- [ ] 時間コード逆転・欠落行を検出
- [ ] 色マップが正しく適用（警告時に候補提示）
- [ ] `GAP_n` → 指定秒数のギャップ＋テロップ生成（任意）
- [ ] `job.json` に `csv_sha`, `template_version`, `timeline_uuid`, `warnings`, `errors` が記録される
- [ ] `diag.zip` に `job.json`, `errors.csv`, 入力 CSV, テンプレ YAML, `plugin_version.txt` を含める

## 3. Premiere 版（CEPパネル）

- [ ] 同一 CSV + テンプレ → シーケンスがフレーム単位で完全一致
- [ ] `label2` が色マップ通りに反映
- [ ] `pproTicks` が `frames / fps * 254016000000` を満たす
- [ ] ギャップ前後の余白がテンプレ `gap_seconds` 通り
- [ ] オフライン（ネット遮断）環境でインストール→実行が成功

## 4. Resolve 版（スクリプト）

- [ ] スクリプトメニューがユーザー権限で登録できる
- [ ] Premiere 生成 XML を Resolve で読み込み → スクリプト生成結果と一致
- [ ] Clip Color / Marker で色を表現
- [ ] ギャップは Solid Color or Title で表現し、長さが一致
- [ ] `diag.zip` に Resolve バージョンと OS 情報を追加

## 5. FCPXML / EDL 保険

- [ ] 同一 CSV から FCPXML を出力 → Resolve / Premiere へインポートして結果一致
- [ ] エラー時には `errors.csv` に該当行を抽出

## 6. 監査対応

- [ ] インストールログが `logs/install_*.txt` に出力
- [ ] `job.json` の保持期間（30日）を運用カードに記載
- [ ] ハッシュ（ZXP/FCPXML など）が `docs/rfi/` に記録

## 7. 回帰テスト

- [ ] 既存プロジェクト（例：01舟津シリーズ）で再度生成 → 旧結果と diff なし
- [ ] 関係者レビュー（編集チーム）のサインオフ取得

