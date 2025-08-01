-- Fix RLS and Schema Cache Issues
-- This migration addresses RLS policy issues and schema cache problems

-- 1. Temporarily disable RLS to insert master data
ALTER TABLE episode_statuses DISABLE ROW LEVEL SECURITY;

-- 2. Insert episode_statuses master data
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

-- 3. Re-enable RLS with proper policies
ALTER TABLE episode_statuses ENABLE ROW LEVEL SECURITY;

-- 4. Create more permissive RLS policies for episode_statuses
DROP POLICY IF EXISTS "Enable read access for authenticated users" ON episode_statuses;
DROP POLICY IF EXISTS "Enable write access for authenticated users" ON episode_statuses;

-- Allow all authenticated users to read episode_statuses
CREATE POLICY "Allow read access for all users" ON episode_statuses
  FOR SELECT USING (true);

-- Allow all authenticated users to insert/update episode_statuses
CREATE POLICY "Allow write access for authenticated users" ON episode_statuses
  FOR ALL TO authenticated USING (true) WITH CHECK (true);

-- 5. Fix episodes table RLS policies
DROP POLICY IF EXISTS "Enable read access for authenticated users" ON episodes;
DROP POLICY IF EXISTS "Enable write access for authenticated users" ON episodes;

-- Allow all authenticated users full access to episodes
CREATE POLICY "Allow all access for authenticated users" ON episodes
  FOR ALL TO authenticated USING (true) WITH CHECK (true);

-- 6. Refresh schema cache by updating table comments
COMMENT ON TABLE episodes IS 'Episodes table - updated ' || now()::text;
COMMENT ON TABLE episode_statuses IS 'Episode statuses master table - updated ' || now()::text;

-- 7. Verify the current_status foreign key relationship
ALTER TABLE episodes DROP CONSTRAINT IF EXISTS episodes_current_status_fkey;
ALTER TABLE episodes ADD CONSTRAINT episodes_current_status_fkey 
  FOREIGN KEY (current_status) REFERENCES episode_statuses(status_name);

-- 8. Insert some sample programs data to support episodes
INSERT INTO programs (program_id, title, status, series_name, series_type, season, total_episodes) VALUES
  ('LIBRARY-S1-VTR', 'オリオンの会議室 シーズン1', '制作中', 'オリオンの会議室', 'vtr', 1, 15),
  ('LIBRARY-S1-INT', 'リベラルアーツインタビュー シーズン1', '制作中', 'リベラルアーツインタビュー', 'interview', 1, 6),
  ('LIBRARY-S2-VTR', 'オリオンの会議室 シーズン2', '企画中', 'オリオンの会議室', 'vtr', 2, 15),
  ('LIBRARY-S2-INT', '同友会インタビュー シーズン2', '企画中', '同友会インタビュー', 'interview', 2, 5)
ON CONFLICT (program_id) DO UPDATE SET
  series_name = EXCLUDED.series_name,
  series_type = EXCLUDED.series_type,
  season = EXCLUDED.season,
  total_episodes = EXCLUDED.total_episodes;

-- 9. Force schema cache refresh
NOTIFY pgrst, 'reload schema';