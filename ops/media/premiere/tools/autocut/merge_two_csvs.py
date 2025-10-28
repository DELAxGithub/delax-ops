#!/usr/bin/env python3
"""
Merge two speaker-specific transcript CSVs into a single CSV formatted for Step 1.

Input CSVs must have headers: Speaker Name, Start Time, End Time, Text
Output columns:
  色選択, イン点, アウト点, スピーカーネーム, スピーカーAの文字起こし, スピーカーBの文字起こし, AやB以外

Speaker A/B are assigned to the two most frequent speakers across both CSVs.
Rows are merged and sorted by イン点 timecode ascending.
"""

import csv
import os
import sys
from typing import List, Dict, Tuple


STEP1_HEADERS = [
    '色選択',
    'イン点',
    'アウト点',
    'スピーカーネーム',
    'スピーカーAの文字起こし',
    'スピーカーBの文字起こし',
    'AやB以外',
]


def timecode_to_frames(tc: str, fps: int = 30) -> int:
    if not tc:
        return 0
    parts = tc.replace(';', ':').split(':')
    try:
        if len(parts) == 4:
            h, m, s, f = map(int, parts)
        elif len(parts) == 3:
            h = 0
            m, s, f = map(int, parts)
        elif len(parts) == 2:
            h = m = 0
            s, f = map(int, parts)
        else:
            return 0
    except ValueError:
        return 0
    return (h * 3600 + m * 60 + s) * fps + f


def read_csv_rows(path: str) -> List[Dict[str, str]]:
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = [
            {
                'Speaker Name': (r.get('Speaker Name') or '').strip(),
                'Start Time': (r.get('Start Time') or '').strip(),
                'End Time': (r.get('End Time') or '').strip(),
                'Text': (r.get('Text') or '').strip(),
            }
            for r in reader
        ]
    return rows


def assign_speakers(rows: List[Dict[str, str]]) -> Tuple[str, str]:
    freq: Dict[str, int] = {}
    for r in rows:
        sp = r['Speaker Name']
        if not sp:
            continue
        freq[sp] = freq.get(sp, 0) + 1
    sorted_sp = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    a = sorted_sp[0][0] if len(sorted_sp) > 0 else ''
    b = sorted_sp[1][0] if len(sorted_sp) > 1 else ''
    return a, b


def merge_two_csvs(csv_a: str, csv_b: str, assign_by: str = 'file') -> List[List[str]]:
    rows_a = read_csv_rows(csv_a)
    rows_b = read_csv_rows(csv_b)
    all_rows = rows_a + rows_b

    # Determine assignment strategy
    if assign_by == 'freq':
        sp_a, sp_b = assign_speakers(all_rows)
        assign_mode = 'freq'
    else:
        # file-based: every row from csv_a -> A, from csv_b -> B
        sp_a, sp_b = None, None
        assign_mode = 'file'

    # Convert each input row to output row shape
    out_rows: List[List[str]] = []
    for r in all_rows:
        in_tc = r['Start Time'].replace(';', ':')
        out_tc = r['End Time'].replace(';', ':')
        speaker = r['Speaker Name']
        text = r['Text']

        row = [''] * len(STEP1_HEADERS)
        row[STEP1_HEADERS.index('色選択')] = ''
        row[STEP1_HEADERS.index('イン点')] = in_tc
        row[STEP1_HEADERS.index('アウト点')] = out_tc
        row[STEP1_HEADERS.index('スピーカーネーム')] = speaker
        if assign_mode == 'file':
            # Decide by which file this row came from
            # We detect membership by object identity in original lists
            if r in rows_a:
                row[STEP1_HEADERS.index('スピーカーAの文字起こし')] = text
            elif r in rows_b:
                row[STEP1_HEADERS.index('スピーカーBの文字起こし')] = text
            else:
                row[STEP1_HEADERS.index('AやB以外')] = text
        else:
            if sp_a and speaker == sp_a:
                row[STEP1_HEADERS.index('スピーカーAの文字起こし')] = text
            elif sp_b and speaker == sp_b:
                row[STEP1_HEADERS.index('スピーカーBの文字起こし')] = text
            else:
                row[STEP1_HEADERS.index('AやB以外')] = text
        out_rows.append(row)

    # Sort by in-point frames
    out_rows.sort(key=lambda r: timecode_to_frames(r[STEP1_HEADERS.index('イン点')]))

    # Prepend header
    return [STEP1_HEADERS] + out_rows


def write_csv(path: str, rows: List[List[str]]):
    with open(path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(rows)


def main():
    if len(sys.argv) < 3:
        print('Usage: python premiere/tools/autocut/merge_two_csvs.py <speakerA.csv> <speakerB.csv> [output.csv] [--by file|freq]')
        sys.exit(1)

    csv1 = sys.argv[1]
    csv2 = sys.argv[2]
    assign_by = 'file'
    out_path = (
        sys.argv[3]
        if len(sys.argv) >= 4
        else os.path.join(
            os.path.dirname(csv1),
            f"merged_{os.path.splitext(os.path.basename(csv1))[0]}_{os.path.splitext(os.path.basename(csv2))[0]}.csv",
        )
    )
    if len(sys.argv) >= 5 and sys.argv[4] in ('--by', '--assign-by'):
        if len(sys.argv) >= 6:
            assign_by = sys.argv[5]
        else:
            print('Error: --by requires a value (file|freq)')
            sys.exit(1)

    merged = merge_two_csvs(csv1, csv2, assign_by=assign_by)
    write_csv(out_path, merged)
    print(f'Merged CSV written: {out_path}')


if __name__ == '__main__':
    main()
