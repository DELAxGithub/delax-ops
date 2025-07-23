-- ==============================================================================
-- DELA×PM統合システム - 手動移行SQLスクリプト
-- ==============================================================================
-- 
-- 実行方法:
-- 1. PMliberaryのSupabase管理画面にログイン
-- 2. SQL Editorで本スクリプトを実行
-- 3. 段階的に実行して結果を確認
--
-- ==============================================================================

-- ステップ1: スキーマ拡張（PMliberaryデータベースに実行）
-- ==============================================================================

-- 1.1 project_type列の追加（プロジェクト識別用）
ALTER TABLE programs 
ADD COLUMN IF NOT EXISTS project_type text DEFAULT 'liberary';

-- 既存データをliberaryとしてマーク
UPDATE programs 
SET project_type = 'liberary' 
WHERE project_type IS NULL;

-- NOT NULL制約とCHECK制約の追加
ALTER TABLE programs 
ALTER COLUMN project_type SET NOT NULL;

ALTER TABLE programs 
ADD CONSTRAINT programs_project_type_check 
CHECK (project_type IN ('platto', 'liberary', 'unified'));

-- 1.2 PMplatto用フィールドの追加
ALTER TABLE programs 
ADD COLUMN IF NOT EXISTS pr_80text text,
ADD COLUMN IF NOT EXISTS pr_200text text,
ADD COLUMN IF NOT EXISTS source_system text,
ADD COLUMN IF NOT EXISTS migrated_at timestamptz,
ADD COLUMN IF NOT EXISTS legacy_id text;

-- 1.3 インデックスの作成
CREATE INDEX IF NOT EXISTS idx_programs_project_type ON programs(project_type);
CREATE INDEX IF NOT EXISTS idx_programs_source_system ON programs(source_system);
CREATE INDEX IF NOT EXISTS idx_programs_legacy_id ON programs(legacy_id);

-- 1.4 確認クエリ
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'programs' 
AND column_name IN ('project_type', 'pr_80text', 'pr_200text', 'source_system', 'migrated_at', 'legacy_id')
ORDER BY column_name;

-- ==============================================================================
-- ステップ2: PMplattoデータの移行
-- ==============================================================================

-- 2.1 PMplattoプログラムデータの挿入
-- 以下のINSERT文をバックアップデータに基づいて実行

-- サンプル1: つながる時代のわかりあえなさ
INSERT INTO programs (
  program_id, title, subtitle, status, project_type,
  first_air_date, re_air_date, filming_date, complete_date,
  cast1, cast2, script_url, pr_text, notes,
  pr_completed, pr_80text, pr_200text,
  source_system, migrated_at, legacy_id,
  created_at, updated_at
) VALUES (
  'PLAT_008', 
  'つながる時代のわかりあえなさ', 
  '@国立競技場', 
  '放送済み', 
  'platto',
  '2025-03-08', 
  '2025-05-05', 
  '2025-02-07', 
  '2025-02-28',
  '九段 理江', 
  'ドミニク・チェン', 
  NULL, 
  NULL, 
  '[Migrated from PMplatto]',
  true, 
  NULL, 
  NULL,
  'pmplatto', 
  now(), 
  '8',
  now(), 
  now()
);

-- サンプル2: 書くこと、編むこと
INSERT INTO programs (
  program_id, title, subtitle, status, project_type,
  first_air_date, re_air_date, filming_date, complete_date,
  cast1, cast2, pr_completed,
  source_system, migrated_at, legacy_id,
  created_at, updated_at
) VALUES (
  'PLAT_015', 
  '書くこと、編むこと', 
  '@羊毛倉庫', 
  'OA済', 
  'platto',
  '2025-04-26', 
  '2025-06-23', 
  '2025-03-26', 
  '2025-04-19',
  '青山 七恵', 
  '三國万里子', 
  true,
  'pmplatto', 
  now(), 
  '15',
  now(), 
  now()
);

-- 残りの30件のPMplattoプログラムデータ...
-- [実際のバックアップデータに基づいて追加のINSERT文を実行]

-- 2.2 移行結果の確認
SELECT 
  project_type, 
  COUNT(*) as program_count,
  MIN(created_at) as oldest_record,
  MAX(created_at) as newest_record
FROM programs 
GROUP BY project_type
ORDER BY project_type;

-- ==============================================================================
-- ステップ3: PMplattoカレンダータスクの移行（オプション）
-- ==============================================================================

-- 3.1 calendar_tasksテーブルの作成（存在しない場合）
CREATE TABLE IF NOT EXISTS calendar_tasks (
  id bigserial PRIMARY KEY,
  program_id text NOT NULL,
  title text NOT NULL,
  task_type text,
  start_date date,
  end_date date,
  description text,
  project_type text DEFAULT 'platto',
  source_system text DEFAULT 'pmplatto',
  migrated_at timestamptz DEFAULT now(),
  legacy_id text,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- 3.2 インデックスの作成
CREATE INDEX IF NOT EXISTS idx_calendar_tasks_program_id ON calendar_tasks(program_id);
CREATE INDEX IF NOT EXISTS idx_calendar_tasks_project_type ON calendar_tasks(project_type);
CREATE INDEX IF NOT EXISTS idx_calendar_tasks_start_date ON calendar_tasks(start_date);

-- 3.3 サンプルカレンダータスクの挿入
INSERT INTO calendar_tasks (
  program_id, title, task_type, start_date, end_date, description,
  project_type, source_system, legacy_id
) VALUES 
  ('PLAT_008', '番組放送日', 'broadcast', '2025-03-08', '2025-03-08', '初回放送', 'platto', 'pmplatto', '1'),
  ('PLAT_008', '再放送日', 'rebroadcast', '2025-05-05', '2025-05-05', '再放送', 'platto', 'pmplatto', '2');

-- ==============================================================================
-- ステップ4: 統合データの検証
-- ==============================================================================

-- 4.1 統合後のプログラム数確認
SELECT 
  'Total Programs' as metric,
  COUNT(*) as count
FROM programs
UNION ALL
SELECT 
  'PMplatto Programs' as metric,
  COUNT(*) as count
FROM programs WHERE project_type = 'platto'
UNION ALL
SELECT 
  'PMliberary Programs' as metric,
  COUNT(*) as count
FROM programs WHERE project_type = 'liberary';

-- 4.2 PMplattoデータのサンプル確認
SELECT 
  program_id,
  title,
  subtitle,
  status,
  first_air_date,
  cast1,
  cast2,
  project_type,
  source_system
FROM programs 
WHERE project_type = 'platto'
ORDER BY program_id
LIMIT 5;

-- 4.3 データ整合性チェック
SELECT 
  'Programs without program_id' as check_item,
  COUNT(*) as issue_count
FROM programs WHERE program_id IS NULL
UNION ALL
SELECT 
  'Programs without title' as check_item,
  COUNT(*) as issue_count
FROM programs WHERE title IS NULL OR title = ''
UNION ALL
SELECT 
  'Duplicate program_ids' as check_item,
  COUNT(*) - COUNT(DISTINCT program_id) as issue_count
FROM programs;

-- ==============================================================================
-- ステップ5: RLS（Row Level Security）設定（必要に応じて）
-- ==============================================================================

-- 5.1 programsテーブルのRLSポリシー更新
-- 既存のポリシーに影響しないよう、project_typeに関わらず全ユーザーがアクセス可能に
CREATE POLICY "Allow read access to all programs" ON programs
  FOR SELECT TO authenticated USING (true);

CREATE POLICY "Allow write access to all programs" ON programs
  FOR ALL TO authenticated USING (true) WITH CHECK (true);

-- ==============================================================================
-- 移行完了メッセージ
-- ==============================================================================

-- 移行完了後、以下のメッセージが表示されることを確認:
-- 'PMplatto data migration completed successfully!'

SELECT 'PMplatto data migration completed successfully!' as status;

-- ==============================================================================
-- ロールバック手順（必要な場合）
-- ==============================================================================

-- 移行を取り消す場合は以下を実行:
/*
-- PMplattoデータの削除
DELETE FROM programs WHERE project_type = 'platto';
DELETE FROM calendar_tasks WHERE project_type = 'platto';

-- 追加した列の削除（注意: 既存データへの影響を確認）
ALTER TABLE programs 
DROP COLUMN IF EXISTS project_type,
DROP COLUMN IF EXISTS pr_80text,
DROP COLUMN IF EXISTS pr_200text,
DROP COLUMN IF EXISTS source_system,
DROP COLUMN IF EXISTS migrated_at,
DROP COLUMN IF EXISTS legacy_id;

-- インデックスの削除
DROP INDEX IF EXISTS idx_programs_project_type;
DROP INDEX IF EXISTS idx_programs_source_system;
DROP INDEX IF EXISTS idx_programs_legacy_id;

-- calendar_tasksテーブルの削除（必要な場合）
DROP TABLE IF EXISTS calendar_tasks;
*/