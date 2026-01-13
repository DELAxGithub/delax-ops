/*
  # チーム共有ダッシュボード機能

  1. 新規テーブル
    - `team_dashboard` - チーム共有のダッシュボード情報

  2. 機能
    - クイックリンク集の管理
    - チーム共有メモ
    - タスクリスト
    - スケジュール概要情報
*/

-- チームダッシュボードテーブル
CREATE TABLE IF NOT EXISTS team_dashboard (
  id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  widget_type text NOT NULL CHECK (widget_type IN ('quicklinks', 'memo', 'tasks', 'schedule')),
  title text NOT NULL,
  content jsonb NOT NULL DEFAULT '{}',
  sort_order integer NOT NULL DEFAULT 0,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  created_by uuid REFERENCES auth.users(id),
  updated_by uuid REFERENCES auth.users(id)
);

-- インデックスの作成
CREATE INDEX IF NOT EXISTS idx_team_dashboard_widget_type ON team_dashboard(widget_type);
CREATE INDEX IF NOT EXISTS idx_team_dashboard_sort_order ON team_dashboard(sort_order);
CREATE INDEX IF NOT EXISTS idx_team_dashboard_is_active ON team_dashboard(is_active);

-- RLSの有効化
ALTER TABLE team_dashboard ENABLE ROW LEVEL SECURITY;

-- RLSポリシー（チーム全体で共有、認証ユーザーは全てのCRUD操作が可能）
CREATE POLICY "Enable read access for authenticated users" ON team_dashboard
  FOR SELECT TO authenticated USING (true);

CREATE POLICY "Enable write access for authenticated users" ON team_dashboard
  FOR ALL TO authenticated USING (true) WITH CHECK (true);

-- 更新日時のトリガー
CREATE OR REPLACE FUNCTION update_team_dashboard_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  NEW.updated_by = auth.uid();
  RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_team_dashboard_updated_at
  BEFORE UPDATE ON team_dashboard
  FOR EACH ROW
  EXECUTE FUNCTION update_team_dashboard_updated_at();

-- 作成者の設定トリガー
CREATE OR REPLACE FUNCTION set_team_dashboard_created_by()
RETURNS TRIGGER AS $$
BEGIN
  NEW.created_by = auth.uid();
  NEW.updated_by = auth.uid();
  RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER set_team_dashboard_created_by
  BEFORE INSERT ON team_dashboard
  FOR EACH ROW
  EXECUTE FUNCTION set_team_dashboard_created_by();

-- サンプルデータの挿入（開発環境用）
INSERT INTO team_dashboard (widget_type, title, content, sort_order) VALUES
  ('memo', 'チーム共有メモ', '{"text": "ここにチーム共有のメモを記載します。\n\n• 重要な連絡事項\n• 作業上の注意点\n• その他の情報"}', 1),
  ('quicklinks', 'クイックリンク', '{"links": [{"url": "https://example.com", "label": "社内システム"}, {"url": "https://github.com", "label": "GitHub"}]}', 2),
  ('tasks', 'チーム共有タスク', '{"tasks": [{"id": "1", "text": "サンプルタスク1", "completed": false}, {"id": "2", "text": "サンプルタスク2", "completed": true}]}', 3)
ON CONFLICT DO NOTHING;

-- コメント追加
COMMENT ON TABLE team_dashboard IS '制作チーム用の共有ダッシュボード情報';
COMMENT ON COLUMN team_dashboard.widget_type IS 'ウィジェットタイプ: quicklinks, memo, tasks, schedule';
COMMENT ON COLUMN team_dashboard.content IS 'ウィジェットの内容をJSON形式で格納';
COMMENT ON COLUMN team_dashboard.sort_order IS 'ダッシュボード内での表示順序';