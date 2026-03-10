import sys
import xml.etree.ElementTree as ET
from pathlib import Path
import re
import subprocess

repo_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(repo_root))

from core.writers.xml import write_fcp7_xml

cur_dir = Path(__file__).parent
md_path = cur_dir / "Case16_LeftOnRead_EN.md"
srt_path = cur_dir / "S2ep1_EN.srt"
audio_dir = cur_dir / "output" / "audio_en"

with open(md_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

eng_sentences = []
for line in lines:
    if "|" in line:
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 3:
            narration = parts[2]
            if not narration or "Narration (EN)" in narration or "**Orion's Conference Room, Case 16" in narration:
                continue
            if "**`[" in narration:
                continue
            if narration.startswith("**") and narration.endswith("**"):
                narration = narration[2:-2].strip()
            if narration:
                eng_sentences.append(narration)

with open(srt_path, 'r', encoding='utf-8') as f:
    srt_blocks = f.read().strip().split("\n\n")

def parse_time(t_str):
    t_str = t_str.replace(',', '.')
    h, m, s = t_str.split(':')
    return int(h)*3600 + int(m)*60 + float(s)

block_info = []
for b in srt_blocks:
    l = b.strip().split('\n')
    if len(l) >= 3:
        st, et = l[1].split(' --> ')
        text = " ".join(l[2:]).replace('<b>', '').replace('</b>', '').strip()
        block_info.append({'start': parse_time(st), 'text': text})

def normalize(t):
    return re.sub(r'[^a-zA-Z0-9]', '', t).lower()

matches = []
for i, sentence in enumerate(eng_sentences):
    ns = normalize(sentence)
    best = 0
    for b in block_info:
        nb = normalize(b['text'])
        if nb in ns or ns in nb:
            best = b['start']
            break
    matches.append(best)

for i in range(1, len(matches)):
    if matches[i] <= matches[i-1]:
        matches[i] = matches[i-1] + 1.0

def get_mp3_dur(p):
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(p)]
    return float(subprocess.check_output(cmd).decode().strip())

class DummyAudioSegment:
    def __init__(self, index, duration_sec, sample_rate=24000):
        self.index = index
        self.duration_sec = duration_sec
        self.sample_rate = sample_rate

class DummyTimelineSegment:
    def __init__(self, index, start_time_sec, end_time_sec, audio_filename, audio_duration_sec):
        self.index = index
        self.start_time_sec = start_time_sec
        self.end_time_sec = end_time_sec
        self.audio_filename = audio_filename
        self.audio_duration_sec = audio_duration_sec

timeline_segments = []
audio_segments = []

for idx, sentence in enumerate(eng_sentences):
    segment_no = idx + 1
    mp3 = audio_dir / f"Case16_EN_{segment_no:03d}.mp3"
    if not mp3.exists():
        continue
    dur = get_mp3_dur(mp3)
    st = matches[idx]
    et = st + dur
    
    t_seg = DummyTimelineSegment(segment_no, st, et, mp3.name, dur)
    a_seg = DummyAudioSegment(segment_no, dur)
    timeline_segments.append(t_seg)
    audio_segments.append(a_seg)


output_xml = cur_dir / "English_TTS_Timeline.xml"
write_fcp7_xml(
    output_xml, 
    timeline_segments, 
    audio_segments, 
    "OrienEn16_English", 
    fps=23.976, # Typical framerate
    audio_dir=audio_dir
)
print("Done writing FCP7 XML to", output_xml.name)
