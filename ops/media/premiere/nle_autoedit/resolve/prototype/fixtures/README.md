# Resolve Prototype Fixtures

Premiere のフィクスチャと同じ CSV / XML を利用します。Resolve スクリプトでは、NAS 上の素材を Media Pool に再リンクするためテンプレ宣言の `path_map` を優先します。

- 01 舟津: `/Volumes/P-40/Dropbox/LIBERARY/202501_舟津/` 以下
- 02 大川内: `/Volumes/P-40/Dropbox/LIBERARY/202502_大川内/`
- 残り 4 件: TBD（CSV/テンプレ確認後に追記）

## FCPXML バックアップ

各ケースについて Premiere 生成 XML をそのまま Resolve にインポートできることを確認済みです。追加で FCPXML/EDL を生成する際は `premiere/prototype/csv_xml_cutter_reference.py` を流用し、同じブロック構成が得られることを検証します。

