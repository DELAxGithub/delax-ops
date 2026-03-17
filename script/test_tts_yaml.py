#!/usr/bin/env python3
"""YAMLからGemini 2.5 TTS で音声生成（下から逆順、レートリミット対応）

ファイル名規則:
  {case番号}_{セクション}_{連番}_{voice}_{テキスト冒頭10文字}.mp3
  例: case30_引用_01_老年男性A_暗黙知は個人的で.mp3
"""

import os
import sys
import re
import base64
import subprocess
import time
import requests
import yaml
from pathlib import Path
from collections import OrderedDict

# 読み付きYAMLがあればそちらを優先、なければ通常版
YAML_READING = Path(__file__).parent / "TTS音声割り当て_読み付き_Case16-30.yaml"
YAML_PLAIN = Path(__file__).parent / "TTS音声割り当て_Case16-30.yaml"
OUTPUT_DIR = Path(__file__).parent / "tts_output_all"
ENV_PATH = Path(__file__).resolve().parents[1] / "ops/media/orion/.env"

# Gemini TTS voice mapping
VOICE_MAP = {
    "老年男性A": "Charon",
    "老年男性B": "Fenrir",
    "老年男性C": "Orus",
    "老年男性D": "Puck",
    "若手女性": "Kore",
    "若手女性B": "Kore",
    "若手男性": "Puck",
    "中年男性": "Charon",
    "中年男性B": "Fenrir",
    "中年女性": "Aoede",
}

REQUEST_DELAY_SEC = 4.0  # レートリミット対策


def load_api_key():
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        return key
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            if line.startswith("GEMINI_API_KEY="):
                return line.split("=", 1)[1].strip().strip("'\"")
    return None


def sanitize_filename(text, max_len=10):
    """テキスト冒頭をファイル名用に整形"""
    clean = re.sub(r'[（）\(\)「」『』、。？！\s\n]', '', text)
    return clean[:max_len]


def extract_case_number(case_key):
    """case16_xxx → 16"""
    m = re.match(r'case(\d+)', case_key)
    return int(m.group(1)) if m else 0


def collect_all_entries(data):
    """全エントリをcase→section→itemsの順で収集"""
    entries = []
    for case_key, case_data in data.items():
        if not isinstance(case_data, dict):
            continue
        case_num = extract_case_number(case_key)
        for section in ["引用", "セリフ"]:
            items = case_data.get(section, [])
            if not isinstance(items, list):
                continue
            for idx, item in enumerate(items, 1):
                text = item.get("tts_text") or item.get("text", "")
                orig_text = item.get("text", "")
                voice = item.get("voice", "不明")
                if not text:
                    continue
                entries.append({
                    "case_num": case_num,
                    "case_key": case_key,
                    "section": section,
                    "idx": idx,
                    "text": text,
                    "orig_text": orig_text,
                    "voice": voice,
                })
    return entries


def build_filename(entry):
    """case30_引用_01_老年男性A_暗黙知は個人的で.mp3"""
    snippet = sanitize_filename(entry["orig_text"])
    return f"case{entry['case_num']:02d}_{entry['section']}_{entry['idx']:02d}_{entry['voice']}_{snippet}.mp3"


def generate_tts(text, gemini_voice, api_key, output_path):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent?key={api_key}"

    payload = {
        "contents": [{"parts": [{"text": text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {"voiceName": gemini_voice}
                }
            },
        },
    }

    for attempt in range(3):
        try:
            resp = requests.post(url, json=payload, timeout=60)
        except requests.exceptions.Timeout:
            print(f"    Timeout (attempt {attempt+1}/3)")
            time.sleep(5)
            continue

        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", 30))
            print(f"    Rate limited! Waiting {retry_after}s...")
            time.sleep(retry_after)
            continue

        if resp.status_code != 200:
            print(f"    API Error: {resp.status_code} {resp.text[:150]}")
            return False

        data = resp.json()
        try:
            b64data = data["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
        except (KeyError, IndexError):
            print(f"    No audio data in response (attempt {attempt+1}/3)")
            time.sleep(5)
            continue

        pcm_bytes = base64.b64decode(b64data)
        cmd = [
            "ffmpeg", "-y", "-f", "s16le", "-ar", "24000", "-ac", "1",
            "-i", "-", "-filter:a", "atempo=0.9", str(output_path),
        ]
        proc = subprocess.run(cmd, input=pcm_bytes, capture_output=True)
        if proc.returncode != 0:
            print(f"    ffmpeg error: {proc.stderr.decode('utf-8', errors='ignore')[:150]}")
            return False
        return True

    return False


def main():
    api_key = load_api_key()
    if not api_key:
        print("GEMINI_API_KEY not found")
        sys.exit(1)

    # 読み付きYAMLを優先
    yaml_path = YAML_READING if YAML_READING.exists() else YAML_PLAIN
    print(f"Using: {yaml_path.name}")

    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    entries = collect_all_entries(data)

    # 下から逆順（case番号降順 → セクション → idx降順）
    entries.sort(key=lambda e: (-e["case_num"], e["section"], -e["idx"]))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # スキップ済みファイルのチェック
    existing = set(f.name for f in OUTPUT_DIR.glob("*.mp3"))

    total = len(entries)
    generated = 0
    skipped = 0

    print(f"Total entries: {total} | Output: {OUTPUT_DIR}")
    print(f"Order: case30 -> case16 (reverse)\n")

    for i, entry in enumerate(entries, 1):
        filename = build_filename(entry)
        output_path = OUTPUT_DIR / filename
        gemini_voice = VOICE_MAP.get(entry["voice"], "Charon")

        # 既に生成済みならスキップ
        if filename in existing:
            print(f"[{i}/{total}] SKIP (exists): {filename}")
            skipped += 1
            continue

        print(f"[{i}/{total}] case{entry['case_num']:02d} {entry['section']} #{entry['idx']:02d} | {entry['voice']} -> {gemini_voice}")
        print(f"  TTS: {entry['text'][:60]}...")

        if generate_tts(entry["text"], gemini_voice, api_key, output_path):
            print(f"  -> {filename}")
            generated += 1
        else:
            print(f"  -> FAILED: {filename}")

        # レートリミット対策
        if i < total:
            time.sleep(REQUEST_DELAY_SEC)

    print(f"\nDone! Generated: {generated}, Skipped: {skipped}, Failed: {total - generated - skipped}")


if __name__ == "__main__":
    main()
