-- ============================================================================
-- DELA×PM 基本スキーマ作成マイグレーション
-- 作成日: 2025-07-28
-- 目的: クリーンな基本スキーマからの構築
-- ============================================================================

-- =========================================
-- STEP 1: 基本テーブル作成
-- =========================================

-- 1.1 programsテーブル作成
CREATE TABLE IF NOT EXISTS programs (
    id SERIAL PRIMARY KEY,
    program_id TEXT UNIQUE,
    title TEXT NOT NULL,
    subtitle TEXT,
    status TEXT,
    notes TEXT,
    first_air_date DATE,
    re_air_date DATE,
    filming_date DATE,
    complete_date DATE,
    cast1 TEXT,
    cast2 TEXT,
    director TEXT,
    script_url TEXT,
    pr_text TEXT,
    pr_completed BOOLEAN DEFAULT false,
    pr_due_date DATE,
    pr_80text TEXT,
    pr_200text TEXT,
    source_system TEXT,
    migrated_at TIMESTAMPTZ,
    legacy_id TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- 1.2 episodesテーブル作成（基本構造のみ）
CREATE TABLE IF NOT EXISTS episodes (
    id SERIAL PRIMARY KEY,
    episode_id TEXT UNIQUE,
    program_id INTEGER REFERENCES programs(id) ON DELETE CASCADE,
    episode_number INTEGER,
    title TEXT NOT NULL,
    episode_type TEXT DEFAULT 'regular',
    current_status TEXT,
    due_date DATE,
    director TEXT,
    notes TEXT,
    interview_guest TEXT,
    recording_date DATE,
    season INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- =========================================
-- STEP 2: インデックス作成
-- =========================================

-- 2.1 基本インデックス
CREATE INDEX IF NOT EXISTS idx_programs_program_id ON programs(program_id);
CREATE INDEX IF NOT EXISTS idx_programs_title ON programs(title);
CREATE INDEX IF NOT EXISTS idx_programs_status ON programs(status);
CREATE INDEX IF NOT EXISTS idx_programs_created_at ON programs(created_at);
CREATE INDEX IF NOT EXISTS idx_programs_updated_at ON programs(updated_at);

-- 2.2 検索用インデックス
CREATE INDEX IF NOT EXISTS idx_programs_notes_gin ON programs USING gin(to_tsvector('simple', notes));

-- =========================================
-- STEP 3: RLS設定（ゲストアクセス対応）
-- =========================================

-- 3.1 RLS有効化
ALTER TABLE programs ENABLE ROW LEVEL SECURITY;
ALTER TABLE episodes ENABLE ROW LEVEL SECURITY;

-- 3.2 フルアクセスポリシー（ゲスト対応）
CREATE POLICY "programs_full_access" ON programs FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "episodes_full_access" ON episodes FOR ALL USING (true) WITH CHECK (true);

-- =========================================
-- 完了確認
-- =========================================

SELECT 
    'テーブル作成完了' as status,
    (SELECT COUNT(*) FROM information_schema.tables WHERE table_name IN ('programs', 'episodes')) as tables_created;