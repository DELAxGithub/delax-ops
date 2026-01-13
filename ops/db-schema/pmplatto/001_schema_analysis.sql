/*
  PMPlatto vs PMLibrary スキーマ差分分析
  
  目的: PMPlattoのSupabaseをPMLibraryレベルに更新するための差分を特定
*/

-- 現在のPMPlattoスキーマ（基準）
-- programs テーブル（基本構成）

-- PMLibraryで追加されているフィールド（PMPlattoに追加が必要）
ALTER TABLE programs 
  ADD COLUMN IF NOT EXISTS series_name text,
  ADD COLUMN IF NOT EXISTS series_type text CHECK (series_type IN ('interview', 'vtr', NULL)),
  ADD COLUMN IF NOT EXISTS season integer,
  ADD COLUMN IF NOT EXISTS total_episodes integer;

-- PMLibraryに存在する追加テーブル（PMPlattoに新規作成が必要）

-- 1. episode_statuses テーブル（ステータスマスター）
CREATE TABLE IF NOT EXISTS episode_statuses (
  id serial PRIMARY KEY,
  status_name text NOT NULL UNIQUE,
  status_order integer NOT NULL,
  color_code text,
  created_at timestamptz DEFAULT now()
);

-- 2. episodes テーブル（エピソード管理）
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

-- 3. status_history テーブル（ステータス履歴）
CREATE TABLE IF NOT EXISTS status_history (
  id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  episode_id bigint REFERENCES episodes(id) ON DELETE CASCADE,
  old_status text,
  new_status text,
  changed_by uuid REFERENCES auth.users(id),
  change_reason text,
  changed_at timestamptz DEFAULT now()
);

-- 4. calendar_tasks テーブル（既存のcalendar_tasksに追加フィールド）
-- PMPlattoには基本のcalendar_tasksが存在するが、チームイベント機能が不足
ALTER TABLE calendar_tasks 
  ADD COLUMN IF NOT EXISTS meeting_url text,
  ADD COLUMN IF NOT EXISTS description text,
  ADD COLUMN IF NOT EXISTS is_team_event boolean DEFAULT false;

-- 制約とインデックスの追加
CREATE INDEX IF NOT EXISTS idx_episodes_episode_id ON episodes(episode_id);
CREATE INDEX IF NOT EXISTS idx_episodes_season ON episodes(season);
CREATE INDEX IF NOT EXISTS idx_episodes_current_status ON episodes(current_status);
CREATE INDEX IF NOT EXISTS idx_episodes_due_date ON episodes(due_date);
CREATE INDEX IF NOT EXISTS idx_episodes_episode_type ON episodes(episode_type);
CREATE INDEX IF NOT EXISTS idx_status_history_episode ON status_history(episode_id);
CREATE INDEX IF NOT EXISTS idx_status_history_changed_at ON status_history(changed_at);
CREATE INDEX IF NOT EXISTS idx_calendar_tasks_team_event ON calendar_tasks (is_team_event);

-- 差分サマリー
/*
追加が必要なもの:
1. programs テーブルに4つのフィールド追加
2. episode_statuses テーブル新規作成
3. episodes テーブル新規作成  
4. status_history テーブル新規作成
5. calendar_tasks テーブルに3つのフィールド追加
6. 各種インデックス、制約、トリガーの追加
7. RLSポリシーの追加
8. ビューと関数の追加

影響度: 中程度
- 既存データに影響なし（フィールド追加のみ）
- 新機能用テーブルの追加
- 既存アプリケーションとの互換性維持
*/