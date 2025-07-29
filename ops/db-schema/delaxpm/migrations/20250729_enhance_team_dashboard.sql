-- チームダッシュボード機能強化マイグレーション

-- 既存データを更新（より実用的な内容に変更）
UPDATE team_dashboard SET content = '{"text": "📋 チーム進捗共有メモ\n\n【重要】\n• KDDIプロジェクト: 2025年8月末納期\n• 若手6人候補リスト確認中\n• 新機能テスト完了予定: 7/31\n\n【連絡事項】\n• Slack招待URL更新済み\n• 週次レビュー: 毎週金曜15:00\n• 緊急時連絡: #dela-emergency"}' 
WHERE widget_type = 'memo';

UPDATE team_dashboard SET content = '{"links": [{"url": "https://kddi-dela-team.slack.com/join/shared_invite/xxx", "label": "🚀 KDDIチームSlack参加"}, {"url": "https://github.com/DELAxGithub/DELAxPM", "label": "📁 GitHub リポジトリ"}, {"url": "https://delaxpm.netlify.app", "label": "🌐 本番サイト"}, {"url": "https://kddi-project-docs.notion.so", "label": "📚 プロジェクト資料"}, {"url": "https://meet.google.com/kddi-weekly", "label": "📹 週次会議室"}]}' 
WHERE widget_type = 'quicklinks';

UPDATE team_dashboard SET content = '{"tasks": [{"id": "task-1", "text": "サンプルタスク1: UI改善完了確認", "completed": false, "category": "development"}, {"id": "task-2", "text": "サンプルタスク2: データベース最適化", "completed": true, "category": "backend"}, {"id": "task-3", "text": "若手6人候補面談スケジュール調整", "completed": false, "category": "hr"}, {"id": "task-4", "text": "KDDIプレゼン資料準備", "completed": false, "category": "presentation"}, {"id": "task-5", "text": "テストデータ準備完了", "completed": true, "category": "testing"}]}' 
WHERE widget_type = 'tasks';

-- メンバー管理ウィジェットを追加
INSERT INTO team_dashboard (widget_type, title, content, sort_order, is_active) 
VALUES ('members', 'チームメンバー', '{"members": [{"id": "member-1", "name": "田中 太郎", "role": "リーダー", "status": "active", "skills": ["React", "TypeScript", "プロジェクト管理"]}, {"id": "member-2", "name": "佐藤 花子", "role": "フロントエンド", "status": "active", "skills": ["React", "CSS", "UI/UX"]}, {"id": "member-3", "name": "鈴木 次郎", "role": "バックエンド", "status": "active", "skills": ["Node.js", "PostgreSQL", "API設計"]}, {"id": "member-4", "name": "若手候補A", "role": "インターン", "status": "candidate", "skills": ["JavaScript", "学習中"]}, {"id": "member-5", "name": "若手候補B", "role": "インターン", "status": "candidate", "skills": ["Python", "学習中"]}, {"id": "member-6", "name": "若手候補C", "role": "インターン", "status": "candidate", "skills": ["Java", "学習中"]}]}', 5, true)
ON CONFLICT (widget_type) DO UPDATE SET
  title = EXCLUDED.title,
  content = EXCLUDED.content,
  sort_order = EXCLUDED.sort_order,
  updated_at = now();

-- チームダッシュボードテーブルが存在しない場合の対策
CREATE TABLE IF NOT EXISTS team_dashboard (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  widget_type text UNIQUE NOT NULL,
  title text NOT NULL,
  content jsonb NOT NULL DEFAULT '{}',
  sort_order integer NOT NULL DEFAULT 0,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- インデックスを追加（パフォーマンス向上）
CREATE INDEX IF NOT EXISTS idx_team_dashboard_widget_type ON team_dashboard(widget_type);
CREATE INDEX IF NOT EXISTS idx_team_dashboard_sort_order ON team_dashboard(sort_order);
CREATE INDEX IF NOT EXISTS idx_team_dashboard_active ON team_dashboard(is_active);

-- 更新トリガーを追加
CREATE OR REPLACE FUNCTION update_team_dashboard_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_team_dashboard_updated_at ON team_dashboard;
CREATE TRIGGER trigger_update_team_dashboard_updated_at
  BEFORE UPDATE ON team_dashboard
  FOR EACH ROW
  EXECUTE FUNCTION update_team_dashboard_updated_at();