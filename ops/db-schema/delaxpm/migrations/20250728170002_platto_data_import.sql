-- ============================================================================
-- DELA×PM Plattoデータ投入
-- 作成日: 2025-07-28
-- 目的: programs_rows.sqlのデータを3層構造に変換して投入
-- ============================================================================

-- =========================================
-- STEP 1: Platto番組作成
-- =========================================

INSERT INTO programs (title, project_type, client_name, description, settings) VALUES
('プラッと進捗すごろく', 'platto', '小寺浩志', 'ラジオ番組制作の9段階進捗管理システム。キャスティングから請求まで一貫して管理。', 
 '{"stages": 9, "workflow": "radio", "team": "platto"}');

-- =========================================
-- STEP 2: Plattoシリーズ作成
-- =========================================

-- 2024年シーズン
INSERT INTO series (program_id, season_number, title, status, start_date) VALUES
((SELECT id FROM programs WHERE project_type = 'platto'), 1, '2024年シーズン', 'completed', '2024-07-01');

-- 2025年シーズン
INSERT INTO series (program_id, season_number, title, status, start_date) VALUES
((SELECT id FROM programs WHERE project_type = 'platto'), 2, '2025年シーズン', 'active', '2025-01-01');

-- 2026年シーズン
INSERT INTO series (program_id, season_number, title, status, start_date) VALUES
((SELECT id FROM programs WHERE project_type = 'platto'), 3, '2026年シーズン', 'active', '2026-01-01');

-- =========================================
-- STEP 3: Plattoエピソード投入
-- =========================================

-- 状態マッピング関数
CREATE OR REPLACE FUNCTION map_platto_status(old_status TEXT) 
RETURNS TEXT AS $$
BEGIN
    RETURN CASE old_status
        WHEN 'キャスティング中' THEN 'casting'
        WHEN 'シナリオ制作中' THEN 'scenario'
        WHEN '収録準備中' THEN 'recording_prep'
        WHEN 'ロケハン前' THEN 'recording_prep'
        WHEN '収録済み' THEN 'recorded'
        WHEN '編集中' THEN 'editing'
        WHEN 'MA中' THEN 'editing'
        WHEN '確認中' THEN 'review'
        WHEN '承認済み' THEN 'approved'
        WHEN '放送済み' THEN 'delivered'
        WHEN '完パケ納品' THEN 'delivered'
        WHEN '請求済み' THEN 'billed'
        ELSE 'casting'
    END;
END;
$$ LANGUAGE plpgsql;

-- シーズン判定関数
CREATE OR REPLACE FUNCTION get_platto_series_id(air_date DATE) 
RETURNS INTEGER AS $$
BEGIN
    IF air_date >= '2024-01-01' AND air_date < '2025-01-01' THEN
        RETURN (SELECT id FROM series WHERE program_id = (SELECT id FROM programs WHERE project_type = 'platto') AND season_number = 1);
    ELSIF air_date >= '2025-01-01' AND air_date < '2026-01-01' THEN
        RETURN (SELECT id FROM series WHERE program_id = (SELECT id FROM programs WHERE project_type = 'platto') AND season_number = 2);
    ELSE
        RETURN (SELECT id FROM series WHERE program_id = (SELECT id FROM programs WHERE project_type = 'platto') AND season_number = 3);
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Plattoエピソードデータ投入
INSERT INTO episodes (series_id, episode_number, title, status, air_date, cast1, cast2, location, script_url, notes, metadata) VALUES
-- 2024年分
(get_platto_series_id('2024-07-09'), 1, '後から変更', map_platto_status('放送済み'), '2024-07-09', 'チュ・ヒチョル', '三牧 聖子', '@日比谷公園', null, null, '{"legacy_id": "001", "pr_completed": true}'),
(get_platto_series_id('2024-07-23'), 2, '後から変更', map_platto_status('放送済み'), '2024-07-23', '岩尾 俊兵', '大澤 聡', '@大手町', null, null, '{"legacy_id": "002", "pr_completed": true}'),
(get_platto_series_id('2024-10-15'), 3, 'Z世代を知れば日本が見える?', map_platto_status('放送済み'), '2024-10-15', '舟津 昌平', '谷川 嘉浩', '@宮下公園', null, null, '{"legacy_id": "003", "pr_completed": true}'),
(get_platto_series_id('2024-11-05'), 4, '本を読めない？時代の読書論', map_platto_status('放送済み'), '2024-11-05', '三宅 香帆', '阿部 公彦', '＠丸の内', null, null, '{"legacy_id": "004", "pr_completed": true}'),
(get_platto_series_id('2024-12-17'), 5, '胃袋の記憶を辿る旅', map_platto_status('放送済み'), '2024-12-17', '稲田 俊輔', '湯澤 規子', '@日比谷公園', null, null, '{"legacy_id": "005", "pr_completed": true}'),

-- 2025年分
(get_platto_series_id('2025-01-14'), 6, '近くて遠い？大国のリアル', map_platto_status('放送済み'), '2025-01-14', '小泉 悠', '岡本 隆司', '@明治神宮外苑', null, null, '{"legacy_id": "006", "pr_completed": true}'),
(get_platto_series_id('2025-02-16'), 7, 'シン・アメリカ時代の虚構とリアル', map_platto_status('放送済み'), '2025-02-16', '三牧 聖子', '小川 哲', '@代々木公園', null, null, '{"legacy_id": "007", "pr_completed": true}'),
(get_platto_series_id('2025-03-08'), 8, 'つながる時代のわかりあえなさ', map_platto_status('放送済み'), '2025-03-08', '九段 理江', 'ドミニク・チェン', '@国立競技場', null, null, '{"legacy_id": "008", "pr_completed": true, "re_air_date": "2025-05-05"}'),
(get_platto_series_id('2025-04-02'), 9, '資本主義の余白は今どこに？', map_platto_status('放送済み'), '2025-04-02', '大川内 直子', '星野 太', '@日本橋兜町', 'https://docs.google.com/document/d/1dkQ3hbptrPxD6GL0c9ufz0apviw18lyz3sDIT2uwy8I/edit?usp=sharing', null, '{"legacy_id": "009", "pr_completed": true, "pr_80text": "数字に追われる現代人…。金融の街・兜町で文化人類学者と美学者が、その閉塞感からの出口を考えた。"}'),
(get_platto_series_id('2025-04-09'), 10, 'ファッションは個性？同調？', map_platto_status('放送済み'), '2025-04-09', '平芳 裕子', 'トミヤマ ユキコ', '＠原宿', 'https://docs.google.com/document/d/1HWlJtA7RzpdtJ3WNc36_jSOCe5aZ_AMN-oYiZE7B-Ic/edit?usp=sharing', 'マンガに描かれる装いと、ファッションが生み出す物語。', '{"legacy_id": "010", "pr_completed": true, "pr_due_date": "2025-03-25"}'),
(get_platto_series_id('2025-05-07'), 11, '古くて新しい巡礼の話', map_platto_status('放送済み'), '2025-05-07', '岡本 亮輔', 'サンキュータツオ', '@秋葉原', 'https://docs.google.com/document/d/1SiJav6pvD8M1mqvjMc0GfPuRzxhufgM_GyqF8_U_NLo/edit?usp=sharing', '「巡礼の新しいカタチ@秋葉原', '{"legacy_id": "011", "pr_completed": true}'),
(get_platto_series_id('2025-05-14'), 12, '冷笑から哄笑へ　明るい自分探しの旅', map_platto_status('完パケ納品'), '2025-05-14', 'しんめいP', '納富 信留', '＠哲学堂公園', 'https://docs.google.com/document/d/1ALvFqJW39AbqBcOroQinR5Q1Q8jKBDQsjCnmH9z-k-0/edit?usp=sharing', '東洋哲学の読書本でベストセラーを記録した東大卒ニート', '{"legacy_id": "012", "pr_completed": true}'),
(get_platto_series_id('2025-06-04'), 13, '人生を変える為にルールを変える？', map_platto_status('完パケ納品'), '2025-06-04', '米光 一成', '水野 祐', '@新宿中央公園', null, 'ゲームと法律。一見かけ離れた世界をつなぐのは、ゲーミフィケーション', '{"legacy_id": "013", "pr_completed": true}'),
(get_platto_series_id('2025-06-11'), 14, '消費される教養の正体', map_platto_status('放送済み'), '2025-06-11', '勅使川原真衣', 'レジー', '＠神保町', 'https://docs.google.com/document/d/1z5VONnaiHAkbIYV5cyQFRZ2O7ZRx2S0uyAPBLoRhg8w/edit?usp=sharing', '学歴社会」の構造を解き明かす研究者', '{"legacy_id": "014", "pr_completed": false}'),
(get_platto_series_id('2025-07-02'), 15, 'スマホ越しの熱気、変容するアジア文化', map_platto_status('完パケ納品'), '2025-07-02', '伊藤亜聖', 'もてスリム', '@上野アメ横', 'https://docs.google.com/document/d/1ANIQyGg7oZKUkcrBCkXVgFXZtCwFHsWxQaz2KN-JzDo/edit?usp=sharing', '中国・新興国のデジタル経済を分析する伊藤氏', '{"legacy_id": "015", "pr_completed": false, "pr_due_date": "2025-06-20"}'),
(get_platto_series_id('2025-07-09'), 16, '無限の可能性は実在する？', map_platto_status('完パケ納品'), '2025-07-09', '今井翔太', '野村泰紀', '@池袋', 'https://docs.google.com/document/d/179UYsKGQtN1djWt6DAp9DLt8UJuOKqTqPMptmaueIJU/edit?usp=sharing', '私たちの宇宙は無数に存在する「多元宇宙」の一つなのか？', '{"legacy_id": "016", "pr_completed": false, "pr_due_date": "2025-06-27"}'),
(get_platto_series_id('2025-08-06'), 17, '信じる者は"創造"する？', map_platto_status('MA中'), '2025-08-06', '柳澤田実', '関美和', '@麻布', 'https://docs.google.com/document/d/12OYfm6knU_azRGqcsQ-fnrj_iWad1TMTR54aq_tX30E/edit?usp=sharing', 'なぜアメリカは世界を「創造」しようとするのか？', '{"legacy_id": "017", "pr_completed": false, "pr_due_date": "2025-07-25"}'),
(get_platto_series_id('2025-08-13'), 18, '戦争と創造', map_platto_status('編集中'), '2025-08-13', '岡本 裕一朗', '今日 マチ子', '@上野公園', 'https://docs.google.com/document/d/13QGR0foGNiYtZtqjz370AHAw0fuwFeXTI-MHGS4_4Ss/edit?usp=sharing', '戦争を語ることは可能か？表現することで何が救われるのか？', '{"legacy_id": "018", "pr_completed": false}'),
(get_platto_series_id('2025-09-03'), 19, 'デジタルで変容する存在の境界', map_platto_status('収録準備中'), '2025-09-03', '市原えつこ', 'comugi', '@六本木とか上野', null, '「死後も存在し続ける」とはどういうことか。', '{"legacy_id": "019", "pr_completed": false}'),
(get_platto_series_id('2025-09-10'), 20, '世代を超える"つながり"の育て方', map_platto_status('ロケハン前'), '2025-09-10', '飯島勝矢', '山本ふみこ', '@古民家カフェ', null, '人生100年"を豊かにする暮らしと「街」とは？', '{"legacy_id": "020", "pr_completed": false}'),

-- 2025年未来分（キャスティング中）
(get_platto_series_id('2025-10-01'), 21, null, map_platto_status('キャスティング中'), '2025-10-01', null, null, null, null, null, '{"legacy_id": "021", "pr_completed": false}'),
(get_platto_series_id('2025-10-08'), 22, null, map_platto_status('キャスティング中'), '2025-10-08', null, null, null, null, null, '{"legacy_id": "022", "pr_completed": false}'),
(get_platto_series_id('2025-11-05'), 23, null, map_platto_status('キャスティング中'), '2025-11-05', null, null, null, null, null, '{"legacy_id": "023", "pr_completed": false}'),
(get_platto_series_id('2025-11-12'), 24, null, map_platto_status('キャスティング中'), '2025-11-12', null, null, null, null, null, '{"legacy_id": "024", "pr_completed": false}'),
(get_platto_series_id('2025-12-03'), 25, null, map_platto_status('キャスティング中'), '2025-12-03', null, null, null, null, null, '{"legacy_id": "025", "pr_completed": false}'),
(get_platto_series_id('2025-12-10'), 26, null, map_platto_status('キャスティング中'), '2025-12-10', null, null, null, null, null, '{"legacy_id": "026", "pr_completed": false}'),

-- 2026年分（キャスティング中）
(get_platto_series_id('2026-01-07'), 27, null, map_platto_status('キャスティング中'), '2026-01-07', null, null, null, null, null, '{"legacy_id": "027", "pr_completed": false}'),
(get_platto_series_id('2026-01-14'), 28, null, map_platto_status('キャスティング中'), '2026-01-14', null, null, null, null, null, '{"legacy_id": "028", "pr_completed": false}'),
(get_platto_series_id('2026-02-04'), 29, null, map_platto_status('キャスティング中'), '2026-02-04', null, null, null, null, null, '{"legacy_id": "029", "pr_completed": false}'),
(get_platto_series_id('2026-02-11'), 30, null, map_platto_status('キャスティング中'), '2026-02-11', null, null, null, null, null, '{"legacy_id": "030", "pr_completed": false}'),
(get_platto_series_id('2026-03-04'), 31, null, map_platto_status('キャスティング中'), '2026-03-04', null, null, null, null, null, '{"legacy_id": "031", "pr_completed": false}'),
(get_platto_series_id('2026-03-11'), 32, null, map_platto_status('キャスティング中'), '2026-03-11', null, null, null, null, null, '{"legacy_id": "032", "pr_completed": false}');

-- =========================================
-- 投入確認
-- =========================================

SELECT 
    'Plattoデータ投入完了' as status,
    (SELECT COUNT(*) FROM episodes WHERE series_id IN (
        SELECT id FROM series WHERE program_id = (SELECT id FROM programs WHERE project_type = 'platto')
    )) as total_episodes,
    (SELECT COUNT(*) FROM series WHERE program_id = (SELECT id FROM programs WHERE project_type = 'platto')) as total_series;