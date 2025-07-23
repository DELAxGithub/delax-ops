/*
  DELA×PM統合システム - 既存データ移行スクリプト
  
  既存のPMplattoとPMliberaryのデータを統合データベースに移行
  プロジェクトタイプによる識別とタグ付けを実施
  
  移行対象:
  - PMplatto: 'platto'タグで移行
  - PMliberary: 'liberary'タグで移行
  
  移行戦略:
  1. 段階的移行による安全性確保
  2. データ検証とエラーハンドリング
  3. 移行ログの詳細記録
  4. ロールバック可能な設計
*/

-- 移行ログテーブルの作成
CREATE TABLE IF NOT EXISTS migration_log (
  id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  migration_phase text NOT NULL,
  table_name text,
  operation text,
  record_count integer,
  status text CHECK (status IN ('started', 'completed', 'failed', 'skipped')) NOT NULL,
  error_message text,
  execution_time interval,
  created_at timestamptz DEFAULT now()
);

-- 移行統計テーブルの作成
CREATE TABLE IF NOT EXISTS migration_stats (
  id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  source_system text CHECK (source_system IN ('platto', 'liberary')) NOT NULL,
  table_name text NOT NULL,
  records_before integer DEFAULT 0,
  records_after integer DEFAULT 0,
  records_migrated integer DEFAULT 0,
  records_failed integer DEFAULT 0,
  migration_completed_at timestamptz,
  created_at timestamptz DEFAULT now()
);

-- 移行ヘルパー関数: ログ記録
CREATE OR REPLACE FUNCTION log_migration(
  phase text,
  table_name text DEFAULT NULL,
  operation text DEFAULT NULL,
  record_count integer DEFAULT NULL,
  status text DEFAULT 'started',
  error_msg text DEFAULT NULL
) RETURNS void AS $$
BEGIN
  INSERT INTO migration_log (migration_phase, table_name, operation, record_count, status, error_message)
  VALUES (phase, table_name, operation, record_count, status, error_msg);
END;
$$ LANGUAGE plpgsql;

-- 移行ヘルパー関数: 統計更新
CREATE OR REPLACE FUNCTION update_migration_stats(
  src_system text,
  tbl_name text,
  before_count integer,
  after_count integer,
  migrated_count integer,
  failed_count integer DEFAULT 0
) RETURNS void AS $$
BEGIN
  INSERT INTO migration_stats (source_system, table_name, records_before, records_after, records_migrated, records_failed, migration_completed_at)
  VALUES (src_system, tbl_name, before_count, after_count, migrated_count, failed_count, now())
  ON CONFLICT (source_system, table_name) DO UPDATE SET
    records_before = EXCLUDED.records_before,
    records_after = EXCLUDED.records_after,
    records_migrated = EXCLUDED.records_migrated,
    records_failed = EXCLUDED.records_failed,
    migration_completed_at = EXCLUDED.migration_completed_at;
END;
$$ LANGUAGE plpgsql;

-- 移行開始ログ
SELECT log_migration('MIGRATION_START', NULL, 'FULL_MIGRATION', NULL, 'started');

-- =============================================================================
-- フェーズ1: PMplattoデータの移行
-- =============================================================================

SELECT log_migration('PHASE_1_PLATTO', NULL, 'PHASE_START', NULL, 'started');

-- PMplatto programs テーブルの移行
DO $$
DECLARE
  before_count integer;
  after_count integer;
  migrated_count integer;
BEGIN
  -- 移行前カウント
  SELECT COUNT(*) INTO before_count FROM programs WHERE project_type = 'platto';
  
  -- PMplattoのprogramsテーブルが存在する場合の移行処理
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'programs_platto') THEN
    -- 既存のPMplattoデータを'platto'タグ付きで移行
    INSERT INTO programs (
      program_id, title, subtitle, current_status, project_type,
      first_air_date, re_air_date, filming_date, complete_date,
      cast1, cast2, director, script_url, pr_text, notes,
      editing_date, mixing_date, first_preview_date, station_preview_date,
      final_package_date, on_air_date, billing_date,
      pr_80text, pr_200text, pr_completed, pr_due_date,
      source_system, migrated_at, legacy_id,
      created_at, updated_at
    )
    SELECT 
      program_id, title, subtitle, status, 'platto',
      first_air_date, re_air_date, filming_date, complete_date,
      cast1, cast2, director, script_url, pr_text, notes,
      editing_date, mixing_date, first_preview_date, station_preview_date,
      final_package_date, on_air_date, billing_date,
      pr_80text, pr_200text, pr_completed, pr_due_date,
      'platto', now(), id::text,
      created_at, updated_at
    FROM programs_platto
    WHERE NOT EXISTS (
      SELECT 1 FROM programs p 
      WHERE p.legacy_id = programs_platto.id::text 
      AND p.source_system = 'platto'
    );
    
    GET DIAGNOSTICS migrated_count = ROW_COUNT;
    
  ELSE
    -- 既存のprogramsテーブルのデータを'platto'として扱う場合
    -- （既存データが既にある場合の処理）
    UPDATE programs 
    SET project_type = 'platto', 
        source_system = 'platto', 
        migrated_at = now()
    WHERE project_type IS NULL OR project_type = 'unified';
    
    GET DIAGNOSTICS migrated_count = ROW_COUNT;
  END IF;
  
  -- 移行後カウント
  SELECT COUNT(*) INTO after_count FROM programs WHERE project_type = 'platto';
  
  -- 統計更新
  PERFORM update_migration_stats('platto', 'programs', before_count, after_count, migrated_count);
  PERFORM log_migration('PHASE_1_PLATTO', 'programs', 'MIGRATE', migrated_count, 'completed');
  
EXCEPTION
  WHEN OTHERS THEN
    PERFORM log_migration('PHASE_1_PLATTO', 'programs', 'MIGRATE', 0, 'failed', SQLERRM);
    RAISE;
END $$;

-- PMplatto calendar_tasks/calendar_events テーブルの移行
DO $$
DECLARE
  before_count integer;
  after_count integer;
  migrated_count integer;
BEGIN
  SELECT COUNT(*) INTO before_count FROM calendar_events WHERE project_type = 'platto';
  
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'calendar_tasks') THEN
    INSERT INTO calendar_events (
      title, event_date, event_type, project_type,
      program_id, description, status,
      source_system, migrated_at, legacy_id,
      created_at, updated_at
    )
    SELECT 
      COALESCE(title, 'プラッとタスク') as title,
      start_date as event_date,
      CASE 
        WHEN task_type = 'broadcast' THEN 'broadcast'
        WHEN task_type = 'recording' THEN 'recording'
        ELSE 'other'
      END as event_type,
      'platto' as project_type,
      program_id,
      description,
      'pending' as status,
      'platto', now(), id::text,
      created_at, updated_at
    FROM calendar_tasks
    WHERE NOT EXISTS (
      SELECT 1 FROM calendar_events ce 
      WHERE ce.legacy_id = calendar_tasks.id::text 
      AND ce.source_system = 'platto'
    );
    
    GET DIAGNOSTICS migrated_count = ROW_COUNT;
  END IF;
  
  SELECT COUNT(*) INTO after_count FROM calendar_events WHERE project_type = 'platto';
  PERFORM update_migration_stats('platto', 'calendar_events', before_count, after_count, migrated_count);
  PERFORM log_migration('PHASE_1_PLATTO', 'calendar_events', 'MIGRATE', migrated_count, 'completed');
  
EXCEPTION
  WHEN OTHERS THEN
    PERFORM log_migration('PHASE_1_PLATTO', 'calendar_events', 'MIGRATE', 0, 'failed', SQLERRM);
    -- カレンダーイベントの移行失敗は致命的ではないため続行
END $$;

SELECT log_migration('PHASE_1_PLATTO', NULL, 'PHASE_END', NULL, 'completed');

-- =============================================================================
-- フェーズ2: PMliberaryデータの移行
-- =============================================================================

SELECT log_migration('PHASE_2_LIBERARY', NULL, 'PHASE_START', NULL, 'started');

-- PMliberary programs テーブルの移行（リベラリー用のプログラム）
DO $$
DECLARE
  before_count integer;
  after_count integer;
  migrated_count integer;
BEGIN
  SELECT COUNT(*) INTO before_count FROM programs WHERE project_type = 'liberary';
  
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'programs_liberary') THEN
    INSERT INTO programs (
      program_id, title, subtitle, current_status, project_type,
      program_type, season_number,
      first_air_date, re_air_date, filming_date, complete_date,
      cast1, cast2, director, producer, script_url, pr_text, notes,
      client_name, budget, broadcast_time,
      source_system, migrated_at, legacy_id,
      created_at, updated_at
    )
    SELECT 
      program_id, title, subtitle, status, 'liberary',
      COALESCE(program_type, 'series'), season_number,
      first_air_date, re_air_date, filming_date, complete_date,
      cast1, cast2, director, producer, script_url, pr_text, notes,
      client_name, budget, broadcast_time,
      'liberary', now(), id::text,
      created_at, updated_at
    FROM programs_liberary
    WHERE NOT EXISTS (
      SELECT 1 FROM programs p 
      WHERE p.legacy_id = programs_liberary.id::text 
      AND p.source_system = 'liberary'
    );
    
    GET DIAGNOSTICS migrated_count = ROW_COUNT;
  END IF;
  
  SELECT COUNT(*) INTO after_count FROM programs WHERE project_type = 'liberary';
  PERFORM update_migration_stats('liberary', 'programs', before_count, after_count, migrated_count);
  PERFORM log_migration('PHASE_2_LIBERARY', 'programs', 'MIGRATE', migrated_count, 'completed');
  
EXCEPTION
  WHEN OTHERS THEN
    PERFORM log_migration('PHASE_2_LIBERARY', 'programs', 'MIGRATE', 0, 'failed', SQLERRM);
    RAISE;
END $$;

-- PMliberary episodes テーブルの移行
DO $$
DECLARE
  before_count integer;
  after_count integer;
  migrated_count integer;
  default_program_id bigint;
BEGIN
  SELECT COUNT(*) INTO before_count FROM episodes WHERE project_type = 'liberary';
  
  -- リベラリー用のデフォルトプログラムを作成/取得
  INSERT INTO programs (title, project_type, program_type, source_system, migrated_at)
  VALUES ('リベラリー統合プログラム', 'liberary', 'series', 'liberary', now())
  ON CONFLICT DO NOTHING;
  
  SELECT id INTO default_program_id 
  FROM programs 
  WHERE title = 'リベラリー統合プログラム' AND project_type = 'liberary' 
  LIMIT 1;
  
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'episodes_liberary') THEN
    INSERT INTO episodes (
      episode_id, program_id, title, episode_type, season, episode_number,
      project_type, script_url, current_status, director, due_date,
      interview_guest, interview_date, interview_location,
      vtr_location, vtr_theme, notes, estimated_duration,
      source_system, migrated_at, legacy_id,
      created_at, updated_at
    )
    SELECT 
      episode_id,
      COALESCE(
        (SELECT id FROM programs WHERE legacy_id = episodes_liberary.program_id::text AND source_system = 'liberary'),
        default_program_id
      ) as program_id,
      title, episode_type, season, episode_number,
      'liberary', script_url, current_status, director, due_date,
      interview_guest, interview_date, interview_location,
      vtr_location, vtr_theme, notes, estimated_duration,
      'liberary', now(), id::text,
      created_at, updated_at
    FROM episodes_liberary
    WHERE NOT EXISTS (
      SELECT 1 FROM episodes e 
      WHERE e.legacy_id = episodes_liberary.id::text 
      AND e.source_system = 'liberary'
    );
    
    GET DIAGNOSTICS migrated_count = ROW_COUNT;
  END IF;
  
  SELECT COUNT(*) INTO after_count FROM episodes WHERE project_type = 'liberary';
  PERFORM update_migration_stats('liberary', 'episodes', before_count, after_count, migrated_count);
  PERFORM log_migration('PHASE_2_LIBERARY', 'episodes', 'MIGRATE', migrated_count, 'completed');
  
EXCEPTION
  WHEN OTHERS THEN
    PERFORM log_migration('PHASE_2_LIBERARY', 'episodes', 'MIGRATE', 0, 'failed', SQLERRM);
    RAISE;
END $$;

-- PMliberary team_events テーブルの移行
DO $$
DECLARE
  before_count integer;
  after_count integer;
  migrated_count integer;
BEGIN
  SELECT COUNT(*) INTO before_count FROM team_events WHERE project_type = 'liberary';
  
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'team_events_liberary') THEN
    INSERT INTO team_events (
      title, event_type, start_date, end_date, description, location,
      participants, project_type,
      source_system, migrated_at, legacy_id,
      created_at, updated_at
    )
    SELECT 
      title, event_type, start_date, end_date, description, location,
      participants, 'liberary',
      'liberary', now(), id::text,
      created_at, updated_at
    FROM team_events_liberary
    WHERE NOT EXISTS (
      SELECT 1 FROM team_events te 
      WHERE te.legacy_id = team_events_liberary.id::text 
      AND te.source_system = 'liberary'
    );
    
    GET DIAGNOSTICS migrated_count = ROW_COUNT;
  END IF;
  
  SELECT COUNT(*) INTO after_count FROM team_events WHERE project_type = 'liberary';
  PERFORM update_migration_stats('liberary', 'team_events', before_count, after_count, migrated_count);
  PERFORM log_migration('PHASE_2_LIBERARY', 'team_events', 'MIGRATE', migrated_count, 'completed');
  
EXCEPTION
  WHEN OTHERS THEN
    PERFORM log_migration('PHASE_2_LIBERARY', 'team_events', 'MIGRATE', 0, 'failed', SQLERRM);
END $$;

-- PMliberary dashboard関連の移行
DO $$
DECLARE
  before_count integer;
  after_count integer;
  migrated_count integer;
BEGIN
  -- dashboard_widgets の移行
  SELECT COUNT(*) INTO before_count FROM dashboard_widgets WHERE project_type = 'liberary';
  
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'dashboard_widgets_liberary') THEN
    INSERT INTO dashboard_widgets (
      user_id, widget_type, title, position_x, position_y, width, height,
      config, visible, project_type,
      source_system, migrated_at,
      created_at, updated_at
    )
    SELECT 
      user_id, widget_type, title, position_x, position_y, width, height,
      config, visible, 'liberary',
      'liberary', now(),
      created_at, updated_at
    FROM dashboard_widgets_liberary;
    
    GET DIAGNOSTICS migrated_count = ROW_COUNT;
  END IF;
  
  SELECT COUNT(*) INTO after_count FROM dashboard_widgets WHERE project_type = 'liberary';
  PERFORM update_migration_stats('liberary', 'dashboard_widgets', before_count, after_count, migrated_count);
  PERFORM log_migration('PHASE_2_LIBERARY', 'dashboard_widgets', 'MIGRATE', migrated_count, 'completed');
  
EXCEPTION
  WHEN OTHERS THEN
    PERFORM log_migration('PHASE_2_LIBERARY', 'dashboard_widgets', 'MIGRATE', 0, 'failed', SQLERRM);
END $$;

SELECT log_migration('PHASE_2_LIBERARY', NULL, 'PHASE_END', NULL, 'completed');

-- =============================================================================
-- フェーズ3: データ検証と整合性チェック
-- =============================================================================

SELECT log_migration('PHASE_3_VALIDATION', NULL, 'PHASE_START', NULL, 'started');

-- 孤立データの検出と修正
DO $$
DECLARE
  orphaned_episodes integer;
  fixed_episodes integer;
BEGIN
  -- program_idが無効なエピソードを検出
  SELECT COUNT(*) INTO orphaned_episodes 
  FROM episodes e 
  WHERE e.program_id IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM programs p WHERE p.id = e.program_id);
  
  IF orphaned_episodes > 0 THEN
    -- デフォルトプログラムに関連付け
    UPDATE episodes 
    SET program_id = (
      SELECT id FROM programs 
      WHERE title = 'リベラリー統合プログラム' AND project_type = 'liberary' 
      LIMIT 1
    )
    WHERE program_id IS NOT NULL 
    AND NOT EXISTS (SELECT 1 FROM programs p WHERE p.id = episodes.program_id);
    
    GET DIAGNOSTICS fixed_episodes = ROW_COUNT;
    
    PERFORM log_migration('PHASE_3_VALIDATION', 'episodes', 'FIX_ORPHANED', fixed_episodes, 'completed');
  END IF;
  
EXCEPTION
  WHEN OTHERS THEN
    PERFORM log_migration('PHASE_3_VALIDATION', 'episodes', 'FIX_ORPHANED', 0, 'failed', SQLERRM);
END $$;

-- ステータス整合性の検証
DO $$
DECLARE
  invalid_program_statuses integer;
  invalid_episode_statuses integer;
BEGIN
  -- 無効な番組ステータスを検出
  SELECT COUNT(*) INTO invalid_program_statuses
  FROM programs p
  WHERE p.current_status IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM program_statuses ps WHERE ps.status_name = p.current_status);
  
  -- 無効なエピソードステータスを検出
  SELECT COUNT(*) INTO invalid_episode_statuses
  FROM episodes e
  WHERE e.current_status IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM episode_statuses es WHERE es.status_name = e.current_status);
  
  IF invalid_program_statuses > 0 OR invalid_episode_statuses > 0 THEN
    PERFORM log_migration('PHASE_3_VALIDATION', 'status_validation', 'INVALID_STATUSES', 
                         invalid_program_statuses + invalid_episode_statuses, 'completed',
                         format('Programs: %s, Episodes: %s', invalid_program_statuses, invalid_episode_statuses));
  END IF;
  
EXCEPTION
  WHEN OTHERS THEN
    PERFORM log_migration('PHASE_3_VALIDATION', 'status_validation', 'VALIDATE', 0, 'failed', SQLERRM);
END $$;

SELECT log_migration('PHASE_3_VALIDATION', NULL, 'PHASE_END', NULL, 'completed');

-- =============================================================================
-- フェーズ4: 最適化とメンテナンス
-- =============================================================================

SELECT log_migration('PHASE_4_OPTIMIZATION', NULL, 'PHASE_START', NULL, 'started');

-- インデックス再構築（既に存在する場合はスキップ）
DO $$
BEGIN
  -- 統計情報の更新
  ANALYZE programs;
  ANALYZE episodes;
  ANALYZE calendar_events;
  ANALYZE team_events;
  ANALYZE status_history;
  ANALYZE dashboard_widgets;
  ANALYZE dashboard_memos;
  
  PERFORM log_migration('PHASE_4_OPTIMIZATION', 'all_tables', 'ANALYZE', NULL, 'completed');
  
EXCEPTION
  WHEN OTHERS THEN
    PERFORM log_migration('PHASE_4_OPTIMIZATION', 'all_tables', 'ANALYZE', 0, 'failed', SQLERRM);
END $$;

SELECT log_migration('PHASE_4_OPTIMIZATION', NULL, 'PHASE_END', NULL, 'completed');

-- =============================================================================
-- 移行完了と統計レポート
-- =============================================================================

SELECT log_migration('MIGRATION_COMPLETE', NULL, 'FULL_MIGRATION', NULL, 'completed');

-- 移行統計の最終レポート
SELECT 
  '=== DELA×PM統合システム データ移行完了レポート ===' as report_title;

SELECT 
  source_system,
  table_name,
  records_before,
  records_after,
  records_migrated,
  records_failed,
  migration_completed_at
FROM migration_stats
ORDER BY source_system, table_name;

-- 移行ログの要約
SELECT 
  migration_phase,
  COUNT(*) as operations,
  COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
  COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed
FROM migration_log
GROUP BY migration_phase
ORDER BY created_at;

-- 最終確認クエリ
SELECT 
  'programs' as table_name,
  project_type,
  COUNT(*) as record_count
FROM programs
GROUP BY project_type
UNION ALL
SELECT 
  'episodes' as table_name,
  project_type,
  COUNT(*) as record_count
FROM episodes
GROUP BY project_type
UNION ALL
SELECT 
  'calendar_events' as table_name,
  project_type,
  COUNT(*) as record_count
FROM calendar_events
GROUP BY project_type
ORDER BY table_name, project_type;

-- 移行ヘルパー関数のクリーンアップ（本番環境では実行を検討）
-- DROP FUNCTION IF EXISTS log_migration(text, text, text, integer, text, text);
-- DROP FUNCTION IF EXISTS update_migration_stats(text, text, integer, integer, integer, integer);