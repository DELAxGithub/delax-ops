import os
import requests
import json
import base64
import sys
import subprocess
import csv
import yaml
import time
from pathlib import Path

csv_path = "/Users/delaxpro/src/delax-ops/script/Case16_30fortTTS.csv"
yaml_path = "/Users/delaxpro/src/delax-ops/script/TTS音声割り当て_Case16-30.yaml"
output_dir = "/Users/delaxpro/src/delax-ops/script/outputs"

Path(output_dir).mkdir(parents=True, exist_ok=True)

# 1. 割り当てYAMLのパース
lines_to_generate = []
with open(csv_path, "r", encoding="utf-8") as f:
    reader = csv.reader(f)
    header = next(reader)
    # カラム: Case(0), タイプ(1), テキスト(2), 出典/役割(3), 音声割り当て(4), 備考(5)
    for row in reader:
        if len(row) > 4:
            case_no = row[0]
            text = row[2]
            voice_type = row[4]
            if text.strip() and voice_type.strip():
                 lines_to_generate.append({
                     "case": case_no,
                     "text": text,
                     "voice_assigned": voice_type
                 })

# Gemini TTSの声のマッピング
# yamlで想定された音声キャストに対応
voice_map = {
    "老年男性A": "Charon",
    "老年男性B": "Fenrir",
    "老年男性C": "Charon",  # 4人ローテーションなので再利用
    "老年男性D": "Fenrir",
    "若手女性": "Kore",
    "若手女性B": "Aoede",
    "中年男性": "Charon",
    "中年男性B": "Fenrir",
    "中年女性": "Aoede",
    "若手男性": "Puck",
}

# 2. GEMINI_API_KEYの取得
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    env_path = "/Users/delaxpro/src/delax-ops/ops/media/orion/.env"
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as env_f:
            for eline in env_f:
                if eline.startswith("GEMINI_API_KEY="):
                    api_key = eline.strip().split("=", 1)[1].strip('"\'')
                    break

if not api_key:
    print("Error: No GEMINI_API_KEY found in environment or .env file.")
    sys.exit(1)

# 3. Gemini TTS APIの呼び出し
url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent?key={api_key}"
import re
def clean_text_for_gemini(raw_text):
    # Extract alias from <sub alias="phonetic">text</sub>
    cleaned = re.sub(
        r'<sub alias=[\'"]([^\'"]+)[\'"]>([^<]+)</sub>',
        r'\1',
        raw_text
    )
    # Remove all other XML/SSML tags
    cleaned = re.sub(r'<[^>]+>', '', cleaned)
    return re.sub(r'\s+', ' ', cleaned).strip()

print(f"Total lines to generate: {len(lines_to_generate)}")
for i, item in enumerate(lines_to_generate):
    original_text = item["text"]
    text = clean_text_for_gemini(original_text)
    voice_assigned = item["voice_assigned"]
    case_no = item["case"]
    gemini_voice = voice_map.get(voice_assigned, "Charon") # デフォルトはCharon
    
    mp3_name = os.path.join(output_dir, f"Case{case_no}_{i+1:03d}_{voice_assigned}.mp3")
    if os.path.exists(mp3_name):
        continue
    
    print(f"[{i+1}/{len(lines_to_generate)}] Case {case_no} | Voice: {voice_assigned} -> {gemini_voice} | Text: {text[:20]}...")
    
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": text}
                ]
            }
        ],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {"voiceName": gemini_voice}
                }
            }
        }
    }
    
    attempts = 0
    max_attempts = 3
    success = False
    
    while attempts < max_attempts and not success:
        attempts += 1
        resp = requests.post(url, json=payload)
        if resp.status_code == 429:
             print(" Rate limited. Waiting 10s...")
             time.sleep(10)
             continue
        if resp.status_code != 200:
            print(" API Error:", resp.status_code, resp.text)
            break
            
        data = resp.json()
        try:
            b64data = data["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
            pcm_bytes = base64.b64decode(b64data)
            
            # str() is needed for ffmpeg passing
            cmd = [
                "ffmpeg", "-y", "-f", "s16le", "-ar", "24000", "-ac", "1", "-i", "-",
                "-filter:a", "atempo=0.9", mp3_name
            ]
            proc = subprocess.run(cmd, input=pcm_bytes, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            if proc.returncode == 0:
                print(f" -> Saved {mp3_name}")
                success = True
            else:
                print(f" -> ffmpeg error: {proc.stderr.decode('utf-8')}")
                break
                
        except Exception as e:
            print(" Error parsing response or saving file:", e)
            break
            
    # Add a slight delay to avoid hitting rate limits too fast on large batches
    time.sleep(1.0)

print("Done.")
