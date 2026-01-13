import { serve } from 'https://deno.land/std@0.208.0/http/server.ts';
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';
import { format, startOfWeek, endOfWeek, subWeeks } from 'https://esm.sh/date-fns@2.30.0';
import { ja } from 'https://esm.sh/date-fns@2.30.0/locale';

interface Program {
  id: number;
  program_id: string;
  title: string;
  first_air_date?: string;
  filming_date?: string;
  status: string;
  created_at: string;
  updated_at: string;
}

interface CalendarTask {
  id: string;
  task_type: string;
  start_date: string;
  end_date: string;
  program?: Program;
  is_team_event?: boolean;
}

interface WeeklyReviewData {
  weeklySchedule: {
    broadcasts: { date: string; program: Program }[];
    recordings: { date: string; program: Program }[];
    tasks: { date: string; task: CalendarTask; program?: Program }[];
  };
  statusSummary: Record<string, number>;
  recentUpdates: {
    newPrograms: Program[];
    statusChanges: any[];
  };
}

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

async function generateWeeklyReview(supabase: any): Promise<WeeklyReviewData> {
  const now = new Date();
  const weekStart = startOfWeek(now, { weekStartsOn: 1 });
  const weekEnd = endOfWeek(weekStart, { weekStartsOn: 1 });
  const lastWeekStart = subWeeks(weekStart, 1);

  // 今週のタスクを取得
  const { data: tasks } = await supabase
    .from('calendar_tasks')
    .select(`
      *,
      program:programs (
        id,
        program_id,
        title
      )
    `)
    .gte('start_date', format(weekStart, 'yyyy-MM-dd'))
    .lte('end_date', format(weekEnd, 'yyyy-MM-dd'));

  // プログラムの代わりにエピソードを使用（エピソードデータがある場合）
  // 現在はプログラムテーブルが廃止予定のため、基本的なタスク情報のみ使用

  // ステータス別の番組数を集計（プログラムが存在する場合のみ）
  const statusSummary: Record<string, number> = {};

  // 週次レビューデータを構築
  const weeklyReviewData: WeeklyReviewData = {
    weeklySchedule: {
      broadcasts: [], // プログラムテーブル廃止のため空
      recordings: [],  // プログラムテーブル廃止のため空
      tasks: (tasks || [])
        .map(task => ({
          date: task.start_date,
          task: task as CalendarTask,
          program: task.program as Program | undefined,
        }))
        .sort((a, b) => a.date.localeCompare(b.date)),
    },
    statusSummary,
    recentUpdates: {
      newPrograms: [],
      statusChanges: [],
    },
  };

  return weeklyReviewData;
}

function formatSlackMessage(data: WeeklyReviewData): any {
  const message = {
    text: "📊 週次レビュー",
    blocks: [
      {
        type: "header",
        text: {
          type: "plain_text",
          text: "📊 週次レビュー"
        }
      },
    ]
  };

  // タスク予定
  if (data.weeklySchedule.tasks.length > 0) {
    message.blocks.push({
      type: "section",
      text: {
        type: "mrkdwn",
        text: "📝 *今週のタスク*\n" + data.weeklySchedule.tasks
          .map(t => `• ${t.date} ${t.task.task_type}${t.program ? ` (${t.program.program_id})` : ''}`)
          .join("\n")
      }
    });
  }

  return message;
}

function generateEmailHTML(reviewData: WeeklyReviewData, baseUrl: string): string {
  const today = new Date();
  const currentWeekStart = startOfWeek(today, { weekStartsOn: 1, locale: ja });
  const currentWeekEnd = endOfWeek(currentWeekStart, { weekStartsOn: 1 });

  return `
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>週次レビュー</title>
    <style>
        body {
            font-family: 'Hiragino Sans', 'Hiragino Kaku Gothic ProN', 'Yu Gothic', 'Meiryo', sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f8fafc;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 12px;
            text-align: center;
            margin-bottom: 30px;
        }
        .section {
            background: white;
            padding: 25px;
            border-radius: 12px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }
        .task-item {
            padding: 12px;
            border-left: 4px solid #667eea;
            margin-bottom: 12px;
            background: #f7fafc;
            border-radius: 0 8px 8px 0;
        }
        .link-button {
            display: inline-block;
            background: #667eea;
            color: white;
            text-decoration: none;
            padding: 12px 24px;
            border-radius: 8px;
            font-weight: 600;
            margin: 10px 10px 10px 0;
        }
        .footer {
            text-align: center;
            color: #718096;
            font-size: 14px;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #e2e8f0;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 週次レビュー</h1>
        <p>${format(currentWeekStart, 'M月d日', { locale: ja })}〜${format(currentWeekEnd, 'M月d日', { locale: ja })} の活動報告</p>
    </div>

    <div class="section">
        <h2>🔗 システムアクセス</h2>
        <a href="${baseUrl}/calendar" class="link-button">📅 カレンダー</a>
        <a href="${baseUrl}/kanban" class="link-button">📋 進捗すごろく</a>
        <a href="${baseUrl}/episodes" class="link-button">📺 エピソード一覧</a>
    </div>

    ${reviewData.weeklySchedule.tasks.length > 0 ? `
    <div class="section">
        <h2>📝 今週のタスク</h2>
        ${reviewData.weeklySchedule.tasks.map(task => `
        <div class="task-item">
            <div><strong>${format(new Date(task.date), 'M月d日(E)', { locale: ja })}</strong></div>
            <div>${task.task.task_type}${task.program ? ` (${task.program.program_id})` : ''}</div>
        </div>
        `).join('')}
    </div>
    ` : ''}

    <div class="section">
        <h2>💡 ヒント</h2>
        <p>📱 システムはモバイルでも利用可能です</p>
        <p>🔄 リアルタイム更新により、他のメンバーの変更も即座に反映されます</p>
        <p>📊 進捗管理の詳細は各ページで確認できます</p>
    </div>

    <div class="footer">
        <p>このレビューは自動生成されています</p>
        <p>リベラリー進捗すごろく - Program Management System</p>
    </div>
</body>
</html>
  `;
}

async function sendSlackNotification(webhookUrl: string, message: any): Promise<void> {
  const response = await fetch(webhookUrl, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(message),
  });

  if (!response.ok) {
    throw new Error(`Failed to send Slack notification: ${response.statusText}`);
  }
}

async function sendEmail(config: any, subject: string, htmlContent: string): Promise<void> {
  // ResendやSendGridなどのメールサービスAPIを使用
  // 環境変数でサービスを選択可能にする
  
  const emailService = Deno.env.get('EMAIL_SERVICE') || 'resend';
  
  if (emailService === 'resend') {
    const resendApiKey = Deno.env.get('RESEND_API_KEY');
    if (!resendApiKey) {
      throw new Error('RESEND_API_KEY is not configured');
    }

    const response = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${resendApiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        from: 'リベラリー進捗すごろく <noreply@' + (Deno.env.get('EMAIL_DOMAIN') || 'your-domain.com') + '>',
        to: [config.recipient],
        subject,
        html: htmlContent,
      }),
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to send email via Resend: ${error}`);
    }
  } else {
    throw new Error(`Unsupported email service: ${emailService}`);
  }
}

serve(async (req) => {
  // CORS preflight
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders });
  }

  try {
    // Supabase client
    const supabase = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
    );

    console.log('Generating weekly review...');
    const reviewData = await generateWeeklyReview(supabase);

    // Slack通知
    const slackWebhookUrl = Deno.env.get('SLACK_WEBHOOK_URL');
    if (slackWebhookUrl) {
      console.log('Sending Slack notification...');
      const slackMessage = formatSlackMessage(reviewData);
      await sendSlackNotification(slackWebhookUrl, slackMessage);
      console.log('Slack notification sent');
    } else {
      console.log('Slack webhook URL not configured, skipping Slack notification');
    }

    // メール通知
    const recipient = Deno.env.get('REVIEW_EMAIL');
    const baseUrl = Deno.env.get('APP_BASE_URL');
    
    if (recipient && baseUrl) {
      console.log('Sending email notification...');
      const today = new Date();
      const weekStart = startOfWeek(today, { weekStartsOn: 1, locale: ja });
      const weekEnd = endOfWeek(weekStart, { weekStartsOn: 1 });
      const subject = `週次レビュー - ${format(weekStart, 'M月d日', { locale: ja })}〜${format(weekEnd, 'M月d日', { locale: ja })}`;
      
      const htmlContent = generateEmailHTML(reviewData, baseUrl);
      
      await sendEmail({ recipient }, subject, htmlContent);
      console.log('Email sent successfully');
    } else {
      console.log('Email configuration incomplete, skipping email notification');
    }

    return new Response(
      JSON.stringify({
        success: true,
        message: 'Weekly review completed successfully',
        tasksCount: reviewData.weeklySchedule.tasks.length,
      }),
      {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        status: 200,
      }
    );

  } catch (error) {
    console.error('Error in weekly review:', error);
    return new Response(
      JSON.stringify({
        success: false,
        error: error.message,
      }),
      {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        status: 500,
      }
    );
  }
});