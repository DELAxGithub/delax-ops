-- ============================================================================
-- DELA×PM テーブル名整理マイグレーション
-- 作成日: 2025-07-28
-- 目的: データベース設計改善 - Phase 2
-- 概念とテーブル名の一致（programs → episodes）
-- ============================================================================

-- =========================================
-- STEP 1: 既存の未使用episodesテーブル削除
-- =========================================

-- 1.1 既存のepisodesテーブルを削除（未使用のため）
DROP TABLE IF EXISTS episodes CASCADE;

-- =========================================
-- STEP 2: programsテーブルをepisodesにリネーム
-- =========================================

-- 2.1 テーブル名変更
ALTER TABLE programs RENAME TO episodes;

-- 2.2 シーケンス名変更
ALTER SEQUENCE programs_id_seq RENAME TO episodes_id_seq;

-- =========================================
-- STEP 3: インデックス名変更
-- =========================================

-- 3.1 基本インデックス名変更
ALTER INDEX IF EXISTS idx_programs_program_id RENAME TO idx_episodes_program_id;
ALTER INDEX IF EXISTS idx_programs_title RENAME TO idx_episodes_title;
ALTER INDEX IF EXISTS idx_programs_status RENAME TO idx_episodes_status;
ALTER INDEX IF EXISTS idx_programs_created_at RENAME TO idx_episodes_created_at;
ALTER INDEX IF EXISTS idx_programs_updated_at RENAME TO idx_episodes_updated_at;

-- 3.2 検索用インデックス名変更
ALTER INDEX IF EXISTS idx_programs_notes_gin RENAME TO idx_episodes_notes_gin;
ALTER INDEX IF EXISTS idx_programs_notes_platto RENAME TO idx_episodes_notes_platto;
ALTER INDEX IF EXISTS idx_programs_notes_liberary RENAME TO idx_episodes_notes_liberary;

-- =========================================
-- STEP 4: RLSポリシー名変更
-- =========================================

-- 4.1 既存のprogramsポリシーを削除
DROP POLICY IF EXISTS "programs_full_access" ON episodes;
DROP POLICY IF EXISTS "programs_select_policy" ON episodes;
DROP POLICY IF EXISTS "programs_insert_policy" ON episodes;
DROP POLICY IF EXISTS "programs_update_policy" ON episodes;
DROP POLICY IF EXISTS "programs_delete_policy" ON episodes;

-- 4.2 episodes用のRLSポリシーを作成
CREATE POLICY "episodes_full_access" ON episodes FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "episodes_select_policy" ON episodes FOR SELECT USING (true);
CREATE POLICY "episodes_insert_policy" ON episodes FOR INSERT WITH CHECK (true);
CREATE POLICY "episodes_update_policy" ON episodes FOR UPDATE USING (true);
CREATE POLICY "episodes_delete_policy" ON episodes FOR DELETE USING (true);

-- =========================================
-- STEP 5: カラム名の意味的整理
-- =========================================

-- 5.1 program_idをepisode_idに変更（エピソード識別子として適切）
ALTER TABLE episodes RENAME COLUMN program_id TO episode_id;

-- 5.2 インデックスも更新
ALTER INDEX IF EXISTS idx_episodes_program_id RENAME TO idx_episodes_episode_id;

-- =========================================
-- STEP 6: 検証とコメント追加
-- =========================================

-- 6.1 テーブルコメント追加
COMMENT ON TABLE episodes IS 'エピソード詳細テーブル - 個別放送回の制作・進捗情報を管理';
COMMENT ON COLUMN episodes.episode_id IS 'エピソード識別子（旧program_id）';
COMMENT ON COLUMN episodes.title IS 'エピソードタイトル';
COMMENT ON COLUMN episodes.notes IS 'メモ - [PLATTO]/[LIBERARY]タグで番組区分';

-- 6.2 データ整合性確認
DO $$
DECLARE
    total_episodes INTEGER;
    platto_episodes INTEGER;
    liberary_episodes INTEGER;
BEGIN
    SELECT COUNT(*) INTO total_episodes FROM episodes;
    SELECT COUNT(*) INTO platto_episodes FROM episodes WHERE notes ILIKE '%[PLATTO]%';
    SELECT COUNT(*) INTO liberary_episodes FROM episodes WHERE notes ILIKE '%[LIBERARY]%';
    
    RAISE NOTICE '=== テーブル名整理完了 ===';
    RAISE NOTICE 'テーブル名: programs → episodes';
    RAISE NOTICE '総エピソード数: %', total_episodes;
    RAISE NOTICE 'PLATTOエピソード: %', platto_episodes;
    RAISE NOTICE 'LIBERARYエピソード: %', liberary_episodes;
    
    IF total_episodes = 15 AND platto_episodes = 10 AND liberary_episodes = 5 THEN
        RAISE NOTICE '✅ データ整合性確認完了';
    ELSE
        RAISE EXCEPTION '❌ データ整合性エラー';
    END IF;
END $$;

-- =========================================
-- 完了確認
-- =========================================

SELECT 
    'テーブル名整理完了 - Phase 2' as status,
    (SELECT COUNT(*) FROM episodes) as total_episodes,
    (SELECT table_name FROM information_schema.tables WHERE table_name = 'episodes' AND table_schema = 'public') as new_table_name;