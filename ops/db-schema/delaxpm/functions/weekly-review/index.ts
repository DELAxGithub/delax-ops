import { serve } from 'https://deno.land/std@0.208.0/http/server.ts';
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';
import { format, startOfWeek, endOfWeek, subWeeks, addDays, isBefore } from 'https://esm.sh/date-fns@2.30.0';
import { ja } from 'https://esm.sh/date-fns@2.30.0/locale';

// 型定義の更新
interface Episode {
  id: number;
  episode_id: string;
  title: string;
  episode_type: 'interview' | 'vtr' | 'regular';
  season: number;
  episode_number: number;
  current_status: string;
  director: string;
  due_date?: string;
  interview_guest?: string;
  recording_date?: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

interface EpisodeStatus {
  id: number;
  status_name: string;
  status_order: number;
  color_code: string;
}

interface CalendarTask {
  id: string;
  task_type: string;
  start_date: string;
  end_date: string;
  description?: string;
  is_team_event?: boolean;
}

interface WeeklyReviewData {
  weeklySchedule: {
    tasks: { date: string; task: CalendarTask }[];
    upcomingDeadlines: { episode: Episode; daysUntil: number }[];
    overdueEpisodes: { episode: Episode; daysOverdue: number }[];
  };
  episodeProgress: {
    totalEpisodes: number;
    byStatus: Record<string, number>;
    byType: Record<string, number>;
    recentUpdates: Episode[];
  };
  weeklyStats: {
    newEpisodes: number;
    completedEpisodes: number;
    inProgressEpisodes: number;
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
  const nextWeekEnd = addDays(weekEnd, 7);

  console.log(`レビュー期間: ${format(weekStart, 'yyyy-MM-dd')} 〜 ${format(weekEnd, 'yyyy-MM-dd')}`);

  // 1. 今週のカレンダータスクを取得
  const { data: tasks, error: tasksError } = await supabase
    .from('calendar_tasks')
    .select('*')
    .gte('start_date', format(weekStart, 'yyyy-MM-dd'))
    .lte('end_date', format(weekEnd, 'yyyy-MM-dd'))
    .order('start_date');

  if (tasksError) {
    console.error('カレンダータスク取得エラー:', tasksError);
  }

  // 2. 全エピソード情報を取得
  const { data: episodes, error: episodesError } = await supabase
    .from('episodes')
    .select('*')
    .order('updated_at', { ascending: false });

  if (episodesError) {
    console.error('エピソード取得エラー:', episodesError);
  }

  // 3. エピソードステータス情報を取得
  const { data: statuses, error: statusesError } = await supabase
    .from('episode_statuses')
    .select('*')
    .order('status_order');

  if (statusesError) {
    console.error('ステータス取得エラー:', statusesError);
  }

  // デフォルト値を設定
  const safeEpisodes = episodes || [];
  const safeTasks = tasks || [];
  const safeStatuses = statuses || [];

  console.log(`取得データ: エピソード${safeEpisodes.length}件, タスク${safeTasks.length}件, ステータス${safeStatuses.length}件`);

  // 4. 期限分析
  const today = new Date();
  const upcomingDeadlines = safeEpisodes
    .filter(ep => ep.due_date && ep.current_status !== '完パケ納品')
    .map(ep => {
      const dueDate = new Date(ep.due_date!);
      const daysUntil = Math.ceil((dueDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
      return { episode: ep, daysUntil };
    })
    .filter(item => item.daysUntil >= 0 && item.daysUntil <= 14) // 2週間以内
    .sort((a, b) => a.daysUntil - b.daysUntil);

  const overdueEpisodes = safeEpisodes
    .filter(ep => ep.due_date && ep.current_status !== '完パケ納品')
    .map(ep => {
      const dueDate = new Date(ep.due_date!);
      const daysOverdue = Math.ceil((today.getTime() - dueDate.getTime()) / (1000 * 60 * 60 * 24));
      return { episode: ep, daysOverdue };
    })
    .filter(item => item.daysOverdue > 0)
    .sort((a, b) => b.daysOverdue - a.daysOverdue);

  // 5. ステータス別集計
  const statusCounts: Record<string, number> = {};
  const typeCounts: Record<string, number> = {};
  
  safeEpisodes.forEach(episode => {
    // ステータス別カウント
    const status = episode.current_status || '未設定';
    statusCounts[status] = (statusCounts[status] || 0) + 1;
    
    // タイプ別カウント
    const type = episode.episode_type || 'その他';
    typeCounts[type] = (typeCounts[type] || 0) + 1;
  });

  // 6. 最近更新されたエピソード（1週間以内）
  const recentUpdates = safeEpisodes
    .filter(ep => {
      const updatedAt = new Date(ep.updated_at);
      return updatedAt >= lastWeekStart;
    })
    .slice(0, 10); // 最新10件

  // 7. 週次統計
  const newEpisodes = safeEpisodes.filter(ep => {
    const createdAt = new Date(ep.created_at);
    return createdAt >= weekStart && createdAt <= weekEnd;
  }).length;

  const completedEpisodes = safeEpisodes.filter(ep => {
    const updatedAt = new Date(ep.updated_at);
    return ep.current_status === '完パケ納品' && 
           updatedAt >= weekStart && updatedAt <= weekEnd;
  }).length;

  const inProgressEpisodes = safeEpisodes.filter(ep => 
    ep.current_status && 
    ep.current_status !== '完パケ納品' && 
    ep.current_status !== '台本作成中'
  ).length;

  // 8. 週次レビューデータを構築
  const weeklyReviewData: WeeklyReviewData = {
    weeklySchedule: {
      tasks: safeTasks.map(task => ({
        date: task.start_date,
        task: task as CalendarTask,
      })),
      upcomingDeadlines,
      overdueEpisodes,
    },
    episodeProgress: {
      totalEpisodes: safeEpisodes.length,
      byStatus: statusCounts,
      byType: typeCounts,
      recentUpdates,
    },
    weeklyStats: {
      newEpisodes,
      completedEpisodes,
      inProgressEpisodes,
    },
  };

  console.log('週次レビューデータ生成完了');
  return weeklyReviewData;
}

function formatSlackMessage(data: WeeklyReviewData): any {
  const today = new Date();
  const weekStart = startOfWeek(today, { weekStartsOn: 1 });
  const weekEnd = endOfWeek(weekStart, { weekStartsOn: 1 });

  const message = {
    text: "📊 週次エピソード進捗レビュー",
    blocks: [
      {
        type: "header",
        text: {
          type: "plain_text",
          text: `📊 週次エピソード進捗レビュー`
        }
      },
      {
        type: "section",
        text: {
          type: "mrkdwn",
          text: `*期間:* ${format(weekStart, 'M月d日', { locale: ja })}〜${format(weekEnd, 'M月d日', { locale: ja })}`
        }
      }
    ]
  };

  // 今週の統計
  message.blocks.push({
    type: "section",
    text: {
      type: "mrkdwn",
      text: `*📈 今週の活動*\n` +
            `• 新規エピソード: ${data.weeklyStats.newEpisodes}件\n` +
            `• 完成エピソード: ${data.weeklyStats.completedEpisodes}件\n` +
            `• 制作中エピソード: ${data.weeklyStats.inProgressEpisodes}件`
    }
  });

  // エピソード進捗状況
  if (Object.keys(data.episodeProgress.byStatus).length > 0) {
    const statusText = Object.entries(data.episodeProgress.byStatus)
      .sort((a, b) => b[1] - a[1]) // 件数の多い順
      .slice(0, 8) // 上位8件
      .map(([status, count]) => `• ${status}: ${count}件`)
      .join('\n');

    message.blocks.push({
      type: "section",
      text: {
        type: "mrkdwn",
        text: `*📊 エピソード進捗状況* (全${data.episodeProgress.totalEpisodes}件)\n${statusText}`
      }
    });
  }

  // 期限アラート
  if (data.weeklySchedule.overdueEpisodes.length > 0) {
    const overdueText = data.weeklySchedule.overdueEpisodes
      .slice(0, 5)
      .map(item => `• ${item.episode.episode_id} - ${item.episode.title} (${item.daysOverdue}日遅れ)`)
      .join('\n');

    message.blocks.push({
      type: "section",
      text: {
        type: "mrkdwn",
        text: `*🚨 期限超過アラート*\n${overdueText}`
      }
    });
  }

  // 今後の期限
  if (data.weeklySchedule.upcomingDeadlines.length > 0) {
    const deadlineText = data.weeklySchedule.upcomingDeadlines
      .slice(0, 5)
      .map(item => `• ${item.episode.episode_id} - ${item.episode.title} (あと${item.daysUntil}日)`)
      .join('\n');

    message.blocks.push({
      type: "section",
      text: {
        type: "mrkdwn",
        text: `*⏰ 今後の期限 (2週間以内)*\n${deadlineText}`
      }
    });
  }

  // 今週のタスク
  if (data.weeklySchedule.tasks.length > 0) {
    const taskText = data.weeklySchedule.tasks
      .map(t => `• ${t.date} - ${t.task.task_type}`)
      .join('\n');

    message.blocks.push({
      type: "section",
      text: {
        type: "mrkdwn",
        text: `*📝 今週のタスク*\n${taskText}`
      }
    });
  }

  // エピソードタイプ別統計
  if (Object.keys(data.episodeProgress.byType).length > 0) {
    const typeText = Object.entries(data.episodeProgress.byType)
      .map(([type, count]) => `• ${type}: ${count}件`)
      .join('\n');

    message.blocks.push({
      type: "section",
      text: {
        type: "mrkdwn",
        text: `*🎬 エピソード種別*\n${typeText}`
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
    <title>週次エピソード進捗レビュー</title>
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
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 15px 0;
        }
        .stat-item {
            background: #f7fafc;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }
        .stat-number {
            font-size: 24px;
            font-weight: bold;
            color: #667eea;
        }
        .stat-label {
            color: #4a5568;
            font-size: 14px;
            margin-top: 5px;
        }
        .alert-item {
            padding: 12px;
            border-left: 4px solid #f56565;
            margin-bottom: 12px;
            background: #fed7d7;
            border-radius: 0 8px 8px 0;
        }
        .deadline-item {
            padding: 12px;
            border-left: 4px solid #ed8936;
            margin-bottom: 12px;
            background: #feebc8;
            border-radius: 0 8px 8px 0;
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
        .episode-list {
            max-height: 200px;
            overflow-y: auto;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 週次エピソード進捗レビュー</h1>
        <p>${format(currentWeekStart, 'M月d日', { locale: ja })}〜${format(currentWeekEnd, 'M月d日', { locale: ja })} の進捗報告</p>
    </div>

    <div class="section">
        <h2>📈 今週の活動サマリー</h2>
        <div class="stats-grid">
            <div class="stat-item">
                <div class="stat-number">${reviewData.weeklyStats.newEpisodes}</div>
                <div class="stat-label">新規エピソード</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">${reviewData.weeklyStats.completedEpisodes}</div>
                <div class="stat-label">完成エピソード</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">${reviewData.weeklyStats.inProgressEpisodes}</div>
                <div class="stat-label">制作中エピソード</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">${reviewData.episodeProgress.totalEpisodes}</div>
                <div class="stat-label">総エピソード数</div>
            </div>
        </div>
    </div>

    ${reviewData.weeklySchedule.overdueEpisodes.length > 0 ? `
    <div class="section">
        <h2>🚨 期限超過アラート</h2>
        <div class="episode-list">
            ${reviewData.weeklySchedule.overdueEpisodes.slice(0, 10).map(item => `
            <div class="alert-item">
                <strong>${item.episode.episode_id}</strong> - ${item.episode.title}<br>
                <small>期限: ${item.episode.due_date} (${item.daysOverdue}日遅れ) | ステータス: ${item.episode.current_status}</small>
            </div>
            `).join('')}
        </div>
    </div>
    ` : ''}

    ${reviewData.weeklySchedule.upcomingDeadlines.length > 0 ? `
    <div class="section">
        <h2>⏰ 今後の期限 (2週間以内)</h2>
        <div class="episode-list">
            ${reviewData.weeklySchedule.upcomingDeadlines.slice(0, 10).map(item => `
            <div class="deadline-item">
                <strong>${item.episode.episode_id}</strong> - ${item.episode.title}<br>
                <small>期限: ${item.episode.due_date} (あと${item.daysUntil}日) | ステータス: ${item.episode.current_status}</small>
            </div>
            `).join('')}
        </div>
    </div>
    ` : ''}

    <div class="section">
        <h2>📊 エピソード進捗状況</h2>
        <div class="stats-grid">
            ${Object.entries(reviewData.episodeProgress.byStatus).slice(0, 8).map(([status, count]) => `
            <div class="stat-item">
                <div class="stat-number">${count}</div>
                <div class="stat-label">${status}</div>
            </div>
            `).join('')}
        </div>
    </div>

    ${Object.keys(reviewData.episodeProgress.byType).length > 0 ? `
    <div class="section">
        <h2>🎬 エピソード種別</h2>
        <div class="stats-grid">
            ${Object.entries(reviewData.episodeProgress.byType).map(([type, count]) => `
            <div class="stat-item">
                <div class="stat-number">${count}</div>
                <div class="stat-label">${type}</div>
            </div>
            `).join('')}
        </div>
    </div>
    ` : ''}

    ${reviewData.weeklySchedule.tasks.length > 0 ? `
    <div class="section">
        <h2>📝 今週のタスク</h2>
        ${reviewData.weeklySchedule.tasks.map(task => `
        <div class="task-item">
            <div><strong>${format(new Date(task.date), 'M月d日(E)', { locale: ja })}</strong></div>
            <div>${task.task.task_type}</div>
            ${task.task.description ? `<div><small>${task.task.description}</small></div>` : ''}
        </div>
        `).join('')}
    </div>
    ` : ''}

    <div class="section">
        <h2>🔗 システムアクセス</h2>
        <a href="${baseUrl}/episodes" class="link-button">📺 エピソード一覧</a>
        <a href="${baseUrl}/kanban" class="link-button">📋 進捗すごろく</a>
        <a href="${baseUrl}/calendar" class="link-button">📅 カレンダー</a>
    </div>

    <div class="section">
        <h2>💡 システム活用のヒント</h2>
        <p>📱 <strong>モバイル対応:</strong> スマートフォンからでも進捗確認が可能です</p>
        <p>🔄 <strong>リアルタイム更新:</strong> 他のメンバーの変更が即座に反映されます</p>
        <p>📊 <strong>進捗管理:</strong> カンバンボードで視覚的な進捗管理ができます</p>
        <p>📋 <strong>期限管理:</strong> 期限が近いエピソードは自動的にアラート表示されます</p>
    </div>

    <div class="footer">
        <p>このレビューは自動生成されています</p>
        <p>進捗すごろく - Episode Management System</p>
        <p>生成日時: ${format(new Date(), 'yyyy年M月d日 H:mm', { locale: ja })}</p>
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
        from: '進捗すごろく <noreply@' + (Deno.env.get('EMAIL_DOMAIN') || 'your-domain.com') + '>',
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
    console.log('=== 週次レビュー Edge Function 開始 ===');
    
    // Supabase client
    const supabase = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
    );

    console.log('週次レビューデータ生成開始...');
    const reviewData = await generateWeeklyReview(supabase);

    // Slack通知
    const slackWebhookUrl = Deno.env.get('SLACK_WEBHOOK_URL');
    if (slackWebhookUrl) {
      console.log('Slack通知送信中...');
      const slackMessage = formatSlackMessage(reviewData);
      await sendSlackNotification(slackWebhookUrl, slackMessage);
      console.log('Slack通知送信完了');
    } else {
      console.log('Slack Webhook URL未設定のため、Slack通知をスキップ');
    }

    // メール通知
    const recipient = Deno.env.get('REVIEW_EMAIL');
    const baseUrl = Deno.env.get('APP_BASE_URL');
    
    if (recipient && baseUrl) {
      console.log('メール通知送信中...');
      const today = new Date();
      const weekStart = startOfWeek(today, { weekStartsOn: 1, locale: ja });
      const weekEnd = endOfWeek(weekStart, { weekStartsOn: 1 });
      const subject = `週次エピソード進捗レビュー - ${format(weekStart, 'M月d日', { locale: ja })}〜${format(weekEnd, 'M月d日', { locale: ja })}`;
      
      const htmlContent = generateEmailHTML(reviewData, baseUrl);
      
      await sendEmail({ recipient }, subject, htmlContent);
      console.log('メール送信完了');
    } else {
      console.log('メール設定不完全のため、メール通知をスキップ');
      console.log('不足設定:', {
        REVIEW_EMAIL: !recipient,
        APP_BASE_URL: !baseUrl
      });
    }

    console.log('=== 週次レビュー Edge Function 完了 ===');

    return new Response(
      JSON.stringify({
        success: true,
        message: 'Weekly review completed successfully',
        stats: {
          totalEpisodes: reviewData.episodeProgress.totalEpisodes,
          tasksCount: reviewData.weeklySchedule.tasks.length,
          overdueCount: reviewData.weeklySchedule.overdueEpisodes.length,
          upcomingDeadlines: reviewData.weeklySchedule.upcomingDeadlines.length,
          newEpisodes: reviewData.weeklyStats.newEpisodes,
          completedEpisodes: reviewData.weeklyStats.completedEpisodes,
        },
      }),
      {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        status: 200,
      }
    );

  } catch (error) {
    console.error('週次レビューエラー:', error);
    return new Response(
      JSON.stringify({
        success: false,
        error: error.message,
        timestamp: new Date().toISOString(),
      }),
      {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        status: 500,
      }
    );
  }
});