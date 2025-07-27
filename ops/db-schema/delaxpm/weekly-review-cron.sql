-- 週次レビューの自動実行設定
-- 毎週月曜日の9:00（JST）に実行

-- pg_cronが有効でない場合は拡張機能を追加
-- CREATE EXTENSION IF NOT EXISTS pg_cron;

-- 既存のジョブがあれば削除
SELECT cron.unschedule('weekly-review-job');

-- 週次レビューのスケジュール設定
-- 毎週月曜日の0:00（UTC）= 日本時間9:00に実行
SELECT cron.schedule(
  'weekly-review-job',
  '0 0 * * 1',  -- 毎週月曜日 0:00 UTC (JST 9:00)
  $$
  SELECT net.http_post(
    url := 'https://pfrzcteapmwufnovmmfc.supabase.co/functions/v1/weekly-review',
    headers := '{"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBmcnpjdGVhcG13dWZub3ZtbWZjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTMwMDAwNTAsImV4cCI6MjA2ODU3NjA1MH0.We0I0UDqKfS9jPSzDvWtQmB7na8YvCld6_Kko4uBCdU"}'::jsonb
  );
  $$
);

-- スケジュール確認クエリ
-- SELECT * FROM cron.job WHERE jobname = 'weekly-review-job';

-- 手動実行用クエリ（テスト用）
/*
SELECT net.http_post(
  url := 'https://pfrzcteapmwufnovmmfc.supabase.co/functions/v1/weekly-review',
  headers := '{"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBmcnpjdGVhcG13dWZub3ZtbWZjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTMwMDAwNTAsImV4cCI6MjA2ODU3NjA1MH0.We0I0UDqKfS9jPSzDvWtQmB7na8YvCld6_Kko4uBCdU"}'::jsonb
);
*/

-- スケジュール削除用（必要な場合）
-- SELECT cron.unschedule('weekly-review-job');