/*
  # Team Dashboard Initial Data
  
  1. Purpose
    - Insert initial data for team_dashboard widgets
    - Ensure all 4 widget types are available
    - Provide meaningful default content
    
  2. Widget Types
    - memo: Team shared notes
    - quicklinks: Quick access links
    - tasks: Team shared task list
    - schedule: Schedule overview
*/

-- Clear any existing data (for clean initialization)
DELETE FROM team_dashboard;

-- Insert initial dashboard widgets
INSERT INTO team_dashboard (widget_type, title, content, sort_order, is_active) VALUES
  (
    'memo', 
    'チーム共有メモ', 
    '{"text": "ここにチーム共有のメモを記載します。\n\n• 重要な連絡事項\n• 作業上の注意点\n• その他の情報\n\n編集ボタンから内容を更新できます。"}', 
    1, 
    true
  ),
  (
    'quicklinks', 
    'クイックリンク', 
    '{"links": [{"url": "https://github.com/DELAxGithub/DELAxPM", "label": "GitHub リポジトリ"}, {"url": "https://delaxpm.netlify.app", "label": "本番サイト"}, {"url": "https://delaxpm.netlify.app/liberary", "label": "リベラリー"}, {"url": "https://delaxpm.netlify.app/platto", "label": "プラット"}]}', 
    2, 
    true
  ),
  (
    'tasks', 
    'チーム共有タスク', 
    '{"tasks": [{"id": "1", "text": "UIテスト実行", "completed": false}, {"id": "2", "text": "ドキュメント更新", "completed": true}, {"id": "3", "text": "バグ修正確認", "completed": false}, {"id": "4", "text": "カレンダー機能テスト", "completed": false}]}', 
    3, 
    true
  ),
  (
    'schedule', 
    'スケジュール', 
    '{"events": [{"date": "2025-01-30", "title": "月次レビュー", "type": "meeting"}, {"date": "2025-02-01", "title": "新機能リリース", "type": "milestone"}]}', 
    4, 
    true
  );

-- Verify data insertion
DO $$
DECLARE
    widget_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO widget_count FROM team_dashboard;
    
    IF widget_count = 4 THEN
        RAISE NOTICE 'Team dashboard initialization successful: % widgets created', widget_count;
    ELSE
        RAISE EXCEPTION 'Team dashboard initialization failed: expected 4 widgets, got %', widget_count;
    END IF;
END $$;