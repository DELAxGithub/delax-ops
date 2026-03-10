import csv
from pathlib import Path

csv_path = Path('/Users/delaxpro/src/delax-ops/ops/media/orion/projects/OrienEn16/OrionEp16 en.csv')

with open(csv_path, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    a1_clips = []
    for row in reader:
        # Check track column. The 4th column is 'V' (Track).
        # Sometimes header is 'V' or 'V/A'. In this file it's 'V'
        track = row.get('V', '')
        if track == 'A1':
            name = row.get('名前', '')
            # Ignore OP and ED
            if 'OP' not in name and 'ED' not in name:
                a1_clips.append(name)

print("Number of narration items on A1:", len(a1_clips))
for i, c in enumerate(a1_clips):
    print(f"{i+1}: {c}")
