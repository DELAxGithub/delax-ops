import re
from pathlib import Path

def parse_markdown(md_path):
    with open(md_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    eng_sentences = []
    for line in lines:
        if "|" in line:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 3:
                tc = parts[1]
                narration = parts[2]
                
                # Filter out pure headers like [OPENING] or TC matching
                if not narration or "Narration" in narration or "**Orion's Conference" in narration:
                    continue
                if "**`[" in narration:
                    continue
                if narration.startswith("**") and narration.endswith("**"):
                    narration = narration[2:-2]
                
                if narration:
                    eng_sentences.append(narration)
    return eng_sentences

def parse_srt(srt_path):
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    blocks = content.strip().split("\n\n")
    return blocks

eng = parse_markdown('Case16_LeftOnRead_EN.md')
blocks = parse_srt('S2ep1.srt')

print(f"English sentences from MD: {len(eng)}")
print(f"SRT blocks: {len(blocks)}")

# Let's print some to see alignment
for i in range(min(5, len(eng))):
    print("---")
    print(f"MD: {eng[i]}")
    print(f"SRT:\n{blocks[i]}")

