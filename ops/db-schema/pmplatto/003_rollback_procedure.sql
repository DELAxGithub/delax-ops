/*
  PMPlatto Schema Migration Rollback Procedure
  
  スキーマ移行で問題が発生した場合のロールバック手順
  
  注意: このスクリプトは移行後に問題が発生した場合のみ使用してください
*/

-- ==========================================
-- ロールバック手順（緊急時のみ使用）
-- ==========================================

-- Step 1: 新しく追加されたテーブルを削除
-- 注意: これらのテーブルにデータが入っている場合は失われます

BEGIN;

-- トリガーを削除
DROP TRIGGER IF EXISTS record_episode_status_change ON episodes;
DROP TRIGGER IF EXISTS update_episodes_updated_at ON episodes;

-- ビューを削除
DROP VIEW IF EXISTS episode_details;

-- 関数を削除
DROP FUNCTION IF EXISTS record_status_change();
DROP FUNCTION IF EXISTS update_episode_updated_at();

-- RLSポリシーを削除
DROP POLICY IF EXISTS "Enable read access for authenticated users" ON episodes;
DROP POLICY IF EXISTS "Enable write access for authenticated users" ON episodes;
DROP POLICY IF EXISTS "Enable read access for authenticated users" ON status_history;
DROP POLICY IF EXISTS "Enable write access for authenticated users" ON status_history;
DROP POLICY IF EXISTS "Enable read access for authenticated users" ON episode_statuses;

-- 新しく追加されたテーブルを削除（順序に注意）
DROP TABLE IF EXISTS status_history CASCADE;
DROP TABLE IF EXISTS episodes CASCADE;
DROP TABLE IF EXISTS episode_statuses CASCADE;

-- programs テーブルから新しいフィールドを削除
ALTER TABLE programs 
  DROP COLUMN IF EXISTS series_name,
  DROP COLUMN IF EXISTS series_type,
  DROP COLUMN IF EXISTS season,
  DROP COLUMN IF EXISTS total_episodes;

-- calendar_tasks テーブルから新しいフィールドを削除
ALTER TABLE calendar_tasks 
  DROP COLUMN IF EXISTS meeting_url,
  DROP COLUMN IF EXISTS description,
  DROP COLUMN IF EXISTS is_team_event;

-- 制約を削除
ALTER TABLE calendar_tasks DROP CONSTRAINT IF EXISTS valid_meeting_url;
ALTER TABLE programs DROP CONSTRAINT IF EXISTS programs_series_type_check;

COMMIT;

-- ==========================================
-- ロールバック確認クエリ
-- ==========================================

-- 1. 削除されたテーブルが存在しないことを確認
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_name IN ('episodes', 'status_history', 'episode_statuses');
-- 結果: 0行が返されることを確認

-- 2. programs テーブルが元の状態に戻っていることを確認
SELECT column_name, data_type, is_nullable
FROM information_schema.columns 
WHERE table_name = 'programs' AND table_schema = 'public'
  AND column_name IN ('series_name', 'series_type', 'season', 'total_episodes');
-- 結果: 0行が返されることを確認

-- 3. calendar_tasks テーブルが元の状態に戻っていることを確認
SELECT column_name, data_type, is_nullable
FROM information_schema.columns 
WHERE table_name = 'calendar_tasks' AND table_schema = 'public'
  AND column_name IN ('meeting_url', 'description', 'is_team_event');
-- 結果: 0行が返されることを確認

-- ==========================================
-- バックアップからの完全復旧手順
-- ==========================================

/*
より安全なロールバック方法：

1. 移行前のバックアップファイルを使用した完全復旧

# Step 1: 現在のデータベースを削除
supabase db reset --project-ref YOUR_PROJECT_REF

# Step 2: バックアップから復旧
supabase db exec --project-ref YOUR_PROJECT_REF --file backups/YYYYMMDD_HHMMSS/pmplatto_full_backup.sql

# Step 3: 復旧確認
supabase db exec --project-ref YOUR_PROJECT_REF --file - <<SQL
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';
SQL

この方法の利点:
- 完全に元の状態に戻せる
- データの整合性が保証される
- 部分的な問題による不整合を回避

この方法の欠点:
- 移行後に作成されたデータは失われる
- 復旧に時間がかかる
*/

-- ==========================================
-- ロールバック実行チェックリスト
-- ==========================================

/*
ロールバック前に確認すること:
□ 移行後に新しいデータが作成されていないか確認
□ ロールバックの必要性を再検討
□ バックアップファイルの存在確認
□ ユーザーへの事前通知

ロールバック後に確認すること:
□ 全てのテーブルが元の状態に戻っている
□ 既存データが保持されている
□ アプリケーションが正常に動作する
□ ユーザーへの復旧完了通知

緊急連絡先:
- 開発チーム: [連絡先を記載]
- インフラ担当: [連絡先を記載]
*/