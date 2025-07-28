/*
  DELA×PM 統合データベース設計
  
  プラッと進捗すごろく + リベラリーの統合版
  
  主要テーブル:
  1. programs - 番組マスター（シーズン管理含む）
  2. episodes - エピソード管理（プラッと・リベラリー統合）
  3. program_statuses - 番組ステータスマスター
  4. episode_statuses - エピソードステータスマスター
  5. calendar_events - カレンダー・イベント管理
  6. team_events - チームイベント
  7. users - ユーザー管理
  8. status_history - ステータス変更履歴
  9. dashboard_widgets - ダッシュボード設定
  10. dashboard_memos - ダッシュボードメモ
*/

-- ユーザー管理テーブル
CREATE TABLE IF NOT EXISTS users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email text UNIQUE NOT NULL,
  name text NOT NULL,
  role text CHECK (role IN ('admin', 'producer', 'director', 'editor', 'viewer')) DEFAULT 'viewer',
  department text,
  avatar_url text,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- 番組ステータスマスター
CREATE TABLE IF NOT EXISTS program_statuses (
  id serial PRIMARY KEY,
  status_name text NOT NULL UNIQUE,
  status_order integer NOT NULL,
  color_code text,
  description text,
  created_at timestamptz DEFAULT now()
);

-- 番組ステータスの初期データ
INSERT INTO program_statuses (status_name, status_order, color_code, description) VALUES
  ('キャスティング中', 1, '#6B7280', '出演者を決定している段階'),
  ('ロケ済', 2, '#8B5CF6', 'ロケーション撮影が完了'),
  ('VE済', 3, '#6366F1', 'ビデオ編集が完了'),
  ('MA済', 4, '#3B82F6', '音声ミキシングが完了'),
  ('初号試写済', 5, '#06B6D4', '最初の試写が完了'),
  ('局プレ済', 6, '#10B981', '放送局でのプレビューが完了'),
  ('完パケ済', 7, '#84CC16', '最終パッケージが完了'),
  ('OA済', 8, '#EAB308', '放送が完了'),
  ('請求済', 9, '#22C55E', '請求処理が完了')
ON CONFLICT (status_name) DO NOTHING;

-- エピソードステータスマスター
CREATE TABLE IF NOT EXISTS episode_statuses (
  id serial PRIMARY KEY,
  status_name text NOT NULL UNIQUE,
  status_order integer NOT NULL,
  color_code text,
  description text,
  created_at timestamptz DEFAULT now()
);

-- エピソードステータスの初期データ
INSERT INTO episode_statuses (status_name, status_order, color_code, description) VALUES
  ('台本作成中', 1, '#6B7280', '台本を作成している段階'),
  ('素材準備', 2, '#8B5CF6', '撮影・収録に必要な素材を準備中'),
  ('素材確定', 3, '#6366F1', '使用する素材が確定済み'),
  ('編集中', 4, '#3B82F6', 'ビデオ編集作業中'),
  ('試写1', 5, '#06B6D4', '第一回試写完了'),
  ('修正1', 6, '#10B981', '試写後の修正完了'),
  ('MA中', 7, '#84CC16', '音声ミキシング作業中'),
  ('初稿完成', 8, '#EAB308', '初稿が完成'),
  ('修正中', 9, '#F59E0B', '最終修正作業中'),
  ('完パケ納品', 10, '#22C55E', '最終納品完了')
ON CONFLICT (status_name) DO NOTHING;

-- 番組マスターテーブル（統合版）
CREATE TABLE IF NOT EXISTS programs (
  id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  program_id text,
  title text NOT NULL,
  subtitle text,
  program_type text CHECK (program_type IN ('single', 'series', 'season')) DEFAULT 'single',
  season_number integer,
  current_status text REFERENCES program_statuses(status_name),
  
  -- 日程関連
  first_air_date date,
  re_air_date date,
  filming_date date,
  complete_date date,
  
  -- スタッフ・キャスト
  cast1 text,
  cast2 text,
  director text,
  producer text,
  
  -- 制作情報
  script_url text,
  pr_text text,
  notes text,
  client_name text,
  budget decimal,
  broadcast_time text,
  
  -- 進捗日程（プラッと用）
  editing_date date,
  mixing_date date,
  first_preview_date date,
  station_preview_date date,
  final_package_date date,
  on_air_date date,
  billing_date date,
  
  -- システム管理
  assigned_users text[],
  created_by uuid REFERENCES users(id),
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- エピソードテーブル（統合版）
CREATE TABLE IF NOT EXISTS episodes (
  id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  episode_id text NOT NULL UNIQUE,
  program_id bigint REFERENCES programs(id) ON DELETE CASCADE,
  title text NOT NULL,
  episode_type text CHECK (episode_type IN ('interview', 'vtr', 'regular')) NOT NULL,
  season integer DEFAULT 1,
  episode_number integer NOT NULL,
  
  -- 制作情報
  script_url text,
  current_status text REFERENCES episode_statuses(status_name),
  director text,
  due_date date,
  
  -- インタビュー用項目
  interview_guest text,
  interview_date date,
  interview_location text,
  
  -- VTR用項目
  vtr_location text,
  vtr_theme text,
  
  -- その他
  notes text,
  estimated_duration interval,
  assigned_users text[],
  
  -- システム管理
  created_by uuid REFERENCES users(id),
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  
  UNIQUE(program_id, season, episode_number)
);

-- カレンダーイベントテーブル
CREATE TABLE IF NOT EXISTS calendar_events (
  id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  title text NOT NULL,
  event_date date NOT NULL,
  event_type text CHECK (event_type IN ('broadcast', 'rerun', 'recording', 'deadline', 'meeting', 'other')) NOT NULL,
  
  -- 関連付け
  program_id bigint REFERENCES programs(id) ON DELETE CASCADE,
  episode_id bigint REFERENCES episodes(id) ON DELETE CASCADE,
  
  -- 詳細情報
  description text,
  location text,
  start_time time,
  end_time time,
  status text CHECK (status IN ('pending', 'confirmed', 'completed', 'cancelled')) DEFAULT 'pending',
  
  -- 参加者
  assigned_users text[],
  
  -- システム管理
  created_by uuid REFERENCES users(id),
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- チームイベントテーブル
CREATE TABLE IF NOT EXISTS team_events (
  id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  title text NOT NULL,
  event_type text CHECK (event_type IN ('meeting', 'deadline', 'training', 'other')) NOT NULL,
  start_date date NOT NULL,
  end_date date,
  description text,
  location text,
  participants text[],
  created_by uuid REFERENCES users(id),
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- ステータス変更履歴テーブル
CREATE TABLE IF NOT EXISTS status_history (
  id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  target_type text CHECK (target_type IN ('program', 'episode')) NOT NULL,
  target_id bigint NOT NULL,
  old_status text,
  new_status text NOT NULL,
  changed_by uuid REFERENCES users(id),
  changed_at timestamptz DEFAULT now(),
  notes text
);

-- ダッシュボードウィジェット設定
CREATE TABLE IF NOT EXISTS dashboard_widgets (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES users(id) ON DELETE CASCADE,
  widget_type text CHECK (widget_type IN ('tasks', 'schedule', 'memo', 'quicklinks', 'stats')) NOT NULL,
  title text NOT NULL,
  position_x integer DEFAULT 0,
  position_y integer DEFAULT 0,
  width integer DEFAULT 1,
  height integer DEFAULT 1,
  config jsonb,
  visible boolean DEFAULT true,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- ダッシュボードメモ
CREATE TABLE IF NOT EXISTS dashboard_memos (
  id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  title text NOT NULL,
  content text NOT NULL,
  priority text CHECK (priority IN ('low', 'medium', 'high')) DEFAULT 'medium',
  created_by uuid REFERENCES users(id),
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- トリガー関数: updated_at自動更新
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- updated_atトリガーの設定
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_programs_updated_at BEFORE UPDATE ON programs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_episodes_updated_at BEFORE UPDATE ON episodes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_calendar_events_updated_at BEFORE UPDATE ON calendar_events
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_team_events_updated_at BEFORE UPDATE ON team_events
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_dashboard_widgets_updated_at BEFORE UPDATE ON dashboard_widgets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_dashboard_memos_updated_at BEFORE UPDATE ON dashboard_memos
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ステータス変更履歴を自動記録するトリガー関数
CREATE OR REPLACE FUNCTION record_status_change()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_TABLE_NAME = 'programs' AND OLD.current_status IS DISTINCT FROM NEW.current_status THEN
        INSERT INTO status_history (target_type, target_id, old_status, new_status, changed_by)
        VALUES ('program', NEW.id, OLD.current_status, NEW.current_status, NEW.created_by);
    ELSIF TG_TABLE_NAME = 'episodes' AND OLD.current_status IS DISTINCT FROM NEW.current_status THEN
        INSERT INTO status_history (target_type, target_id, old_status, new_status, changed_by)
        VALUES ('episode', NEW.id, OLD.current_status, NEW.current_status, NEW.created_by);
    END IF;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- ステータス変更履歴トリガー
CREATE TRIGGER record_program_status_change AFTER UPDATE ON programs
    FOR EACH ROW EXECUTE FUNCTION record_status_change();

CREATE TRIGGER record_episode_status_change AFTER UPDATE ON episodes
    FOR EACH ROW EXECUTE FUNCTION record_status_change();

-- インデックスの作成
CREATE INDEX IF NOT EXISTS idx_programs_status ON programs(current_status);
CREATE INDEX IF NOT EXISTS idx_episodes_status ON episodes(current_status);
CREATE INDEX IF NOT EXISTS idx_calendar_events_date ON calendar_events(event_date);
CREATE INDEX IF NOT EXISTS idx_episodes_program_id ON episodes(program_id);
CREATE INDEX IF NOT EXISTS idx_status_history_target ON status_history(target_type, target_id);

-- RLS (Row Level Security) の有効化
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE programs ENABLE ROW LEVEL SECURITY;
ALTER TABLE episodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE calendar_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE team_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE status_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE dashboard_widgets ENABLE ROW LEVEL SECURITY;
ALTER TABLE dashboard_memos ENABLE ROW LEVEL SECURITY;

-- RLS ポリシーの設定（認証されたユーザーのみアクセス可能）
CREATE POLICY "Users can view all users" ON users FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "Users can update their own profile" ON users FOR UPDATE USING (auth.uid() = id);

CREATE POLICY "Authenticated users can access programs" ON programs FOR ALL USING (auth.role() = 'authenticated');
CREATE POLICY "Authenticated users can access episodes" ON episodes FOR ALL USING (auth.role() = 'authenticated');
CREATE POLICY "Authenticated users can access calendar_events" ON calendar_events FOR ALL USING (auth.role() = 'authenticated');
CREATE POLICY "Authenticated users can access team_events" ON team_events FOR ALL USING (auth.role() = 'authenticated');
CREATE POLICY "Authenticated users can access status_history" ON status_history FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "Authenticated users can access dashboard_widgets" ON dashboard_widgets FOR ALL USING (auth.role() = 'authenticated');
CREATE POLICY "Authenticated users can access dashboard_memos" ON dashboard_memos FOR ALL USING (auth.role() = 'authenticated');