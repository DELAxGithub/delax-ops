# episodes ディレクトリの使い方

各エピソード固有の素材は `premiere/projects/<episode_id>/` 以下にまとめます。`<episode_id>` は `022` や `OrionEp2` など、プロジェクトが判別できる短いIDにしてください。

推奨構成:
- `inputs/`: Premiereから書き出したテンプレートXMLや編集指示CSVなどの元データ。
- `outputs/`: `premiere/tools/autocut/` 配下のスクリプトで生成されたXMLや補助ファイル。
- `notes/` (任意): エピソード固有のメモを残したい場合に作成してください。

例:
```text
premiere/projects/
  022/
    inputs/
      022_統合_1.xml
      Sequence 11.xml
    outputs/
      022!!_final_cut_cut_from_022_統合_1.xml
```

この構成にそろえておくと、ツール本体の更新と個別エピソードの成果物が混ざらずに管理できます。
