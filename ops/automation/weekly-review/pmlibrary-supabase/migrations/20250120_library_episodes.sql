/*
  # LIBRARY エピソード管理システム

  1. 新規テーブル
    - `episodes` - エピソード情報（主テーブル）
    - `status_history` - ステータス変更履歴
    - `episode_statuses` - ステータスマスター

  2. 既存テーブルの更新
    - `programs` テーブルはシーズン管理用に活用
*/

-- ステータスマスターテーブル
CREATE TABLE IF NOT EXISTS episode_statuses (
  id serial PRIMARY KEY,
  status_name text NOT NULL UNIQUE,
  status_order integer NOT NULL,
  color_code text,
  created_at timestamptz DEFAULT now()
);

-- 10段階のステータスを定義
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

-- エピソードテーブル（主テーブル）
CREATE TABLE IF NOT EXISTS episodes (
  id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  episode_id text NOT NULL UNIQUE, -- LA-INT001, ORN-EP01 など
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

-- 既存のprogramsテーブルに番組シリーズ情報を追加
ALTER TABLE programs
  ADD COLUMN IF NOT EXISTS series_name text,
  ADD COLUMN IF NOT EXISTS series_type text CHECK (series_type IN ('interview', 'vtr', NULL)),
  ADD COLUMN IF NOT EXISTS season integer,
  ADD COLUMN IF NOT EXISTS total_episodes integer;

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

-- インデックスの作成
CREATE INDEX IF NOT EXISTS idx_episodes_episode_id ON episodes(episode_id);
CREATE INDEX IF NOT EXISTS idx_episodes_season ON episodes(season);
CREATE INDEX IF NOT EXISTS idx_episodes_current_status ON episodes(current_status);
CREATE INDEX IF NOT EXISTS idx_episodes_due_date ON episodes(due_date);
CREATE INDEX IF NOT EXISTS idx_episodes_episode_type ON episodes(episode_type);
CREATE INDEX IF NOT EXISTS idx_status_history_episode ON status_history(episode_id);
CREATE INDEX IF NOT EXISTS idx_status_history_changed_at ON status_history(changed_at);

-- RLSの有効化
ALTER TABLE episodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE status_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE episode_statuses ENABLE ROW LEVEL SECURITY;

-- RLSポリシー
CREATE POLICY "Enable read access for authenticated users" ON episodes
  FOR SELECT TO authenticated USING (true);

CREATE POLICY "Enable write access for authenticated users" ON episodes
  FOR ALL TO authenticated USING (true) WITH CHECK (true);

CREATE POLICY "Enable read access for authenticated users" ON status_history
  FOR SELECT TO authenticated USING (true);

CREATE POLICY "Enable write access for authenticated users" ON status_history
  FOR INSERT TO authenticated WITH CHECK (true);

CREATE POLICY "Enable read access for authenticated users" ON episode_statuses
  FOR SELECT TO authenticated USING (true);

-- 更新日時のトリガー
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

-- 便利なビュー：エピソード詳細
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

-- アクセス権の付与
GRANT SELECT ON episode_details TO authenticated;

-- programsテーブルにprogram_idのユニーク制約を追加（存在しない場合）
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint 
    WHERE conname = 'programs_program_id_key'
  ) THEN
    ALTER TABLE programs ADD CONSTRAINT programs_program_id_key UNIQUE (program_id);
  END IF;
END
$$;

-- サンプルデータの挿入（開発環境用）
-- 本番環境では実行しない
DO $$
BEGIN
  -- 既存のサンプルデータがなければ挿入
  IF NOT EXISTS (SELECT 1 FROM programs WHERE program_id LIKE 'LIBRARY-%') THEN
    -- シーズン1のプログラム情報
    INSERT INTO programs (program_id, title, status, series_name, series_type, season, total_episodes)
    VALUES 
      ('LIBRARY-S1-INT', 'リベラルアーツインタビュー', '放送中', 'リベラルアーツインタビュー', 'interview', 1, 6),
      ('LIBRARY-S1-VTR', 'オリオンの会議室', '放送中', 'オリオンの会議室', 'vtr', 1, 15);

    -- シーズン2のプログラム情報
    INSERT INTO programs (program_id, title, status, series_name, series_type, season, total_episodes)
    VALUES 
      ('LIBRARY-S2-INT', '同友会インタビュー', '収録準備中', '同友会インタビュー', 'interview', 2, 5),
      ('LIBRARY-S2-VTR', 'VTRシリーズ シーズン2', '収録準備中', 'VTRシリーズ', 'vtr', 2, 15);
  END IF;
END
$$;