-- ============================================================================
-- DELA×PM ステータスマスター定義投入
-- 作成日: 2025-07-28
-- 目的: PlattoとLiberaryのステータス定義を投入
-- ============================================================================

-- =========================================
-- Plattoステータス定義（9段階）
-- =========================================

INSERT INTO status_master (project_type, status_key, status_name, order_index, color_code, description) VALUES
('platto', 'casting', 'キャスティング中', 1, '#ff6b6b', 'ゲストキャストを選定中'),
('platto', 'scenario', 'シナリオ制作中', 2, '#4ecdc4', '番組構成・台本作成中'),
('platto', 'recording_prep', '収録準備中', 3, '#45b7d1', '収録に向けた準備作業中'),
('platto', 'recorded', '収録済', 4, '#96ceb4', '収録完了、編集待ち'),
('platto', 'editing', '編集中', 5, '#feca57', '映像・音声編集作業中'),
('platto', 'review', '確認中', 6, '#ff9ff3', 'クライアント確認・修正指示待ち'),
('platto', 'approved', '承認済', 7, '#54a0ff', 'クライアント承認完了'),
('platto', 'delivered', '納品済', 8, '#5f27cd', '完成品納品完了'),
('platto', 'billed', '請求済', 9, '#00d2d3', '請求書発行完了');

-- =========================================
-- Liberaryステータス定義（10段階）
-- =========================================

INSERT INTO status_master (project_type, status_key, status_name, order_index, color_code, description) VALUES
('liberary', 'script_writing', '台本作成中', 1, '#ff6b6b', '企画・台本作成段階'),
('liberary', 'material_prep', '素材準備', 2, '#4ecdc4', '収録用素材準備中'),
('liberary', 'material_ready', '素材確定', 3, '#45b7d1', '収録素材確定完了'),
('liberary', 'first_draft', '初稿完成', 4, '#96ceb4', '初回編集完了'),
('liberary', 'editing', '編集中', 5, '#feca57', '本編集作業中'),
('liberary', 'revision', '修正中', 6, '#ff9ff3', 'クライアント指示による修正中'),
('liberary', 'ma', 'MA中', 7, '#54a0ff', '音声調整・最終仕上げ中'),
('liberary', 'first_screening', '試写1', 8, '#5f27cd', '初回試写・確認段階'),
('liberary', 'final_revision', '修正1', 9, '#00d2d3', '試写後修正作業'),
('liberary', 'delivered', '完パケ納品', 10, '#2d98da', '完成品納品完了');

-- =========================================
-- 投入確認
-- =========================================

SELECT 
    'ステータスマスター投入完了' as status,
    project_type,
    COUNT(*) as status_count
FROM status_master 
GROUP BY project_type
ORDER BY project_type;