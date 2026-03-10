import os
import sys
from pathlib import Path

# Fix python path
repo_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(repo_root))

from tts.tts_config_loader import load_merged_tts_config
from tts.orion_tts_generator import OrionTTSGenerator

cur_dir = Path(__file__).parent
md_path = cur_dir / "Case16_LeftOnRead_EN.md"

with open(md_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

eng_sentences = []
for line in lines:
    if "|" in line:
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 3:
            narration = parts[2]
            
            # Filter pure headers
            if not narration or "Narration (EN)" in narration or "**Orion's Conference Room, Case 16" in narration:
                continue
            if "**`[" in narration:
                continue
            if narration.startswith("**") and narration.endswith("**"):
                narration = narration[2:-2].strip()
            
            if narration:
                eng_sentences.append(narration)

print(f"Extracted {len(eng_sentences)} sentences for TTS.")

output_dir = cur_dir / "output" / "audio_en"
output_dir.mkdir(parents=True, exist_ok=True)

# Generate TTS
config = load_merged_tts_config("OrionEp16") # fallback
generator = OrionTTSGenerator(config)

success_count = 0
for idx, text in enumerate(eng_sentences):
    segment_no = idx + 1
    output_file = output_dir / f"Case16_EN_{segment_no:03d}.mp3"
    
    if output_file.exists():
        print(f"Skipping {output_file.name}")
        success_count += 1
        continue
        
    print(f"Generating [{segment_no:03d}/{len(eng_sentences)}]: {text[:60]}")
    
    try:
        success = generator.generate(
            text=text,
            character="ナレーター",
            output_path=output_file,
            segment_no=segment_no,
            scene="EN_Narration",
            prev_scene="EN_Narration",
            gemini_voice="Aoede", 
            gemini_style_prompt="Speak with intellectual depth and documentary-style narration, calm and authoritative, in fluent English without a foreign accent."
        )
        if not success:
            print(f"Failed to generate {output_file.name}")
        else:
            success_count += 1
    except Exception as e:
        print(f"Error: {e}")

print(f"Done. {success_count}/{len(eng_sentences)} generated successfully.")
