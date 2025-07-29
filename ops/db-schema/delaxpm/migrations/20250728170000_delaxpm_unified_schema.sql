-- ============================================================================
-- DELA×PM 統合データベーススキーマ作成
-- 作成日: 2025-07-28
-- 目的: PMplattoとPMliberaryを統合する3層構造データベース
-- ============================================================================

-- =========================================
-- STEP 1: 既存テーブルのバックアップ・削除
-- =========================================

-- 既存データがあればバックアップに移動
DO $$
BEGIN
    -- programsテーブルのバックアップ
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'programs' AND table_schema = 'public') THEN
        CREATE TABLE IF NOT EXISTS programs_backup AS SELECT * FROM programs;
    END IF;
    
    -- episodesテーブルのバックアップ
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'episodes' AND table_schema = 'public') THEN
        CREATE TABLE IF NOT EXISTS episodes_backup AS SELECT * FROM episodes;
    END IF;
END
$$;

-- 既存テーブルを削除
DROP TABLE IF EXISTS activity_logs CASCADE;
DROP TABLE IF EXISTS episodes CASCADE;
DROP TABLE IF EXISTS series CASCADE;
DROP TABLE IF EXISTS programs CASCADE;
DROP TABLE IF EXISTS stage_templates CASCADE;

-- =========================================
-- STEP 2: 新しい3層構造テーブル作成
-- =========================================

-- 2.1 programs（番組テーブル）
CREATE TABLE programs (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,                          -- 番組名
    project_type TEXT NOT NULL CHECK (project_type IN ('platto', 'liberary')), -- プロジェクト種別
    client_name TEXT,                             -- クライアント名
    description TEXT,                             -- 番組説明
    settings JSONB DEFAULT '{}',                  -- プロジェクト固有設定
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- 2.2 series（シリーズテーブル）
CREATE TABLE series (
    id SERIAL PRIMARY KEY,
    program_id INTEGER REFERENCES programs(id) ON DELETE CASCADE,
    season_number INTEGER DEFAULT 1,             -- シーズン番号
    title TEXT NOT NULL,                         -- シリーズ名
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'completed', 'cancelled')),
    start_date DATE,                             -- 開始日
    end_date DATE,                               -- 終了日
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    
    UNIQUE(program_id, season_number)
);

-- 2.3 episodes（エピソードテーブル）
CREATE TABLE episodes (
    id SERIAL PRIMARY KEY,
    series_id INTEGER REFERENCES series(id) ON DELETE CASCADE,
    episode_number INTEGER NOT NULL,             -- エピソード番号
    title TEXT,                                  -- エピソードタイトル
    status TEXT NOT NULL,                        -- ステータス（プロジェクト固有）
    air_date DATE,                               -- 放送・公開日
    cast1 TEXT,                                  -- キャスト1
    cast2 TEXT,                                  -- キャスト2
    location TEXT,                               -- 収録場所
    director TEXT,                               -- ディレクター
    script_url TEXT,                             -- 台本URL
    notes TEXT,                                  -- 備考
    metadata JSONB DEFAULT '{}',                 -- プロジェクト固有データ
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    
    UNIQUE(series_id, episode_number)
);

-- 2.4 status_master（ステータス定義テーブル）
CREATE TABLE status_master (
    id SERIAL PRIMARY KEY,
    project_type TEXT NOT NULL CHECK (project_type IN ('platto', 'liberary')),
    status_key TEXT NOT NULL,                    -- ステータスキー
    status_name TEXT NOT NULL,                   -- 表示名
    order_index INTEGER NOT NULL,               -- 表示順序
    color_code TEXT DEFAULT '#666666',          -- 表示色
    description TEXT,                            -- ステータス説明
    created_at TIMESTAMPTZ DEFAULT now(),
    
    UNIQUE(project_type, status_key),
    UNIQUE(project_type, order_index)
);

-- =========================================
-- STEP 3: インデックス作成
-- =========================================

-- Programs インデックス
CREATE INDEX idx_programs_project_type ON programs(project_type);
CREATE INDEX idx_programs_created_at ON programs(created_at);

-- Series インデックス
CREATE INDEX idx_series_program_id ON series(program_id);
CREATE INDEX idx_series_season ON series(program_id, season_number);
CREATE INDEX idx_series_status ON series(status);

-- Episodes インデックス
CREATE INDEX idx_episodes_series_id ON episodes(series_id);
CREATE INDEX idx_episodes_status ON episodes(status);
CREATE INDEX idx_episodes_air_date ON episodes(air_date);
CREATE INDEX idx_episodes_number ON episodes(series_id, episode_number);

-- 全文検索インデックス
CREATE INDEX idx_episodes_search ON episodes USING gin(to_tsvector('simple', COALESCE(title, '') || ' ' || COALESCE(notes, '')));

-- Status master インデックス
CREATE INDEX idx_status_master_project ON status_master(project_type, order_index);

-- =========================================
-- STEP 4: RLS（Row Level Security）設定
-- =========================================

-- RLS有効化
ALTER TABLE programs ENABLE ROW LEVEL SECURITY;
ALTER TABLE series ENABLE ROW LEVEL SECURITY;
ALTER TABLE episodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE status_master ENABLE ROW LEVEL SECURITY;

-- フルアクセスポリシー（ゲスト対応）
CREATE POLICY "programs_full_access" ON programs FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "series_full_access" ON series FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "episodes_full_access" ON episodes FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "status_master_read" ON status_master FOR SELECT USING (true);

-- =========================================
-- STEP 5: トリガー設定
-- =========================================

-- updated_at自動更新用関数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- updated_atトリガー設定
CREATE TRIGGER update_programs_updated_at 
    BEFORE UPDATE ON programs 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_series_updated_at 
    BEFORE UPDATE ON series 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_episodes_updated_at 
    BEFORE UPDATE ON episodes 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =========================================
-- 完了確認
-- =========================================

SELECT 
    'DELA×PM統合スキーマ作成完了' as status,
    (SELECT COUNT(*) FROM information_schema.tables 
     WHERE table_name IN ('programs', 'series', 'episodes', 'status_master') AND table_schema = 'public') as tables_created,
    (SELECT COUNT(*) FROM information_schema.triggers 
     WHERE trigger_name LIKE '%updated_at') as triggers_created;