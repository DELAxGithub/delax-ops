-- ============================================================================
-- DELA×PM Liberaryデータ投入
-- 作成日: 2025-07-28
-- 目的: dummy_episodes.csvのデータを3層構造に変換して投入
-- ============================================================================

-- =========================================
-- STEP 1: Liberary番組作成
-- =========================================

INSERT INTO programs (title, project_type, client_name, description, settings) VALUES
('リベラリー進捗管理', 'liberary', '小寺浩志', 'WEB動画制作の10段階進捗管理システム。企画から完パケ納品まで包括的管理。', 
 '{"stages": 10, "workflow": "web", "team": "liberary"}');

-- =========================================
-- STEP 2: Liberaryシリーズ作成
-- =========================================

-- ORNシリーズ（Season 1）
INSERT INTO series (program_id, season_number, title, status, start_date) VALUES
((SELECT id FROM programs WHERE project_type = 'liberary'), 1, 'ORN Season 1', 'active', '2025-01-01');

-- Season 2
INSERT INTO series (program_id, season_number, title, status, start_date) VALUES
((SELECT id FROM programs WHERE project_type = 'liberary'), 2, 'Season 2', 'active', '2025-03-01');

-- LA-INTシリーズ（インタビュー）
INSERT INTO series (program_id, season_number, title, status, start_date) VALUES
((SELECT id FROM programs WHERE project_type = 'liberary'), 3, 'LA Interview Series', 'active', '2025-01-01');

-- DY-INTシリーズ（同友会インタビュー）
INSERT INTO series (program_id, season_number, title, status, start_date) VALUES
((SELECT id FROM programs WHERE project_type = 'liberary'), 4, 'DY Interview Series', 'active', '2025-03-01');

-- =========================================
-- STEP 3: 状態マッピング関数
-- =========================================

CREATE OR REPLACE FUNCTION map_liberary_status(old_status TEXT) 
RETURNS TEXT AS $$
BEGIN
    RETURN CASE old_status
        WHEN '台本作成中' THEN 'script_writing'
        WHEN '素材準備' THEN 'material_prep'
        WHEN '素材確定' THEN 'material_ready'
        WHEN '初稿完成' THEN 'first_draft'
        WHEN '編集中' THEN 'editing'
        WHEN '修正中' THEN 'revision'
        WHEN 'MA中' THEN 'ma'
        WHEN '試写1' THEN 'first_screening'
        WHEN '修正1' THEN 'final_revision'
        WHEN '完パケ納品' THEN 'delivered'
        ELSE 'script_writing'
    END;
END;
$$ LANGUAGE plpgsql;

-- シリーズ判定関数
CREATE OR REPLACE FUNCTION get_liberary_series_id(episode_prefix TEXT) 
RETURNS INTEGER AS $$
BEGIN
    IF episode_prefix LIKE 'ORN-%' THEN
        RETURN (SELECT id FROM series WHERE program_id = (SELECT id FROM programs WHERE project_type = 'liberary') AND season_number = 1);
    ELSIF episode_prefix LIKE 'S2-%' THEN
        RETURN (SELECT id FROM series WHERE program_id = (SELECT id FROM programs WHERE project_type = 'liberary') AND season_number = 2);
    ELSIF episode_prefix LIKE 'LA-INT%' THEN
        RETURN (SELECT id FROM series WHERE program_id = (SELECT id FROM programs WHERE project_type = 'liberary') AND season_number = 3);
    ELSIF episode_prefix LIKE 'DY-INT%' THEN
        RETURN (SELECT id FROM series WHERE program_id = (SELECT id FROM programs WHERE project_type = 'liberary') AND season_number = 4);
    ELSE
        RETURN (SELECT id FROM series WHERE program_id = (SELECT id FROM programs WHERE project_type = 'liberary') AND season_number = 1);
    END IF;
END;
$$ LANGUAGE plpgsql;

-- =========================================
-- STEP 4: Liberaryエピソード投入
-- =========================================

-- ORN Season 1 エピソード（15話）
INSERT INTO episodes (series_id, episode_number, title, status, air_date, director, script_url, metadata) VALUES
(get_liberary_series_id('ORN-EP01'), 1, '転職の約束', map_liberary_status('編集中'), '2025-02-15', '田中ディレクター', 'https://docs.google.com/document/d/dummy01', '{"episode_id": "ORN-EP01", "episode_type": "vtr", "material_status": "○", "due_date": "2025-02-15"}'),
(get_liberary_series_id('ORN-EP02'), 2, '帰れない私たち', map_liberary_status('素材確定'), '2025-02-20', '佐藤ディレクター', 'https://docs.google.com/document/d/dummy02', '{"episode_id": "ORN-EP02", "episode_type": "vtr", "material_status": "○", "due_date": "2025-02-20"}'),
(get_liberary_series_id('ORN-EP03'), 3, '動じない上司の秘密', map_liberary_status('素材準備'), '2025-02-25', '田中ディレクター', 'https://docs.google.com/document/d/dummy03', '{"episode_id": "ORN-EP03", "episode_type": "vtr", "material_status": "△", "due_date": "2025-02-25"}'),
(get_liberary_series_id('ORN-EP04'), 4, 'パワハラと寛容の間', map_liberary_status('台本作成中'), '2025-03-01', '山田ディレクター', 'https://docs.google.com/document/d/dummy04', '{"episode_id": "ORN-EP04", "episode_type": "vtr", "material_status": "×", "due_date": "2025-03-01"}'),
(get_liberary_series_id('ORN-EP05'), 5, '頑張らない技術', map_liberary_status('試写1'), '2025-02-10', '佐藤ディレクター', 'https://docs.google.com/document/d/dummy05', '{"episode_id": "ORN-EP05", "episode_type": "vtr", "material_status": "○", "due_date": "2025-02-10"}'),
(get_liberary_series_id('ORN-EP06'), 6, 'エース社員の憂鬱', map_liberary_status('修正1'), '2025-02-12', '田中ディレクター', 'https://docs.google.com/document/d/dummy06', '{"episode_id": "ORN-EP06", "episode_type": "vtr", "material_status": "○", "due_date": "2025-02-12"}'),
(get_liberary_series_id('ORN-EP07'), 7, 'イノベーションという破壊', map_liberary_status('MA中'), '2025-02-08', '鈴木ディレクター', 'https://docs.google.com/document/d/dummy07', '{"episode_id": "ORN-EP07", "episode_type": "vtr", "material_status": "○", "due_date": "2025-02-08"}'),
(get_liberary_series_id('ORN-EP08'), 8, '朝活の呪い', map_liberary_status('初稿完成'), '2025-02-05', '山田ディレクター', 'https://docs.google.com/document/d/dummy08', '{"episode_id": "ORN-EP08", "episode_type": "vtr", "material_status": "○", "due_date": "2025-02-05"}'),
(get_liberary_series_id('ORN-EP09'), 9, '測れないものの価値', map_liberary_status('修正中'), '2025-02-03', '佐藤ディレクター', 'https://docs.google.com/document/d/dummy09', '{"episode_id": "ORN-EP09", "episode_type": "vtr", "material_status": "○", "due_date": "2025-02-03"}'),
(get_liberary_series_id('ORN-EP10'), 10, 'カリスマはもういらない', map_liberary_status('完パケ納品'), '2025-01-25', '田中ディレクター', 'https://docs.google.com/document/d/dummy10', '{"episode_id": "ORN-EP10", "episode_type": "vtr", "material_status": "○", "due_date": "2025-01-25"}'),
(get_liberary_series_id('ORN-EP11'), 11, '知ったかぶりの効用', map_liberary_status('編集中'), '2025-02-18', '鈴木ディレクター', 'https://docs.google.com/document/d/dummy11', '{"episode_id": "ORN-EP11", "episode_type": "vtr", "material_status": "○", "due_date": "2025-02-18"}'),
(get_liberary_series_id('ORN-EP12'), 12, '瞑想アプリの違和感', map_liberary_status('素材確定'), '2025-02-22', '山田ディレクター', 'https://docs.google.com/document/d/dummy12', '{"episode_id": "ORN-EP12", "episode_type": "vtr", "material_status": "△", "due_date": "2025-02-22"}'),
(get_liberary_series_id('ORN-SP01'), 13, '正しい会社なんてない（特別編）', map_liberary_status('素材準備'), '2025-03-05', '佐藤ディレクター', 'https://docs.google.com/document/d/dummy13', '{"episode_id": "ORN-SP01", "episode_type": "vtr", "material_status": "×", "due_date": "2025-03-05"}'),
(get_liberary_series_id('ORN-SP02'), 14, 'スペシャリストかゼネラリストか（特別編）', map_liberary_status('台本作成中'), '2025-03-10', '田中ディレクター', 'https://docs.google.com/document/d/dummy14', '{"episode_id": "ORN-SP02", "episode_type": "vtr", "material_status": "×", "due_date": "2025-03-10"}'),
(get_liberary_series_id('ORN-SP03'), 15, '知れば知るほど分からない（特別編）', map_liberary_status('台本作成中'), '2025-03-15', '鈴木ディレクター', 'https://docs.google.com/document/d/dummy15', '{"episode_id": "ORN-SP03", "episode_type": "vtr", "material_status": "×", "due_date": "2025-03-15"}');

-- Season 2 エピソード（15話）
INSERT INTO episodes (series_id, episode_number, title, status, air_date, director, script_url, metadata) VALUES
(get_liberary_series_id('S2-EP01'), 1, '既読スルーの哲学', map_liberary_status('素材準備'), '2025-03-20', '山田ディレクター', 'https://docs.google.com/document/d/dummy16', '{"episode_id": "S2-EP01", "episode_type": "vtr", "material_status": "△", "due_date": "2025-03-20"}'),
(get_liberary_series_id('S2-EP02'), 2, '雑談ができない私たち', map_liberary_status('台本作成中'), '2025-03-25', '佐藤ディレクター', 'https://docs.google.com/document/d/dummy17', '{"episode_id": "S2-EP02", "episode_type": "vtr", "material_status": "×", "due_date": "2025-03-25"}'),
(get_liberary_series_id('S2-EP03'), 3, '褒められない、褒めない', map_liberary_status('台本作成中'), '2025-03-30', '田中ディレクター', 'https://docs.google.com/document/d/dummy18', '{"episode_id": "S2-EP03", "episode_type": "vtr", "material_status": "×", "due_date": "2025-03-30"}'),
(get_liberary_series_id('S2-EP04'), 4, '会議で発言できない人へ', map_liberary_status('台本作成中'), '2025-04-05', '鈴木ディレクター', 'https://docs.google.com/document/d/dummy19', '{"episode_id": "S2-EP04", "episode_type": "vtr", "material_status": "×", "due_date": "2025-04-05"}'),
(get_liberary_series_id('S2-EP05'), 5, 'SNS疲れの処方箋', map_liberary_status('台本作成中'), '2025-04-10', '山田ディレクター', 'https://docs.google.com/document/d/dummy20', '{"episode_id": "S2-EP05", "episode_type": "vtr", "material_status": "×", "due_date": "2025-04-10"}'),
(get_liberary_series_id('S2-EP06'), 6, '板挟みの美学', map_liberary_status('台本作成中'), '2025-04-15', '佐藤ディレクター', 'https://docs.google.com/document/d/dummy21', '{"episode_id": "S2-EP06", "episode_type": "vtr", "material_status": "×", "due_date": "2025-04-15"}'),
(get_liberary_series_id('S2-EP07'), 7, 'ナンバー2の矜持', map_liberary_status('台本作成中'), '2025-04-20', '田中ディレクター', 'https://docs.google.com/document/d/dummy22', '{"episode_id": "S2-EP07", "episode_type": "vtr", "material_status": "×", "due_date": "2025-04-20"}'),
(get_liberary_series_id('S2-EP08'), 8, '派閥という生き物', map_liberary_status('台本作成中'), '2025-04-25', '鈴木ディレクター', 'https://docs.google.com/document/d/dummy23', '{"episode_id": "S2-EP08", "episode_type": "vtr", "material_status": "×", "due_date": "2025-04-25"}'),
(get_liberary_series_id('S2-EP09'), 9, '異動という名の流刑', map_liberary_status('台本作成中'), '2025-04-30', '山田ディレクター', 'https://docs.google.com/document/d/dummy24', '{"episode_id": "S2-EP09", "episode_type": "vtr", "material_status": "×", "due_date": "2025-04-30"}'),
(get_liberary_series_id('S2-EP10'), 10, '退職という決断', map_liberary_status('台本作成中'), '2025-05-05', '佐藤ディレクター', 'https://docs.google.com/document/d/dummy25', '{"episode_id": "S2-EP10", "episode_type": "vtr", "material_status": "×", "due_date": "2025-05-05"}'),
(get_liberary_series_id('S2-EP11'), 11, '締切前夜の心理学', map_liberary_status('台本作成中'), '2025-05-10', '田中ディレクター', 'https://docs.google.com/document/d/dummy26', '{"episode_id": "S2-EP11", "episode_type": "vtr", "material_status": "×", "due_date": "2025-05-10"}'),
(get_liberary_series_id('S2-EP12'), 12, '休めない症候群', map_liberary_status('台本作成中'), '2025-05-15', '鈴木ディレクター', 'https://docs.google.com/document/d/dummy27', '{"episode_id": "S2-EP12", "episode_type": "vtr", "material_status": "×", "due_date": "2025-05-15"}'),
(get_liberary_series_id('S2-SP01'), 13, '会議という時間（特別編）', map_liberary_status('台本作成中'), '2025-05-20', '山田ディレクター', 'https://docs.google.com/document/d/dummy28', '{"episode_id": "S2-SP01", "episode_type": "vtr", "material_status": "×", "due_date": "2025-05-20"}'),
(get_liberary_series_id('S2-SP02'), 14, 'マルチタスクという幻想（特別編）', map_liberary_status('台本作成中'), '2025-05-25', '佐藤ディレクター', 'https://docs.google.com/document/d/dummy29', '{"episode_id": "S2-SP02", "episode_type": "vtr", "material_status": "×", "due_date": "2025-05-25"}'),
(get_liberary_series_id('S2-SP03'), 15, '引き継ぎという贈り物（特別編）', map_liberary_status('台本作成中'), '2025-05-30', '田中ディレクター', 'https://docs.google.com/document/d/dummy30', '{"episode_id": "S2-SP03", "episode_type": "vtr", "material_status": "×", "due_date": "2025-05-30"}');

-- LA-INTシリーズ（インタビュー6話）
INSERT INTO episodes (series_id, episode_number, title, status, air_date, director, script_url, location, metadata) VALUES
(get_liberary_series_id('LA-INT001'), 1, '谷川嘉浩：現代社会を解読する哲学者', map_liberary_status('台本作成中'), '2025-02-01', '高橋ディレクター', 'https://docs.google.com/document/d/dummy31', '東京スタジオA', '{"episode_id": "LA-INT001", "episode_type": "interview", "guest_name": "谷川嘉浩", "recording_date": "2025-01-20"}'),
(get_liberary_series_id('LA-INT002'), 2, '大川内直子：文化人類学をビジネスに応用する実務家', map_liberary_status('編集中'), '2025-02-05', '高橋ディレクター', 'https://docs.google.com/document/d/dummy32', '東京スタジオA', '{"episode_id": "LA-INT002", "episode_type": "interview", "guest_name": "大川内直子", "recording_date": "2025-01-15"}'),
(get_liberary_series_id('LA-INT003'), 3, '舟津昌平：マクロな経済構造転換とイノベーション', map_liberary_status('試写1'), '2025-01-30', '高橋ディレクター', 'https://docs.google.com/document/d/dummy33', '東京スタジオB', '{"episode_id": "LA-INT003", "episode_type": "interview", "guest_name": "舟津昌平", "recording_date": "2025-01-10"}'),
(get_liberary_series_id('LA-INT004'), 4, '庭本佳子：労働法×人的資本とチームリーダーシップ', map_liberary_status('MA中'), '2025-01-28', '木村ディレクター', 'https://docs.google.com/document/d/dummy34', '大阪スタジオ', '{"episode_id": "LA-INT004", "episode_type": "interview", "guest_name": "庭本佳子", "recording_date": "2025-01-08"}'),
(get_liberary_series_id('LA-INT005'), 5, '渡部麻衣子：科学技術と社会の架け橋', map_liberary_status('初稿完成'), '2025-01-26', '木村ディレクター', 'https://docs.google.com/document/d/dummy35', '東京スタジオA', '{"episode_id": "LA-INT005", "episode_type": "interview", "guest_name": "渡部麻衣子", "recording_date": "2025-01-05"}'),
(get_liberary_series_id('LA-INT006'), 6, '伊藤亜聖：デジタル新興国の経済研究', map_liberary_status('完パケ納品'), '2025-01-20', '木村ディレクター', 'https://docs.google.com/document/d/dummy36', '東京スタジオB', '{"episode_id": "LA-INT006", "episode_type": "interview", "guest_name": "伊藤亜聖", "recording_date": "2024-12-25"}');

-- DY-INTシリーズ（同友会インタビュー5話）
INSERT INTO episodes (series_id, episode_number, title, status, air_date, director, script_url, location, metadata) VALUES
(get_liberary_series_id('DY-INT001'), 1, '経営者の哲学：変革期のリーダーシップ', map_liberary_status('素材準備'), '2025-03-01', '中村ディレクター', 'https://docs.google.com/document/d/dummy37', '同友会ホール', '{"episode_id": "DY-INT001", "episode_type": "interview", "guest_name": "山田太郎（架空）", "recording_date": "2025-02-15"}'),
(get_liberary_series_id('DY-INT002'), 2, '地域創生とビジネス：持続可能な経営', map_liberary_status('台本作成中'), '2025-03-15', '中村ディレクター', 'https://docs.google.com/document/d/dummy38', '同友会ホール', '{"episode_id": "DY-INT002", "episode_type": "interview", "guest_name": "佐藤花子（架空）", "recording_date": "2025-03-01"}'),
(get_liberary_series_id('DY-INT003'), 3, 'DXと中小企業：デジタル変革の実践', map_liberary_status('台本作成中'), '2025-03-30', '中村ディレクター', 'https://docs.google.com/document/d/dummy39', 'オンライン収録', '{"episode_id": "DY-INT003", "episode_type": "interview", "guest_name": "鈴木一郎（架空）", "recording_date": "2025-03-15"}'),
(get_liberary_series_id('DY-INT004'), 4, '事業承継の新しい形：次世代への橋渡し', map_liberary_status('台本作成中'), '2025-04-15', '中村ディレクター', 'https://docs.google.com/document/d/dummy40', '同友会ホール', '{"episode_id": "DY-INT004", "episode_type": "interview", "guest_name": "田中美香（架空）", "recording_date": "2025-04-01"}'),
(get_liberary_series_id('DY-INT005'), 5, '社会課題とビジネス：共創型経営の未来', map_liberary_status('台本作成中'), '2025-04-30', '中村ディレクター', 'https://docs.google.com/document/d/dummy41', '同友会ホール', '{"episode_id": "DY-INT005", "episode_type": "interview", "guest_name": "高橋健二（架空）", "recording_date": "2025-04-15"}');

-- =========================================
-- 投入確認
-- =========================================

SELECT 
    'Liberaryデータ投入完了' as status,
    (SELECT COUNT(*) FROM episodes WHERE series_id IN (
        SELECT id FROM series WHERE program_id = (SELECT id FROM programs WHERE project_type = 'liberary')
    )) as total_episodes,
    (SELECT COUNT(*) FROM series WHERE program_id = (SELECT id FROM programs WHERE project_type = 'liberary')) as total_series;