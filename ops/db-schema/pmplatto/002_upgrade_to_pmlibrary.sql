/*
  PMPlatto to PMLibrary Schema Upgrade Script
  
  このスクリプトは段階的にPMPlattoのSupabaseスキーマをPMLibraryレベルに更新します。
  既存データの整合性を保ちながら、新機能を段階的に追加します。
*/

-- ==========================================
-- Phase 1: 既存 programs テーブルの拡張
-- ==========================================

BEGIN;

-- programs テーブルに新しいフィールドを追加
ALTER TABLE programs 
  ADD COLUMN IF NOT EXISTS series_name text,
  ADD COLUMN IF NOT EXISTS series_type text,
  ADD COLUMN IF NOT EXISTS season integer,
  ADD COLUMN IF NOT EXISTS total_episodes integer;

-- series_type の制約を追加
ALTER TABLE programs 
  ADD CONSTRAINT programs_series_type_check 
  CHECK (series_type IN ('interview', 'vtr') OR series_type IS NULL);

-- 既存データに対するデフォルト値の設定
UPDATE programs SET 
  series_name = title,
  series_type = 'interview',  -- デフォルトをインタビューに設定
  season = 1,
  total_episodes = 1
WHERE series_name IS NULL;

COMMIT;

-- ==========================================
-- Phase 2: エピソード管理テーブルの作成
-- ==========================================

BEGIN;

-- ステータスマスターテーブル
CREATE TABLE IF NOT EXISTS episode_statuses (
  id serial PRIMARY KEY,
  status_name text NOT NULL UNIQUE,
  status_order integer NOT NULL,
  color_code text,
  created_at timestamptz DEFAULT now()
);

-- 10段階のステータスを定義（PMLibraryと同一）
INSERT INTO episode_statuses (status_name, status_order, color_code) VALUES
  ('台本作成中', 1, '#6B7280'),
  ('素材準備', 2, '#8B5CF6'),
  ('素材確定', 3, '#6366F1'),
  ('編集中', 4, '#3B82F6'),
  ('試写1', 5, '#06B6D4'),
  ('修正1', 6, '#10B981'),
  ('MA中', 7, '#84CC16'),
  ('初稿完成', 8, '#EAB308'),
  ('修正中', 9, '#F59E0B'),
  ('完パケ納品', 10, '#22C55E')
ON CONFLICT (status_name) DO NOTHING;

-- エピソードテーブル
CREATE TABLE IF NOT EXISTS episodes (
  id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  episode_id text NOT NULL UNIQUE,
  title text NOT NULL,
  episode_type text CHECK (episode_type IN ('interview', 'vtr')) NOT NULL,
  season integer NOT NULL,
  episode_number integer NOT NULL,
  
  -- 共通項目
  script_url text,
  current_status text REFERENCES episode_statuses(status_name),
  director text,
  due_date date,
  
  -- インタビュー番組用
  guest_name text,
  recording_date date,
  recording_location text,
  
  -- VTR番組用  
  material_status text CHECK (material_status IN ('○', '△', '×', NULL)),
  
  -- タイムスタンプ
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- ステータス履歴テーブル
CREATE TABLE IF NOT EXISTS status_history (
  id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  episode_id bigint REFERENCES episodes(id) ON DELETE CASCADE,
  old_status text,
  new_status text,
  changed_by uuid REFERENCES auth.users(id),
  change_reason text,
  changed_at timestamptz DEFAULT now()
);

COMMIT;

-- ==========================================
-- Phase 3: カレンダー機能の拡張
-- ==========================================

BEGIN;

-- calendar_tasks テーブルにチームイベント機能を追加
ALTER TABLE calendar_tasks 
  ADD COLUMN IF NOT EXISTS meeting_url text,
  ADD COLUMN IF NOT EXISTS description text,
  ADD COLUMN IF NOT EXISTS is_team_event boolean DEFAULT false;

-- meeting URL の形式チェック制約
ALTER TABLE calendar_tasks 
  ADD CONSTRAINT valid_meeting_url 
  CHECK (meeting_url IS NULL OR meeting_url ~ '^https?://');

COMMIT;

-- ==========================================
-- Phase 4: インデックスとパフォーマンス最適化
-- ==========================================

-- episodes テーブル用インデックス
CREATE INDEX IF NOT EXISTS idx_episodes_episode_id ON episodes(episode_id);
CREATE INDEX IF NOT EXISTS idx_episodes_season ON episodes(season);
CREATE INDEX IF NOT EXISTS idx_episodes_current_status ON episodes(current_status);
CREATE INDEX IF NOT EXISTS idx_episodes_due_date ON episodes(due_date);
CREATE INDEX IF NOT EXISTS idx_episodes_episode_type ON episodes(episode_type);

-- status_history テーブル用インデックス
CREATE INDEX IF NOT EXISTS idx_status_history_episode ON status_history(episode_id);
CREATE INDEX IF NOT EXISTS idx_status_history_changed_at ON status_history(changed_at);

-- calendar_tasks テーブル用インデックス
CREATE INDEX IF NOT EXISTS idx_calendar_tasks_team_event ON calendar_tasks (is_team_event);

-- ==========================================
-- Phase 5: RLS (Row Level Security) の設定
-- ==========================================

-- episodes テーブルのRLS
ALTER TABLE episodes ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Enable read access for authenticated users" ON episodes
  FOR SELECT TO authenticated USING (true);

CREATE POLICY "Enable write access for authenticated users" ON episodes
  FOR ALL TO authenticated USING (true) WITH CHECK (true);

-- status_history テーブルのRLS
ALTER TABLE status_history ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Enable read access for authenticated users" ON status_history
  FOR SELECT TO authenticated USING (true);

CREATE POLICY "Enable write access for authenticated users" ON status_history
  FOR INSERT TO authenticated WITH CHECK (true);

-- episode_statuses テーブルのRLS
ALTER TABLE episode_statuses ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Enable read access for authenticated users" ON episode_statuses
  FOR SELECT TO authenticated USING (true);

-- ==========================================
-- Phase 6: トリガーと関数の作成
-- ==========================================

-- エピソード更新日時のトリガー
CREATE OR REPLACE FUNCTION update_episode_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_episodes_updated_at
  BEFORE UPDATE ON episodes
  FOR EACH ROW
  EXECUTE FUNCTION update_episode_updated_at();

-- ステータス変更時に履歴を記録するトリガー
CREATE OR REPLACE FUNCTION record_status_change()
RETURNS TRIGGER AS $$
BEGIN
  IF OLD.current_status IS DISTINCT FROM NEW.current_status THEN
    INSERT INTO status_history (episode_id, old_status, new_status, changed_by)
    VALUES (NEW.id, OLD.current_status, NEW.current_status, auth.uid());
  END IF;
  RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER record_episode_status_change
  AFTER UPDATE OF current_status ON episodes
  FOR EACH ROW
  EXECUTE FUNCTION record_status_change();

-- ==========================================
-- Phase 7: 便利なビューの作成
-- ==========================================

-- エピソード詳細ビュー（PMLibraryと同一）
CREATE OR REPLACE VIEW episode_details AS
SELECT 
  e.*,
  es.status_order,
  es.color_code,
  p.series_name,
  CASE 
    WHEN e.due_date < CURRENT_DATE AND e.current_status != '完パケ納品' THEN true
    ELSE false
  END as is_overdue,
  CURRENT_DATE - e.due_date as days_overdue
FROM episodes e
LEFT JOIN episode_statuses es ON e.current_status = es.status_name
LEFT JOIN programs p ON p.season = e.season AND p.series_type = e.episode_type;

-- ビューへのアクセス権付与
GRANT SELECT ON episode_details TO authenticated;

-- ==========================================
-- Phase 8: データ整合性チェック
-- ==========================================

-- 更新後の整合性確認クエリ
-- これらのクエリで問題がないことを確認してから移行完了とする

-- 1. programs テーブルの新フィールド確認
SELECT 
  COUNT(*) as total_programs,
  COUNT(series_name) as programs_with_series_name,
  COUNT(series_type) as programs_with_series_type,
  COUNT(season) as programs_with_season
FROM programs;

-- 2. episode_statuses テーブルの確認
SELECT COUNT(*) as status_count FROM episode_statuses;

-- 3. 新しく追加されたテーブルの存在確認
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_name IN ('episodes', 'status_history', 'episode_statuses');

-- 4. calendar_tasks の新フィールド確認
SELECT 
  COUNT(*) as total_tasks,
  COUNT(meeting_url) as tasks_with_meeting_url,
  COUNT(description) as tasks_with_description,
  COUNT(CASE WHEN is_team_event = true THEN 1 END) as team_events
FROM calendar_tasks;

-- 5. インデックスの確認
SELECT indexname 
FROM pg_indexes 
WHERE tablename IN ('episodes', 'status_history', 'calendar_tasks')
  AND schemaname = 'public';

/*
移行完了チェックリスト:
□ programs テーブルに4つの新フィールドが追加されている
□ episode_statuses テーブルに10個のステータスが登録されている
□ episodes, status_history テーブルが作成されている
□ calendar_tasks テーブルに3つの新フィールドが追加されている
□ 全てのインデックスが作成されている
□ RLSポリシーが設定されている
□ トリガーが設定されている
□ episode_details ビューが作成されている
□ 既存データが保持されている
□ 整合性チェックが全て通っている
*/