# 週次レビュー エッジファンクション

週次エピソード進捗レビューを自動生成し、SlackとEmailで通知するエッジファンクションです。

## 機能概要

- 週次でエピソード進捗をレビュー
- 期限超過・今後の期限をアラート
- Slack通知（リッチフォーマット）
- Email通知（HTML形式）
- エピソード統計とタスク情報

## 必要な環境変数

### 必須設定
```bash
# Supabase接続
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key

# Slack通知（オプション）
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK

# Email通知（オプション）
REVIEW_EMAIL=example@domain.com
APP_BASE_URL=https://your-app.com
EMAIL_SERVICE=resend
RESEND_API_KEY=re_your_resend_api_key
EMAIL_DOMAIN=your-domain.com
```

### 設定方法

1. **Supabase環境変数の設定**
```bash
# Supabase CLIで設定
supabase secrets set SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
supabase secrets set REVIEW_EMAIL=example@domain.com
supabase secrets set APP_BASE_URL=https://your-app.com
supabase secrets set RESEND_API_KEY=re_your_resend_api_key
supabase secrets set EMAIL_DOMAIN=your-domain.com
```

2. **Slackウェブフック作成**
   - Slack Appを作成
   - Incoming Webhookを有効化
   - チャンネルを指定してWebhook URLを取得

3. **Email設定（Resend使用の場合）**
   - Resendアカウント作成
   - API Keyを取得
   - ドメイン認証

## デプロイ方法

```bash
# ファンクションのデプロイ
supabase functions deploy weekly-review

# 手動実行テスト
supabase functions invoke weekly-review

# スケジュール実行設定（pg_cron使用）
# 毎週月曜日の9:00に実行
SELECT cron.schedule('weekly-review', '0 9 * * 1', 'SELECT net.http_post(url := ''https://your-project.supabase.co/functions/v1/weekly-review'')');
```

## 使用方法

### 手動実行
```bash
curl -X POST https://your-project.supabase.co/functions/v1/weekly-review \
  -H "Authorization: Bearer YOUR_ANON_KEY"
```

### レスポンス例
```json
{
  "success": true,
  "message": "Weekly review completed successfully",
  "stats": {
    "totalEpisodes": 15,
    "tasksCount": 3,
    "overdueCount": 2,
    "upcomingDeadlines": 5,
    "newEpisodes": 1,
    "completedEpisodes": 2
  }
}
```

## スケジュール設定

PostgreSQLのpg_cronを使用して定期実行を設定：

```sql
-- 毎週月曜日の9:00（JST）に実行
SELECT cron.schedule(
  'weekly-review-job',
  '0 0 * * 1',  -- UTC時間（JSTの9:00はUTC 0:00）
  $$
  SELECT net.http_post(
    url := 'https://your-project.supabase.co/functions/v1/weekly-review',
    headers := '{"Authorization": "Bearer YOUR_SERVICE_ROLE_KEY"}'::jsonb
  );
  $$
);

-- スケジュール確認
SELECT * FROM cron.job;

-- スケジュール削除
SELECT cron.unschedule('weekly-review-job');
```

## トラブルシューティング

### ログ確認
```bash
supabase functions logs weekly-review
```

### よくある問題

1. **データベース接続エラー**
   - SUPABASE_URLとSUPABASE_SERVICE_ROLE_KEYを確認

2. **Slack通知が届かない**
   - SLACK_WEBHOOK_URLの形式を確認
   - Slack Appの権限を確認

3. **Email送信失敗**
   - RESEND_API_KEYの有効性を確認
   - EMAIL_DOMAINの認証状況を確認

4. **エピソードデータが取得できない**
   - データベーステーブル名を確認
   - Service Role Keyの権限を確認