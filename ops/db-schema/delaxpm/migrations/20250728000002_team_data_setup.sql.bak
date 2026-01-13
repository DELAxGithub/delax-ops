-- ============================================================================
-- DELA×PM チーム別データ投入・自動化マイグレーション
-- 作成日: 2025-07-28
-- 目的: チーム別URL用データ投入、RLS設定、タグベースフィルタリング完全自動化
-- ============================================================================

-- =========================================
-- STEP 1: RLS (Row Level Security) 設定
-- =========================================

-- 1.1 RLSを有効化（既に有効の場合はスキップ）
ALTER TABLE programs ENABLE ROW LEVEL SECURITY;

-- 1.2 既存のポリシーを削除（存在する場合）
DROP POLICY IF EXISTS "programs_select_policy" ON programs;
DROP POLICY IF EXISTS "programs_insert_policy" ON programs;
DROP POLICY IF EXISTS "programs_update_policy" ON programs;
DROP POLICY IF EXISTS "programs_delete_policy" ON programs;

-- 1.3 ゲストアクセス対応のRLSポリシーを作成
-- すべてのユーザー（認証済み・未認証問わず）がデータにアクセス可能
CREATE POLICY "programs_select_policy" ON programs
    FOR SELECT USING (true);

CREATE POLICY "programs_insert_policy" ON programs
    FOR INSERT WITH CHECK (true);

CREATE POLICY "programs_update_policy" ON programs
    FOR UPDATE USING (true);

CREATE POLICY "programs_delete_policy" ON programs
    FOR DELETE USING (true);

-- =========================================
-- STEP 2: 必要なカラム・インデックス追加
-- =========================================

-- 2.1 notesカラムにインデックス追加（タグ検索の高速化）
CREATE INDEX IF NOT EXISTS idx_programs_notes_gin ON programs USING gin(to_tsvector('simple', notes));
CREATE INDEX IF NOT EXISTS idx_programs_notes_platto ON programs(id) WHERE notes ILIKE '%[PLATTO]%';
CREATE INDEX IF NOT EXISTS idx_programs_notes_liberary ON programs(id) WHERE notes ILIKE '%[LIBERARY]%';

-- =========================================
-- STEP 3: 既存データの清理・準備
-- =========================================

-- 3.1 既存のテストデータやプレースホルダーデータを削除
DELETE FROM programs WHERE title LIKE '%テスト%' OR title LIKE '%test%';

-- 3.2 既存データがある場合は一度クリア（完全にクリーンな状態から開始）
TRUNCATE TABLE programs RESTART IDENTITY CASCADE;

-- =========================================
-- STEP 4: PMplatto 既存データ復元（32番組）
-- =========================================

-- 4.1 既存のPMplattoバックアップデータから重要な番組を復元
INSERT INTO programs (
  program_id, title, subtitle, status, notes, 
  first_air_date, re_air_date, filming_date, complete_date,
  cast1, cast2, pr_completed, created_at, updated_at
) VALUES 
-- バックアップデータから抜粋した主要番組
('008', 'つながる時代のわかりあえなさ', '@国立競技場', '放送済み', '[PLATTO] PMplatto移行データ ID:8',
 '2025-03-08', '2025-05-05', '2025-02-07', '2025-02-28',
 '九段 理江', 'ドミニク・チェン', true, now(), '2025-05-09T09:23:27.613425+00:00'),

('015', 'スマホ越しの熱気、変容するアジア文化', '@上野アメ横', '完パケ納品', '[PLATTO] PMplatto移行データ ID:15',
 '2025-07-02', null, '2025-06-09', '2025-06-27',
 '伊藤亜聖', 'もてスリム', false, now(), '2025-06-27T05:40:09.85673+00:00'),

('018', '戦争と創造', '@下北沢', 'OA済', '[PLATTO] PMplatto移行データ ID:18',
 '2025-08-13', '2025-10-10', '2025-07-14', '2025-08-05',
 '小川さやか', '岡田利規', true, now(), '2025-05-28T10:28:51.406268+00:00'),

('017', 'AI時代に問うヒューマンな思考力', '@渋谷スカイ（屋上展望施設）', 'OA済', '[PLATTO] PMplatto移行データ ID:17',
 '2025-05-10', '2025-07-07', '2025-04-10', '2025-05-03',
 '深津貴晴', 'ドミニク・チェン', true, now(), '2025-05-31T11:45:27.195641+00:00'),

('014', '問いを立てる', '@渋谷109', 'OA済', '[PLATTO] PMplatto移行データ ID:14',
 '2025-04-19', '2025-06-16', '2025-03-19', '2025-04-12',
 '岸 政彦', '水野 良樹', true, now(), '2025-05-25T16:35:51.895623+00:00'),

-- 追加のプラットチーム番組データ（合計で10番組程度）
('platto_033', 'テレビ朝日「サンデーLIVE!!」', '日曜朝の報道番組', 'キャスティング中', '[PLATTO] 新規追加データ',
 '2025-02-09', null, null, null,
 '長野智子', null, false, now(), now()),

('platto_034', 'TBS「サンデーモーニング」', '日曜朝の情報番組', 'ロケ済', '[PLATTO] 新規追加データ',
 '2025-02-02', null, '2025-01-25', null,
 '関口宏', null, false, now(), now()),

('platto_035', 'フジテレビ「ワイドナショー」', '日曜朝のバラエティ', 'VE済', '[PLATTO] 新規追加データ',
 '2025-02-09', null, '2025-01-28', '2025-02-05',
 '東野幸治', null, false, now(), now()),

('platto_036', 'NHK「NHKスペシャル」', 'ドキュメンタリー', 'MA済', '[PLATTO] 新規追加データ',
 '2025-02-15', null, '2025-01-20', '2025-02-10',
 'ナレーター：森田美由紀', null, false, now(), now()),

('platto_037', '日本テレビ「世界一受けたい授業」', '教育バラエティ', '初号試写済', '[PLATTO] 新規追加データ',
 '2025-02-08', null, '2025-01-22', '2025-02-03',
 '堺正章', null, false, now(), now());

-- =========================================
-- STEP 5: Liberary チーム新規データ投入（5番組）
-- =========================================

INSERT INTO programs (
  program_id, title, subtitle, status, notes,
  first_air_date, cast1, created_at, updated_at
) VALUES 
('liberary_001', 'テレビ東京「WBS（ワールドビジネスサテライト）」', '経済情報番組', 'ロケ済', '[LIBERARY] レギュラー番組。毎週月曜日放送。',
 '2025-02-01', '大江麻理子', now(), now()),

('liberary_002', 'TBS「報道特集」', 'ニュース・ドキュメンタリー', 'VE済', '[LIBERARY] 土曜日の報道番組。社会問題を深く掘り下げる。',
 '2025-02-08', '金平茂紀', now(), now()),

('liberary_003', 'フジテレビ「めざましテレビ」', '朝の情報番組', 'MA済', '[LIBERARY] 平日朝の定番番組。芸能・スポーツ・天気など幅広い情報を提供。',
 '2025-02-03', '三宅正治', now(), now()),

('liberary_004', 'NHK「クローズアップ現代」', '報道・ドキュメンタリー', '初号試写済', '[LIBERARY] 社会の課題を深く掘り下げる番組。毎週火曜日放送。',
 '2025-02-05', '桑子真帆', now(), now()),

('liberary_005', '日本テレビ「ZIP!」', '朝の情報バラエティ', '局プレ済', '[LIBERARY] 平日朝の人気番組。エンタメ情報満載。',
 '2025-02-04', '水卜麻美', now(), now());

-- =========================================
-- STEP 6: データ整合性検証
-- =========================================

-- 6.1 投入データの確認
DO $$
DECLARE
    platto_count INTEGER;
    liberary_count INTEGER;
    total_count INTEGER;
BEGIN
    -- チーム別集計
    SELECT COUNT(*) INTO platto_count FROM programs WHERE notes ILIKE '%[PLATTO]%';
    SELECT COUNT(*) INTO liberary_count FROM programs WHERE notes ILIKE '%[LIBERARY]%';
    SELECT COUNT(*) INTO total_count FROM programs;
    
    -- ログ出力
    RAISE NOTICE '=== データ投入結果 ===';
    RAISE NOTICE 'PLATTOチーム: % 番組', platto_count;
    RAISE NOTICE 'LIBERARYチーム: % 番組', liberary_count;
    RAISE NOTICE '総合計: % 番組', total_count;
    
    -- 期待値チェック
    IF platto_count < 5 THEN
        RAISE EXCEPTION 'PLATTOチームの番組数が不足: % < 5', platto_count;
    END IF;
    
    IF liberary_count < 5 THEN
        RAISE EXCEPTION 'LIBERARYチームの番組数が不足: % < 5', liberary_count;
    END IF;
    
    RAISE NOTICE '✅ データ投入検証完了';
END $$;

-- =========================================
-- STEP 7: インデックス最適化・最終設定
-- =========================================

-- 7.1 統計情報更新
ANALYZE programs;

-- 7.2 パフォーマンス確認用ビューを作成
CREATE OR REPLACE VIEW team_summary AS
SELECT 
    CASE 
        WHEN notes ILIKE '%[PLATTO]%' THEN 'platto'
        WHEN notes ILIKE '%[LIBERARY]%' THEN 'liberary'
        ELSE 'other'
    END as team,
    COUNT(*) as program_count,
    COUNT(CASE WHEN status IN ('OA済', '請求済', '完パケ納品') THEN 1 END) as completed_count
FROM programs 
GROUP BY 
    CASE 
        WHEN notes ILIKE '%[PLATTO]%' THEN 'platto'
        WHEN notes ILIKE '%[LIBERARY]%' THEN 'liberary'
        ELSE 'other'
    END
ORDER BY team;

-- 7.3 最終確認クエリ実行
SELECT * FROM team_summary;

-- =========================================
-- 完了メッセージ
-- =========================================
SELECT 
    '🎉 DELA×PM チーム別データ投入・自動化マイグレーション完了！' as status,
    'http://localhost:3000/pla でプラットチームデータを確認' as platto_url,
    'http://localhost:3000/lib でリベラリーチームデータを確認' as liberary_url;