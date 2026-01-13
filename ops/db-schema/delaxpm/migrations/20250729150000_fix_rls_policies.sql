/*
  # RLSポリシー修正 - 認証ユーザー向けアクセス

  本番環境でチームダッシュボードが表示されない問題を修正。
  全テーブルのRLSポリシーを認証ユーザー向けに変更。
*/

-- team_dashboard テーブルのポリシー修正
DROP POLICY IF EXISTS "Enable read access for all users" ON team_dashboard;
DROP POLICY IF EXISTS "Enable write access for all users" ON team_dashboard;
DROP POLICY IF EXISTS "Enable read access for authenticated users" ON team_dashboard;
DROP POLICY IF EXISTS "Enable write access for authenticated users" ON team_dashboard;

CREATE POLICY "Enable read access for authenticated users" ON team_dashboard
  FOR SELECT TO authenticated USING (true);

CREATE POLICY "Enable write access for authenticated users" ON team_dashboard
  FOR ALL TO authenticated USING (true) WITH CHECK (true);

-- programs テーブルのポリシー修正
DROP POLICY IF EXISTS "programs_full_access" ON programs;
CREATE POLICY "programs_full_access" ON programs FOR ALL TO authenticated USING (true) WITH CHECK (true);

-- series テーブルのポリシー修正
DROP POLICY IF EXISTS "series_full_access" ON series;
CREATE POLICY "series_full_access" ON series FOR ALL TO authenticated USING (true) WITH CHECK (true);

-- episodes テーブルのポリシー修正
DROP POLICY IF EXISTS "episodes_full_access" ON episodes;
CREATE POLICY "episodes_full_access" ON episodes FOR ALL TO authenticated USING (true) WITH CHECK (true);

-- status_master テーブルのポリシー修正
DROP POLICY IF EXISTS "status_master_read" ON status_master;
CREATE POLICY "status_master_read" ON status_master FOR SELECT TO authenticated USING (true);

-- calendar_events テーブルのポリシー修正
DROP POLICY IF EXISTS "Enable read access for all users" ON calendar_events;
DROP POLICY IF EXISTS "Enable insert access for all users" ON calendar_events;
DROP POLICY IF EXISTS "Enable update access for all users" ON calendar_events;
DROP POLICY IF EXISTS "Enable delete access for all users" ON calendar_events;
DROP POLICY IF EXISTS "Enable read access for authenticated users" ON calendar_events;
DROP POLICY IF EXISTS "Enable insert access for authenticated users" ON calendar_events;
DROP POLICY IF EXISTS "Enable update access for authenticated users" ON calendar_events;
DROP POLICY IF EXISTS "Enable delete access for authenticated users" ON calendar_events;

CREATE POLICY "Enable read access for authenticated users" ON calendar_events
  FOR SELECT TO authenticated USING (true);

CREATE POLICY "Enable insert access for authenticated users" ON calendar_events
  FOR INSERT TO authenticated WITH CHECK (true);

CREATE POLICY "Enable update access for authenticated users" ON calendar_events
  FOR UPDATE TO authenticated USING (true) WITH CHECK (true);

CREATE POLICY "Enable delete access for authenticated users" ON calendar_events
  FOR DELETE TO authenticated USING (true);