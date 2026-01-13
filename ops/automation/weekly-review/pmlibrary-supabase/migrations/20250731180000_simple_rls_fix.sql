-- Simple RLS Fix and Data Population
-- Only fix RLS policies and insert essential data

-- 1. Fix episode_statuses RLS policies
DROP POLICY IF EXISTS "Enable read access for authenticated users" ON episode_statuses;
DROP POLICY IF EXISTS "Enable write access for authenticated users" ON episode_statuses;

-- Create permissive policies for episode_statuses
CREATE POLICY "Allow read access for all users" ON episode_statuses
  FOR SELECT USING (true);

CREATE POLICY "Allow write access for all users" ON episode_statuses
  FOR ALL USING (true);

-- 2. Fix episodes RLS policies  
DROP POLICY IF EXISTS "Enable read access for authenticated users" ON episodes;
DROP POLICY IF EXISTS "Enable write access for authenticated users" ON episodes;

-- Create permissive policies for episodes
CREATE POLICY "Allow read access for all users" ON episodes
  FOR SELECT USING (true);

CREATE POLICY "Allow write access for all users" ON episodes
  FOR ALL USING (true);

-- 3. Fix programs RLS policies
DROP POLICY IF EXISTS "Enable read access for authenticated users" ON programs;
DROP POLICY IF EXISTS "Enable write access for authenticated users" ON programs;

-- Create permissive policies for programs
CREATE POLICY "Allow read access for all users" ON programs
  FOR SELECT USING (true);

CREATE POLICY "Allow write access for all users" ON programs
  FOR ALL USING (true);

-- 4. Insert episode_statuses master data
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

-- 5. Force schema cache refresh
SELECT pg_notify('pgrst', 'reload schema');