# AutoCut プロジェクト

Premiere Pro の文字起こし CSV とテンプレート XML をもとに、Google Sheets + GAS と Python で粗編集（ラフカット）を自動生成するツール群です。

ディレクトリ構成:
- `premiere/tools/autocut/`: Google Apps Script や Python など、エピソード共通で使うツール類。
- `premiere/docs/`: ワークフローの背景説明やメモなどのドキュメント。`autocut_progress.md` を格納。
- `premiere/projects/<episode_id>/`: 各エピソード固有の素材。
  - `inputs/`: Premiere から書き出したテンプレート XML や最終 CSV などの入力ファイル。
  - `outputs/`: ツールで生成された新しい XML や派生成果物。

エピソードを新規に追加するときは、`premiere/projects/<episode_id>/inputs` に元データを置き、生成物は `outputs` にまとめるようにすると他エピソードと混ざりません。

使い方（概要）:
1. Premiere から対象シーケンスの「文字起こし CSV」と「テンプレート XML」を書き出す。
2. Google Sheets に CSV を貼付け、`premiere/tools/autocut/csv_premiere.js` を（スクリプトエディタに貼り付けて）実行。
   - Step1: 整形 → Step2: 色抽出（必要なら並べ替え/空行） → Step3: 最終 CSV ダウンロード
3. Python で XML を生成:
   - GUI で選ぶ: `python premiere/tools/autocut/csv_xml_cutter.py` を実行して案内に従う
   - 直接指定: `python premiere/tools/autocut/csv_xml_cutter.py <final_csv> <template_xml>`

補足:
- 30fps 前提のタイムコード処理です。
- ギャップ（間）は 20 秒相当になるよう GAS 側でダミークリップ長を調整しています。

詳細は `premiere/docs/autocut_progress.md` を参照してください。
