import os
import sys
from pathlib import Path

try:
    from google import genai
except ImportError:
    print("Could not import google.genai")
    sys.exit(1)

# Load .env
env_path = Path(__file__).resolve().parents[2] / ".env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            os.environ[key.strip()] = val.strip()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    api_key = os.getenv("GEMINI_API_KEY_1")

if not api_key:
    print("No API key")
    sys.exit(1)

client = genai.Client(api_key=api_key)

cur_dir = Path(__file__).parent
with open(cur_dir / 'S2ep1.srt', 'r', encoding='utf-8') as f:
    srt_content = f.read()

with open(cur_dir / 'Case16_LeftOnRead_EN.md', 'r', encoding='utf-8') as f:
    md_content = f.read()

prompt = f"""
You are an expert translator. The user wants an English SRT file that perfectly matches the timing and block count of the original Japanese SRT file.
The English narration text is ALREADY WRITTEN in the provided Markdown file. You just need to apply the English text from the Markdown to replace the Japanese text in the SRT, preserving the SRT formatting, timestamps, and block numbers exactly. 

There MUST be exactly 94 blocks in your output, just like the input.
Ensure you use the exact English phrases from the markdown where applicable.
If the markdown text combines sentences, split them across the blocks to match the Japanese timing as best as possible.

Here is the Japanese SRT to translate:
```
{srt_content}
```

Here is the English Markdown reference:
```
{md_content}
```

Return ONLY the raw English SRT text, nothing else. Make sure there are exactly 94 blocks, maintaining block indices 1 to 94.
"""

print("Calling Gemini API with google.genai...")
response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents=prompt,
    config={'temperature': 0.1}
)
eng_srt = response.text.strip()
if eng_srt.startswith("```srt"):
    eng_srt = eng_srt[6:]
elif eng_srt.startswith("```"):
    eng_srt = eng_srt[3:]
if eng_srt.endswith("```"):
    eng_srt = eng_srt[:-3]
eng_srt = eng_srt.strip()

with open(cur_dir / 'S2ep1_EN.srt', 'w', encoding='utf-8') as f:
    f.write(eng_srt)

print("Translation completed. Saved to S2ep1_EN.srt")
