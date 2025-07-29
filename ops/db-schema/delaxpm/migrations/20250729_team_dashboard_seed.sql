-- チームダッシュボード初期データの挿入

-- 既存データをクリア
DELETE FROM team_dashboard;

-- サンプルデータの挿入
INSERT INTO team_dashboard (widget_type, title, content, sort_order) VALUES
  ('memo', 'チーム共有メモ', '{"text": "ここにチーム共有のメモを記載します。\n\n• 重要な連絡事項\n• 作業上の注意点\n• その他の情報"}', 1),
  ('quicklinks', 'クイックリンク', '{"links": [{"url": "https://github.com/DELAxGithub/DELAxPM", "label": "GitHub リポジトリ"}, {"url": "https://delaxpm.netlify.app", "label": "本番サイト"}]}', 2),
  ('tasks', 'チーム共有タスク', '{"tasks": [{"id": "1", "text": "UIテスト実行", "completed": false}, {"id": "2", "text": "ドキュメント更新", "completed": true}, {"id": "3", "text": "バグ修正確認", "completed": false}]}', 3),
  ('schedule', 'スケジュール', '{}', 4)
ON CONFLICT (widget_type) DO UPDATE SET
  title = EXCLUDED.title,
  content = EXCLUDED.content,
  sort_order = EXCLUDED.sort_order,
  updated_at = now();