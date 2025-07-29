/*
  # Complete Database Setup
  
  1. Calendar Events Table
  2. Team Dashboard Data Initialization
  3. Handle all existing conflicts
*/

-- =========================================
-- PART 1: Calendar Events Table
-- =========================================

-- Create calendar_events table
CREATE TABLE IF NOT EXISTS calendar_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  episode_id bigint REFERENCES episodes(id) ON DELETE SET NULL,
  task_type text NOT NULL,
  start_date date NOT NULL,
  end_date date NOT NULL,
  meeting_url text,
  description text,
  is_team_event boolean DEFAULT false,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  
  -- Date validation
  CONSTRAINT valid_date_range CHECK (end_date >= start_date),
  -- Meeting URL validation
  CONSTRAINT valid_meeting_url CHECK (meeting_url IS NULL OR meeting_url ~ '^https?://')
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_calendar_events_dates ON calendar_events (start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_calendar_events_episode_id ON calendar_events (episode_id);
CREATE INDEX IF NOT EXISTS idx_calendar_events_team_event ON calendar_events (is_team_event);
CREATE INDEX IF NOT EXISTS idx_calendar_events_task_type ON calendar_events (task_type);

-- Enable RLS
ALTER TABLE calendar_events ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist and create new ones
DO $$ 
BEGIN
  DROP POLICY IF EXISTS "Enable read access for all users" ON calendar_events;
  DROP POLICY IF EXISTS "Enable insert access for all users" ON calendar_events;
  DROP POLICY IF EXISTS "Enable update access for all users" ON calendar_events;
  DROP POLICY IF EXISTS "Enable delete access for all users" ON calendar_events;
EXCEPTION
  WHEN undefined_object THEN
    NULL;
END $$;

-- Create policies for guest access
CREATE POLICY "Enable read access for all users" ON calendar_events
  FOR SELECT USING (true);

CREATE POLICY "Enable insert access for all users" ON calendar_events
  FOR INSERT WITH CHECK (true);

CREATE POLICY "Enable update access for all users" ON calendar_events
  FOR UPDATE USING (true) WITH CHECK (true);

CREATE POLICY "Enable delete access for all users" ON calendar_events
  FOR DELETE USING (true);

-- Create updated_at trigger function and trigger
CREATE OR REPLACE FUNCTION update_calendar_events_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_calendar_events_updated_at ON calendar_events;
CREATE TRIGGER update_calendar_events_updated_at
  BEFORE UPDATE ON calendar_events
  FOR EACH ROW
  EXECUTE FUNCTION update_calendar_events_updated_at();

-- =========================================
-- PART 2: Team Dashboard Policies Update
-- =========================================

-- Update team_dashboard policies for guest access
DO $$ 
BEGIN
  DROP POLICY IF EXISTS "Enable read access for authenticated users" ON team_dashboard;
  DROP POLICY IF EXISTS "Enable write access for authenticated users" ON team_dashboard;
  DROP POLICY IF EXISTS "Enable read access for all users" ON team_dashboard;
  DROP POLICY IF EXISTS "Enable write access for all users" ON team_dashboard;
EXCEPTION
  WHEN undefined_object THEN
    NULL;
END $$;

CREATE POLICY "Enable read access for all users" ON team_dashboard
  FOR SELECT USING (true);

CREATE POLICY "Enable write access for all users" ON team_dashboard
  FOR ALL USING (true) WITH CHECK (true);

-- =========================================
-- PART 3: Team Dashboard Initial Data
-- =========================================

-- Clear any existing data and insert fresh data
DELETE FROM team_dashboard;

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

-- =========================================
-- PART 4: Verification
-- =========================================

-- Verify table creation and data insertion
DO $$
DECLARE
    calendar_table_exists BOOLEAN;
    widget_count INTEGER;
BEGIN
    -- Check if calendar_events table exists
    SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_name = 'calendar_events'
    ) INTO calendar_table_exists;
    
    -- Check team_dashboard data
    SELECT COUNT(*) INTO widget_count FROM team_dashboard;
    
    -- Report results
    RAISE NOTICE 'Setup verification:';
    RAISE NOTICE '- Calendar events table exists: %', calendar_table_exists;
    RAISE NOTICE '- Team dashboard widgets: %', widget_count;
    
    IF calendar_table_exists AND widget_count = 4 THEN
        RAISE NOTICE 'Database setup completed successfully!';
    ELSE
        RAISE WARNING 'Database setup may have issues - please verify manually';
    END IF;
END $$;