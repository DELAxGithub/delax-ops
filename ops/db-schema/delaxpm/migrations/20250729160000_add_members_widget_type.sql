/*
  # チームダッシュボードにmembersウィジェットタイプを追加

  1. 変更内容
    - widget_type CHECKコンストレイントにmembersを追加
    - membersウィジェット用のサンプルデータを追加

  2. 理由
    - TypeScript型定義とデータベーススキーマの整合性を確保
    - MembersWidgetコンポーネントの実装に対応
*/

-- 既存のCHECKコンストレイントを削除
ALTER TABLE team_dashboard DROP CONSTRAINT IF EXISTS team_dashboard_widget_type_check;

-- 新しいCHECKコンストレイントを追加（membersを含む）
ALTER TABLE team_dashboard ADD CONSTRAINT team_dashboard_widget_type_check 
  CHECK (widget_type IN ('quicklinks', 'memo', 'tasks', 'schedule', 'members'));

-- membersウィジェット用のサンプルデータを追加
INSERT INTO team_dashboard (widget_type, title, content, sort_order) VALUES
  ('members', 'チームメンバー', '{
    "members": [
      {
        "id": "member-001",
        "name": "田中太郎",
        "role": "プロジェクトマネージャー",
        "status": "active",
        "skills": ["プロジェクト管理", "チーム運営", "企画"],
        "email": "tanaka@example.com"
      },
      {
        "id": "member-002", 
        "name": "佐藤花子",
        "role": "フロントエンドエンジニア",
        "status": "active",
        "skills": ["React", "TypeScript", "UI/UX"],
        "email": "sato@example.com"
      },
      {
        "id": "member-003",
        "name": "山田次郎",
        "role": "バックエンドエンジニア", 
        "status": "candidate",
        "skills": ["Node.js", "PostgreSQL", "API設計"]
      }
    ]
  }', 4)
ON CONFLICT DO NOTHING;

-- コメント更新
COMMENT ON COLUMN team_dashboard.widget_type IS 'ウィジェットタイプ: quicklinks, memo, tasks, schedule, members';