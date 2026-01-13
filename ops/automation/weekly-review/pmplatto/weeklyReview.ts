import { config } from 'dotenv';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { readFileSync } from 'fs';

// Get the directory path of the current file
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Load environment variables from .env file in the project root
const envPath = join(__dirname, '../../.env');
try {
  const envFile = readFileSync(envPath, 'utf-8');
  config({ path: envPath });
  console.log('Environment variables loaded successfully');
  
  // デバッグ用に環境変数の状態を出力
  console.log('Current environment variables:');
  console.log(process.env);
  
  // Supabase関連の環境変数を具体的に確認
  console.log('\nSupabase environment variables:');
  console.log('VITE_SUPABASE_URL:', process.env.VITE_SUPABASE_URL);
  console.log('VITE_SUPABASE_ANON_KEY:', process.env.VITE_SUPABASE_ANON_KEY);
} catch (error) {
  console.error('Error loading .env file:', error);
  process.exit(1);
}

import schedule from 'node-schedule';
import { generateWeeklyReview, formatSlackMessage, sendToSlack } from '../lib/weeklyReview';

async function runWeeklyReview() {
  try {
    console.log('Generating weekly review...');
    const reviewData = await generateWeeklyReview();
    
    console.log('Formatting Slack message...');
    const message = formatSlackMessage(reviewData);
    
    console.log('Sending to Slack...');
    await sendToSlack(message);
    
    console.log('Weekly review completed successfully');
  } catch (error) {
    console.error('Error running weekly review:', error);
    // エラーの詳細情報を出力
    if (error instanceof Error) {
      console.error('Error details:', {
        name: error.name,
        message: error.message,
        stack: error.stack
      });
    }
  }
}

// スケジュール設定（毎週月曜日の朝8時 JST）
const rule = new schedule.RecurrenceRule();
rule.dayOfWeek = 1; // 月曜日
rule.hour = 8;
rule.minute = 0;
rule.tz = 'Asia/Tokyo';

// スケジュールジョブを開始
schedule.scheduleJob(rule, runWeeklyReview);

console.log('Weekly review scheduler started');

// 開発時のテスト用：即時実行
if (process.env.NODE_ENV === 'development') {
  runWeeklyReview();
}