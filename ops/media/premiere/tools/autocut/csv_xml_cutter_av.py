#!/usr/bin/env python3
"""
CSV + XML Timeline Cutter (Audio + Video)
Clones the original cutter and adds video track regeneration alongside audio edits.
"""

import csv
import xml.etree.ElementTree as ET
from xml.dom import minidom
import uuid
import os
import sys

# Try to import tkinter, but also verify it can initialize (fallback to CLI on TclError)
try:
    import tkinter as tk
    from tkinter import filedialog, messagebox
    try:
        _root_test = tk.Tk()
        _root_test.withdraw()
        _root_test.destroy()
        HAS_GUI = True
    except Exception:
        # Tkinter is present but cannot open a display or initialize properly
        HAS_GUI = False
except Exception:
    HAS_GUI = False


DEFAULT_TIMELINE_FPS = 30000 / 1001  # Premiere NTSC timeline fps (~29.97)


def timecode_to_frames(timecode, fps=DEFAULT_TIMELINE_FPS):
    """Convert timecode string to frame number"""
    if not timecode or timecode.strip() == '':
        return 0
    
    # Handle both : and ; separators
    parts = timecode.replace(';', ':').split(':')
    
    if len(parts) == 4:  # HH:MM:SS:FF
        hours, minutes, seconds, frames = map(int, parts)
    elif len(parts) == 3:  # MM:SS:FF
        hours = 0
        minutes, seconds, frames = map(int, parts)
    elif len(parts) == 2:  # SS:FF
        hours = minutes = 0
        seconds, frames = map(int, parts)
    else:
        return 0
    
    total_frames = (hours * 3600 + minutes * 60 + seconds) * fps + frames
    return int(round(total_frames))


def frames_to_ppro_ticks(frames, fps=DEFAULT_TIMELINE_FPS):
    """Convert frames to Premiere Pro ticks (254016000000 per second)"""
    seconds = frames / fps
    return int(seconds * 254016000000)


def csv_color_to_premiere_label(csv_color):
    """Convert CSV color to Premiere Pro label"""
    # 直接Premiere Proラベル名を使用（GASと統一）
    valid_labels = [
        'Violet', 'Rose', 'Mango', 'Yellow', 'Lavender', 'Caribbean', 
        'Tan', 'Forest', 'Blue', 'Purple', 'Teal', 'Brown', 'Gray',
        'Iris', 'Cerulean', 'Magenta'
    ]
    
    # 古い色名からの変換マッピング（後方互換性のため）
    legacy_color_map = {
        'rose': 'Rose',
        'pink': 'Rose', 
        'cyan': 'Caribbean',
        'blue': 'Blue',
        'mint': 'Mango',
        'green': 'Forest',
        'yellow': 'Yellow',
        'orange': 'Mango',
        'red': 'Rose',
        'purple': 'Purple',
        'brown': 'Brown',
        'gray': 'Gray',
        'lavender': 'Lavender',
        'tan': 'Tan',
        'teal': 'Teal',
        'magenta': 'Magenta',
        'violet': 'Violet',
        'forest': 'Forest',
        'iris': 'Iris',
        'cerulean': 'Cerulean',
        'caribbean': 'Caribbean',
        'mango': 'Mango'
    }
    
    # 空の場合はデフォルト
    if not csv_color or csv_color.strip() == '':
        return 'Caribbean'
    
    # そのままPremiereラベル名として有効かチェック
    if csv_color in valid_labels:
        return csv_color
    
    # 古い色名から変換
    return legacy_color_map.get(csv_color.lower(), 'Caribbean')


def ensure(parent, tag):
    """Ensure an XML child exists and return it."""
    child = parent.find(tag)
    if child is None:
        child = ET.SubElement(parent, tag)
    return child


def parse_int(text):
    """Parse int safely; returns None on failure."""
    if text is None:
        return None
    text = str(text).strip()
    if not text:
        return None
    try:
        return int(text)
    except Exception:
        try:
            return int(float(text))
        except Exception:
            return None


def extract_media_files_from_xml(xml_file_path):
    """Extract referenced media file information from existing XML.
    Returns a list of dicts with keys: name, pathurl, element, source_duration, file_id, masterclipid.
    """
    tree = ET.parse(xml_file_path)
    root = tree.getroot()

    media_files = []
    seen_names = set()

    # Find all clipitems with file references
    for clipitem in root.findall('.//clipitem'):
        file_elem = clipitem.find('file')
        if file_elem is not None:
            name_elem = file_elem.find('name')
            pathurl_elem = file_elem.find('pathurl')

            # Some clipitems may only have <file id="..."/> referencing a previous full definition
            file_id = file_elem.get('id')
            full_file_elem = None
            if file_id:
                # Try to get the full file definition (may point to another clipitem's file)
                full_file_elem = root.find(f".//media/file[@id='{file_id}']")
                if full_file_elem is None:
                    # Fallback: use this file element itself
                    full_file_elem = file_elem
            else:
                full_file_elem = file_elem

            # Prefer values from the full file element if present
            if full_file_elem is not None:
                if name_elem is None:
                    name_elem = full_file_elem.find('name')
                if pathurl_elem is None:
                    pathurl_elem = full_file_elem.find('pathurl')

            if name_elem is not None and pathurl_elem is not None:
                name = name_elem.text
                if name in seen_names:
                    continue

                file_info = {
                    'name': name,
                    'pathurl': pathurl_elem.text,
                    'element': full_file_elem,
                }

                # Source duration
                duration_elem = full_file_elem.find('duration') if full_file_elem is not None else None
                if duration_elem is not None and (duration_elem.text or '').isdigit():
                    file_info['source_duration'] = int(duration_elem.text)

                # IDs
                if file_id is None and full_file_elem is not None:
                    file_id = full_file_elem.get('id')
                if file_id:
                    file_info['file_id'] = file_id

                masterclipid_elem = clipitem.find('masterclipid')
                if masterclipid_elem is not None and masterclipid_elem.text:
                    file_info['masterclipid'] = masterclipid_elem.text

                seen_names.add(name)
                media_files.append(file_info)

    print(f"XMLから抽出したファイル: {len(media_files)}個")
    for i, file_info in enumerate(media_files):
        print(f"  {i+1}: {file_info['name']}")

    return media_files


def load_graphic_templates(template_path):
    templates = {}
    try:
        ttree = ET.parse(template_path)
        troot = ttree.getroot()
        for clip in troot.findall('.//sequence/media/video/track/clipitem'):
            key = clip.findtext('filter/effect/name') or clip.findtext('name') or ''
            key = key.strip()
            if key:
                templates[key] = clip
    except Exception:
        return {}
    return templates


def create_cut_xml_from_template(csv_file_path, template_xml_path, graphic_template_path=None):
    """Create cut XML using template XML structure and CSV timecodes"""
    
    # Extract template media metadata
    media_files = extract_media_files_from_xml(template_xml_path)
    
    if not media_files:
        print("エラー: テンプレートXMLからメディアファイルが見つかりません")
        return None
    
    # Parse template XML to get structure
    template_tree = ET.parse(template_xml_path)
    template_root = template_tree.getroot()
    
    # Create new XML with same structure
    root = ET.Element('xmeml', version='4')
    
    # Copy sequence structure from template
    template_sequence = template_root.find('sequence')
    sequence = ET.SubElement(root, 'sequence')
    
    # Copy all sequence attributes
    for attr_name, attr_value in template_sequence.attrib.items():
        sequence.set(attr_name, attr_value)
    
    # Generate new UUID
    uuid_elem = ET.SubElement(sequence, 'uuid')
    uuid_elem.text = str(uuid.uuid4())
    
    # Duration (will be updated later)
    duration = ET.SubElement(sequence, 'duration')
    duration.text = '15155'
    
    # Copy rate from template and derive timeline fps
    template_rate = template_sequence.find('rate')
    rate = ET.SubElement(sequence, 'rate')
    timeline_timebase_text = None
    timeline_ntsc_text = None
    if template_rate is not None:
        for child in template_rate:
            new_child = ET.SubElement(rate, child.tag)
            new_child.text = child.text
            if child.tag == 'timebase' and child.text:
                timeline_timebase_text = child.text.strip()
            if child.tag == 'ntsc' and child.text:
                timeline_ntsc_text = child.text.strip().upper()
    if not timeline_timebase_text:
        timeline_timebase_text = '30'
    if not timeline_ntsc_text:
        timeline_ntsc_text = 'TRUE'

    try:
        timeline_timebase_value = float(timeline_timebase_text)
    except Exception:
        timeline_timebase_value = 30.0

    timeline_fps = timeline_timebase_value
    if timeline_ntsc_text == 'TRUE':
        timeline_fps = timeline_timebase_value * 1000.0 / 1001.0
    if timeline_fps <= 0:
        timeline_fps = DEFAULT_TIMELINE_FPS

    # Seconds-based gap (~5 sec) scaled to timeline frame rate
    gap_size_frames = int(round(timeline_fps * 5.0))
    
    # Name
    name_elem = ET.SubElement(sequence, 'name')
    name_elem.text = f"{os.path.splitext(os.path.basename(csv_file_path))[0]}_cut"
    
    # Copy media structure from template
    template_media = template_sequence.find('media')
    media = ET.SubElement(sequence, 'media')
    
    template_video = template_media.find('video') if template_media is not None else None
    template_audio = template_media.find('audio') if template_media is not None else None
    
    def deep_copy(element):
        return ET.fromstring(ET.tostring(element)) if element is not None else None
    
    video = ET.SubElement(media, 'video')
    if template_video is not None:
        for child in template_video:
            if child.tag != 'track':
                copied_child = deep_copy(child)
                if copied_child is not None:
                    video.append(copied_child)
    
    audio = ET.SubElement(media, 'audio')
    if template_audio is not None:
        for child in template_audio:
            if child.tag != 'track':
                copied_child = deep_copy(child)
                if copied_child is not None:
                    audio.append(copied_child)
    
    # Read CSV into segments: normal blocks grouped by color, and gaps with telop text
    segments = []
    current_color = None
    current_block = None
    
    with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
    
        for row in reader:
            in_point = row.get('イン点', '').strip()
            out_point = row.get('アウト点', '').strip()
            text = row.get('文字起こし', '').strip()
            color = row.get('色選択', '').strip()
            is_gap = color.startswith('GAP_') if color else False
    
            # GAP 行
            if is_gap:
                if current_block:
                    segments.append(current_block)
                    current_block = None
                    current_color = None
                # Gap duration from in/out
                if not out_point:
                    continue
                start_frames = timecode_to_frames(in_point, fps=timeline_fps)
                end_frames = timecode_to_frames(out_point, fps=timeline_fps)
                if end_frames <= start_frames:
                    continue
                segments.append({
                    'type': 'gap',
                    'duration_frames': end_frames - start_frames,
                    'telop_text': text,
                    'telop_label': color.split('_', 1)[1] if '_' in color else color,
                })
                continue
    
            # 非GAP: 色とタイムコード必須
            if not in_point or not out_point or not color:
                continue
    
            # Convert timecodes to frames
            in_frames = timecode_to_frames(in_point, fps=timeline_fps)
            out_frames = timecode_to_frames(out_point, fps=timeline_fps)
    
            if in_frames >= out_frames:
                continue
    
            # If color changed, start new block
            if color != current_color:
                if current_block:
                    segments.append(current_block)
    
                current_color = color
                current_block = {
                    'type': 'block',
                    'color': color,
                    'start_frames': in_frames,
                    'end_frames': out_frames,
                    'rows': [row]
                }
            else:
                # Extend current block
                current_block['end_frames'] = out_frames
                current_block['rows'].append(row)
    
        # Add last block
        if current_block:
            segments.append(current_block)
    
    # Diagnostics
    blocks = [s for s in segments if s['type'] == 'block']
    gaps = [s for s in segments if s['type'] == 'gap']
    print(f"検出: ブロック {len(blocks)}個 / ギャップ {len(gaps)}個")
    
    # Helper: find max clipitem numeric suffix to avoid duplicate IDs
    import re
    id_re = re.compile(r"clipitem-(\d+)")
    max_clip_num = 0
    for ci in template_root.findall('.//clipitem'):
        cid = ci.get('id') or ''
        m = id_re.match(cid)
        if m:
            try:
                max_clip_num = max(max_clip_num, int(m.group(1)))
            except Exception:
                pass
    next_clip_num = max_clip_num + 1
    
    template_has_links = bool(template_root.findall('.//sequence/media/audio/track/clipitem/link') or template_root.findall('.//sequence/media/video/track/clipitem/link'))
    
    media_file_map = {}
    media_file_name_map = {}
    for mf in media_files:
        fid = mf.get('file_id')
        if fid and fid not in media_file_map:
            media_file_map[fid] = mf
        name = mf.get('name')
        if name and name not in media_file_name_map:
            media_file_name_map[name] = mf
    
    def build_track_sources(track_nodes, is_audio):
        sources = []
        for idx, t_track in enumerate(track_nodes):
            src = {'file_id': None, 'name': None, 'pathurl': None, 'element': None}
            if is_audio:
                src['source_channel'] = None

            clipitems = list(t_track.findall('clipitem'))
            segments = []
            cumulative = 0
            for ci in clipitems:
                seg = {}
                seg['clipitem'] = ci
                seg['clip_start_base'] = parse_int(ci.findtext('start'))
                seg['clip_end_base'] = parse_int(ci.findtext('end'))
                seg['clip_in_base'] = parse_int(ci.findtext('in'))
                seg['clip_out_base'] = parse_int(ci.findtext('out'))
                if seg['clip_in_base'] is not None and seg['clip_out_base'] is not None:
                    length = max(seg['clip_out_base'] - seg['clip_in_base'], 0)
                elif seg['clip_start_base'] is not None and seg['clip_end_base'] is not None:
                    length = max(seg['clip_end_base'] - seg['clip_start_base'], 0)
                else:
                    length = 0
                seg['segment_length'] = length
                seg['range_start'] = cumulative
                seg['range_end'] = cumulative + length
                cumulative += length

                name_elem = ci.find('name')
                if name_elem is not None and name_elem.text:
                    seg['name'] = name_elem.text.strip()

                masterclipid_elem = ci.find('masterclipid')
                if masterclipid_elem is not None and masterclipid_elem.text:
                    seg['masterclipid'] = masterclipid_elem.text.strip()

                file_elem = ci.find('file')
                resolved_file_elem = None
                if file_elem is not None:
                    fid = file_elem.get('id')
                    if fid:
                        seg['file_id'] = fid
                        resolved_file_elem = template_root.find(f".//media/file[@id='{fid}']") or file_elem
                    else:
                        resolved_file_elem = file_elem
                if resolved_file_elem is not None:
                    seg['element'] = resolved_file_elem
                    n = resolved_file_elem.find('name')
                    p = resolved_file_elem.find('pathurl')
                    if n is not None and n.text:
                        seg['name'] = seg.get('name') or n.text
                    if p is not None and p.text:
                        seg['pathurl'] = p.text
                    dur_elem = resolved_file_elem.find('duration')
                    if dur_elem is not None and (dur_elem.text or '').isdigit():
                        seg['source_duration'] = int(dur_elem.text)

                if is_audio:
                    st = ci.find('sourcetrack/trackindex')
                    if st is not None and (st.text or '').strip().isdigit():
                        seg['source_channel'] = int(st.text)

                seg_lookup = None
                if seg.get('file_id') and seg['file_id'] in media_file_map:
                    seg_lookup = media_file_map[seg['file_id']]
                elif seg.get('name') and seg['name'] in media_file_name_map:
                    seg_lookup = media_file_name_map[seg['name']]
                if seg_lookup:
                    for key in ('name', 'pathurl', 'element', 'source_duration', 'file_id', 'masterclipid', 'clip_in_base', 'clip_out_base'):
                        if not seg.get(key) and seg_lookup.get(key):
                            seg[key] = seg_lookup[key]

                segments.append(seg)

            if segments:
                src['segments'] = segments
                first_seg = segments[0]
                for key in ('file_id', 'name', 'pathurl', 'element', 'source_duration', 'masterclipid', 'clip_start_base', 'clip_end_base', 'clip_in_base', 'clip_out_base'):
                    if first_seg.get(key) is not None:
                        src[key] = first_seg[key]
                if is_audio and first_seg.get('source_channel') is not None:
                    src['source_channel'] = first_seg['source_channel']

            clipitem_name = None
            if clipitems:
                name_elem = clipitems[0].find('name')
                if name_elem is not None and name_elem.text:
                    clipitem_name = name_elem.text.strip()
            if not src.get('name') and clipitem_name:
                src['name'] = clipitem_name

            lookup = None
            if src.get('file_id') and src['file_id'] in media_file_map:
                lookup = media_file_map[src['file_id']]
            elif src.get('name') and src['name'] in media_file_name_map:
                lookup = media_file_name_map[src['name']]
            elif media_files:
                lookup = media_files[min(idx, len(media_files) - 1)]

            if lookup:
                for key in ('name', 'pathurl', 'element', 'source_duration', 'file_id', 'masterclipid', 'clip_start_base', 'clip_end_base', 'clip_in_base', 'clip_out_base'):
                    if not src.get(key) and lookup.get(key):
                        src[key] = lookup[key]

            if is_audio and src.get('source_channel') is None:
                src['source_channel'] = 1 if (idx % 2 == 0) else 2

            sources.append(src)
        return sources
 
    template_video_tracks = template_video.findall('track') if template_video is not None else []
    template_audio_tracks = template_audio.findall('track') if template_audio is not None else []
 
    video_track_sources = build_track_sources(template_video_tracks, is_audio=False)
    audio_track_sources = build_track_sources(template_audio_tracks, is_audio=True)

    def find_reference_start(sources):
        for src in sources:
            for seg in src.get('segments', []) or []:
                if seg.get('clip_start_base') is not None:
                    return seg['clip_start_base']
        return 0

    reference_start = find_reference_start(video_track_sources + audio_track_sources)

    for src in video_track_sources + audio_track_sources:
        src_segments = src.get('segments') or []
        if not src_segments:
            src['clip_start_offset'] = 0
            continue
        for seg in src_segments:
            seg['timeline_offset'] = (seg.get('clip_start_base') or 0) - reference_start
        src['clip_start_offset'] = src_segments[0].get('timeline_offset', 0)

    def select_segment_for_frames(srcmap, start_frame, end_frame):
        segment_list = srcmap.get('segments') or []
        for seg in segment_list:
            rs = seg.get('range_start')
            re = seg.get('range_end')
            if rs is None or re is None:
                continue
            if start_frame >= rs and end_frame <= re:
                return seg
        if segment_list:
            return segment_list[-1]
        return None
    gap_size = gap_size_frames
    block_clipitems = [[] for _ in range(len(blocks))]
    used_file_ids = set()
    max_timeline_end = 0

    # Rebuild video tracks using segments
    for track_idx, template_track in enumerate(template_video_tracks):
        template_clipitems = list(template_track.findall('clipitem'))
        template_has_clip = bool(template_clipitems)
        if not template_has_clip:
            copied_track = deep_copy(template_track)
            if copied_track is not None:
                video.append(copied_track)
            continue

        track = ET.SubElement(video, 'track')
        for attr_name, attr_value in template_track.attrib.items():
            track.set(attr_name, attr_value)

        srcmap = video_track_sources[track_idx] if track_idx < len(video_track_sources) else {}
        video_file_defaults = {
            'name': srcmap.get('name'),
            'pathurl': srcmap.get('pathurl'),
            'element': srcmap.get('element'),
            'file_id': srcmap.get('file_id'),
            'source_duration': srcmap.get('source_duration'),
            'masterclipid': srcmap.get('masterclipid') or f'masterclip-video-{track_idx + 1}',
            'clip_in_base': srcmap.get('clip_in_base', 0),
            'clip_out_base': srcmap.get('clip_out_base'),
        }
        default_template_clipitem = template_clipitems[0] if template_clipitems else None
        timeline_position = 0
        block_index = 1
        block_counter = -1

        for seg in segments:
            if seg['type'] == 'gap':
                timeline_position += seg['duration_frames']
                continue
            block_counter += 1
            block = seg
            start_frames = block['start_frames']
            end_frames = block['end_frames']
            duration_frames = end_frames - start_frames
            if duration_frames <= 0:
                continue

            timeline_position += gap_size

            segment_info = select_segment_for_frames(srcmap, start_frames, end_frames)
            if segment_info:
                relative_start = start_frames - (segment_info.get('range_start') or 0)
                if relative_start < 0:
                    relative_start = 0
                clip_in_base = segment_info.get('clip_in_base', video_file_defaults['clip_in_base'])
                clip_out_base_limit = segment_info.get('clip_out_base')
                file_id_to_use = segment_info.get('file_id') or video_file_defaults.get('file_id')
                file_element_to_use = segment_info.get('element') or video_file_defaults.get('element')
                masterclip_id_to_use = segment_info.get('masterclipid') or video_file_defaults['masterclipid']
                file_name_to_use = segment_info.get('name') or video_file_defaults.get('name') or f'Video Track {track_idx + 1}'
                pathurl_to_use = segment_info.get('pathurl') or video_file_defaults.get('pathurl')
                timeline_offset = segment_info.get('timeline_offset', srcmap.get('clip_start_offset', 0))
                template_source_clip = segment_info.get('clipitem') or default_template_clipitem
            else:
                relative_start = start_frames
                clip_in_base = video_file_defaults.get('clip_in_base', 0)
                clip_out_base_limit = video_file_defaults.get('clip_out_base')
                file_id_to_use = video_file_defaults.get('file_id')
                file_element_to_use = video_file_defaults.get('element')
                masterclip_id_to_use = video_file_defaults['masterclipid']
                file_name_to_use = video_file_defaults.get('name') or f'Video Track {track_idx + 1}'
                pathurl_to_use = video_file_defaults.get('pathurl')
                timeline_offset = srcmap.get('clip_start_offset', 0)
                template_source_clip = default_template_clipitem

            start_on_timeline = timeline_position + timeline_offset
            end_frame_on_timeline = start_on_timeline + duration_frames

            clipitem = deep_copy(template_source_clip) if template_source_clip is not None else ET.Element('clipitem')
            clipitem.set('id', f'clipitem-{next_clip_num}')
            track.append(clipitem)

            for existing_link in list(clipitem.findall('link')):
                clipitem.remove(existing_link)

            masterclipid = ensure(clipitem, 'masterclipid')
            masterclipid.text = masterclip_id_to_use

            clip_name = ensure(clipitem, 'name')
            clip_name.text = file_name_to_use

            ensure(clipitem, 'enabled').text = 'TRUE'

            clip_in_value = clip_in_base + relative_start
            clip_out_value = clip_in_value + duration_frames
            if clip_out_base_limit is not None and clip_out_value > clip_out_base_limit:
                clip_out_value = clip_out_base_limit

            ensure(clipitem, 'start').text = str(start_on_timeline)
            ensure(clipitem, 'end').text = str(end_frame_on_timeline)
            ensure(clipitem, 'in').text = str(clip_in_value)
            ensure(clipitem, 'out').text = str(clip_out_value)
            ensure(clipitem, 'pproTicksIn').text = str(frames_to_ppro_ticks(clip_in_value, fps=timeline_fps))
            ensure(clipitem, 'pproTicksOut').text = str(frames_to_ppro_ticks(clip_out_value, fps=timeline_fps))

            existing_files = clipitem.findall('file')
            if existing_files:
                file_elem = existing_files[0]
                for extra in existing_files[1:]:
                    clipitem.remove(extra)
            else:
                file_elem = ET.SubElement(clipitem, 'file')

            if file_id_to_use:
                file_elem.set('id', file_id_to_use)
                if file_id_to_use not in used_file_ids and file_element_to_use is not None:
                    file_elem.clear()
                    file_elem.set('id', file_id_to_use)
                    for child in file_element_to_use:
                        file_elem.append(deep_copy(child))
                    used_file_ids.add(file_id_to_use)
                else:
                    for child in list(file_elem):
                        file_elem.remove(child)
            else:
                if file_name_to_use:
                    ensure(file_elem, 'name').text = file_name_to_use
                if pathurl_to_use:
                    ensure(file_elem, 'pathurl').text = pathurl_to_use

            labels = ensure(clipitem, 'labels')
            label2 = ensure(labels, 'label2')
            premiere_label = csv_color_to_premiere_label(block['color'])
            label2.text = premiere_label

            if 0 <= block_counter < len(block_clipitems):
                block_clipitems[block_counter].append({
                    'clipitem': clipitem,
                    'clip_id': clipitem.get('id'),
                    'track_index': track_idx + 1,
                    'media_type': 'video'
                })
            timeline_position += duration_frames
            if end_frame_on_timeline > max_timeline_end:
                max_timeline_end = end_frame_on_timeline
            next_clip_num += 1
            block_index += 1

        for child in template_track:
            if child.tag != 'clipitem':
                track.append(deep_copy(child))

    # Rebuild audio tracks using segments
    for track_idx, template_track in enumerate(template_audio_tracks):
        template_clipitems = list(template_track.findall('clipitem'))
        template_has_clip = bool(template_clipitems)
        if not template_has_clip:
            copied_track = deep_copy(template_track)
            if copied_track is not None:
                audio.append(copied_track)
            continue

        track = ET.SubElement(audio, 'track')
        for attr_name, attr_value in template_track.attrib.items():
            track.set(attr_name, attr_value)

        srcmap = audio_track_sources[track_idx] if track_idx < len(audio_track_sources) else {}
        audio_file_defaults = {
            'name': srcmap.get('name'),
            'pathurl': srcmap.get('pathurl'),
            'element': srcmap.get('element'),
            'file_id': srcmap.get('file_id'),
            'source_duration': srcmap.get('source_duration'),
            'masterclipid': srcmap.get('masterclipid') or f'masterclip-{track_idx + 1}',
            'clip_in_base': srcmap.get('clip_in_base', 0),
            'clip_out_base': srcmap.get('clip_out_base'),
        }
        if not audio_file_defaults['name']:
            if audio_file_defaults.get('pathurl'):
                audio_file_defaults['name'] = os.path.splitext(os.path.basename(audio_file_defaults['pathurl']))[0]
            else:
                audio_file_defaults['name'] = f'Audio Track {track_idx + 1}'
        default_template_clipitem = template_clipitems[0] if template_clipitems else None
        timeline_position = 0
        block_index = 1
        block_counter = -1

        for seg in segments:
            if seg['type'] == 'gap':
                timeline_position += seg['duration_frames']
                continue
            block_counter += 1
            block = seg
            start_frames = block['start_frames']
            end_frames = block['end_frames']
            duration_frames = end_frames - start_frames
            if duration_frames <= 0:
                continue

            timeline_position += gap_size

            segment_info = select_segment_for_frames(srcmap, start_frames, end_frames)
            if segment_info:
                relative_start = start_frames - (segment_info.get('range_start') or 0)
                if relative_start < 0:
                    relative_start = 0
                clip_in_base = segment_info.get('clip_in_base', audio_file_defaults['clip_in_base'])
                clip_out_base_limit = segment_info.get('clip_out_base')
                file_id_to_use = segment_info.get('file_id') or audio_file_defaults.get('file_id')
                file_element_to_use = segment_info.get('element') or audio_file_defaults.get('element')
                masterclip_id_to_use = segment_info.get('masterclipid') or audio_file_defaults['masterclipid']
                file_name_to_use = segment_info.get('name') or audio_file_defaults['name']
                pathurl_to_use = segment_info.get('pathurl') or audio_file_defaults.get('pathurl')
                timeline_offset = segment_info.get('timeline_offset', srcmap.get('clip_start_offset', 0))
                template_source_clip = segment_info.get('clipitem') or default_template_clipitem
                source_channel = segment_info.get('source_channel', srcmap.get('source_channel', 1 if (track_idx % 2 == 0) else 2))
            else:
                relative_start = start_frames
                clip_in_base = audio_file_defaults.get('clip_in_base', 0)
                clip_out_base_limit = audio_file_defaults.get('clip_out_base')
                file_id_to_use = audio_file_defaults.get('file_id')
                file_element_to_use = audio_file_defaults.get('element')
                masterclip_id_to_use = audio_file_defaults['masterclipid']
                file_name_to_use = audio_file_defaults['name']
                pathurl_to_use = audio_file_defaults.get('pathurl')
                timeline_offset = srcmap.get('clip_start_offset', 0)
                template_source_clip = default_template_clipitem
                source_channel = srcmap.get('source_channel', 1 if (track_idx % 2 == 0) else 2)

            start_on_timeline = timeline_position + timeline_offset
            end_frame_on_timeline = start_on_timeline + duration_frames

            clipitem = deep_copy(template_source_clip) if template_source_clip is not None else ET.Element('clipitem', premiereChannelType='mono')
            clipitem.set('id', f'clipitem-{next_clip_num}')
            track.append(clipitem)

            for existing_link in list(clipitem.findall('link')):
                clipitem.remove(existing_link)

            masterclipid = ensure(clipitem, 'masterclipid')
            masterclipid.text = masterclip_id_to_use

            clip_name = ensure(clipitem, 'name')
            clip_name.text = file_name_to_use

            ensure(clipitem, 'enabled').text = 'TRUE'

            if template_source_clip is None:
                clip_duration = ensure(clipitem, 'duration')
                if audio_file_defaults.get('source_duration'):
                    clip_duration.text = str(audio_file_defaults['source_duration'])
                else:
                    clip_duration.text = str(duration_frames)

            clip_rate = ensure(clipitem, 'rate')
            clip_timebase = ensure(clip_rate, 'timebase')
            clip_timebase.text = timeline_timebase_text
            clip_ntsc = ensure(clip_rate, 'ntsc')
            clip_ntsc.text = timeline_ntsc_text

            clip_in_value = clip_in_base + relative_start
            clip_out_value = clip_in_value + duration_frames
            if clip_out_base_limit is not None and clip_out_value > clip_out_base_limit:
                clip_out_value = clip_out_base_limit

            ensure(clipitem, 'start').text = str(start_on_timeline)
            ensure(clipitem, 'end').text = str(end_frame_on_timeline)
            ensure(clipitem, 'in').text = str(clip_in_value)
            ensure(clipitem, 'out').text = str(clip_out_value)
            ensure(clipitem, 'pproTicksIn').text = str(frames_to_ppro_ticks(clip_in_value, fps=timeline_fps))
            ensure(clipitem, 'pproTicksOut').text = str(frames_to_ppro_ticks(clip_out_value, fps=timeline_fps))

            existing_files = clipitem.findall('file')
            if existing_files:
                file_elem = existing_files[0]
                for extra in existing_files[1:]:
                    clipitem.remove(extra)
            else:
                file_elem = ET.SubElement(clipitem, 'file')

            if file_id_to_use:
                file_elem.set('id', file_id_to_use)
                if file_id_to_use not in used_file_ids and file_element_to_use is not None:
                    file_elem.clear()
                    file_elem.set('id', file_id_to_use)
                    for child in file_element_to_use:
                        file_elem.append(deep_copy(child))
                    used_file_ids.add(file_id_to_use)
                else:
                    for child in list(file_elem):
                        file_elem.remove(child)
            else:
                if file_name_to_use:
                    ensure(file_elem, 'name').text = file_name_to_use
                if pathurl_to_use:
                    ensure(file_elem, 'pathurl').text = pathurl_to_use

            sourcetrack = clipitem.find('sourcetrack')
            if sourcetrack is None:
                sourcetrack = ET.SubElement(clipitem, 'sourcetrack')
            mediatype = sourcetrack.find('mediatype')
            if mediatype is None:
                mediatype = ET.SubElement(sourcetrack, 'mediatype')
            mediatype.text = 'audio'
            trackindex_elem = sourcetrack.find('trackindex')
            if trackindex_elem is None:
                trackindex_elem = ET.SubElement(sourcetrack, 'trackindex')
            trackindex_elem.text = str(source_channel)

            labels = ensure(clipitem, 'labels')
            label2 = ensure(labels, 'label2')
            premiere_label = csv_color_to_premiere_label(block['color'])
            label2.text = premiere_label

            if 0 <= block_counter < len(block_clipitems):
                block_clipitems[block_counter].append({
                    'clipitem': clipitem,
                    'clip_id': clipitem.get('id'),
                    'track_index': track_idx + 1,
                    'media_type': 'audio'
                })
            timeline_position += duration_frames
            if end_frame_on_timeline > max_timeline_end:
                max_timeline_end = end_frame_on_timeline
            next_clip_num += 1
            block_index += 1

        for child in template_track:
            if child.tag != 'clipitem':
                track.append(deep_copy(child))
    # Add linking information so paired clips stay associated in Premiere
    if template_has_links:
        for block_idx, items in enumerate(block_clipitems):
            if len(items) <= 1:
                continue
            for entry in items:
                clipitem = entry['clipitem']
                for link_elem in list(clipitem.findall('link')):
                    clipitem.remove(link_elem)
                for target in items:
                    link = ET.SubElement(clipitem, 'link')
                    ET.SubElement(link, 'linkclipref').text = target['clip_id']
                    ET.SubElement(link, 'mediatype').text = target['media_type']
                    ET.SubElement(link, 'trackindex').text = str(target['track_index'])
                    ET.SubElement(link, 'clipindex').text = str(block_idx + 1)
                    ET.SubElement(link, 'groupindex').text = '1'
    
    # Update sequence duration
    total_duration = max_timeline_end
    duration.text = str(total_duration)
    
    # Add telop clips on V1 from gaps, using a graphic template if available
    if gaps and graphic_template_path and os.path.exists(graphic_template_path):
        graphic_templates = load_graphic_templates(graphic_template_path)
        if graphic_templates:
            seq_media = sequence.find('media')
            vid = seq_media.find('video')
            if vid is None:
                vid = ET.SubElement(seq_media, 'video')
            vtrack = vid.find('track')
            if vtrack is None:
                vtrack = ET.SubElement(vid, 'track')
                ET.SubElement(vtrack, 'enabled').text = 'TRUE'
                ET.SubElement(vtrack, 'locked').text = 'FALSE'
    
            telop_start = 0
            for seg in segments:
                if seg['type'] == 'gap':
                    dur = seg['duration_frames']
                    telop_text = (seg.get('telop_text') or '').strip()
                    raw_label = seg.get('telop_label', '').strip()
                    lookup_label = raw_label
                    if raw_label:
                        upper = raw_label.upper()
                        if upper.startswith('NA'):
                            lookup_label = upper
                        elif raw_label.isdigit():
                            lookup_label = f"NA{raw_label}"
                    template_clip = graphic_templates.get(lookup_label) or next(iter(graphic_templates.values()), None)
                    if template_clip is None:
                        telop_start += dur
                        continue
                    clipitem = deep_copy(template_clip)
                    clipitem.set('id', f'vclipitem-{uuid.uuid4()}')
                    clipitem.find('start').text = str(telop_start)
                    clipitem.find('end').text = str(telop_start + dur)
                    clipitem.find('in').text = '0'
                    clipitem.find('out').text = str(dur)
                    ppin = clipitem.find('pproTicksIn')
                    if ppin is None:
                        ppin = ET.SubElement(clipitem, 'pproTicksIn')
                    ppin.text = str(frames_to_ppro_ticks(0, fps=timeline_fps))
                    ppout = clipitem.find('pproTicksOut')
                    if ppout is None:
                        ppout = ET.SubElement(clipitem, 'pproTicksOut')
                    ppout.text = str(frames_to_ppro_ticks(dur, fps=timeline_fps))
                    eff = clipitem.find('filter/effect')
                    if eff is not None:
                        name_elem = eff.find('name')
                        if name_elem is not None:
                            name_elem.text = telop_text or lookup_label or name_elem.text
                    clip_name_elem = clipitem.find('name')
                    if clip_name_elem is not None:
                        clip_name_elem.text = telop_text or lookup_label or clip_name_elem.text
                    vtrack.append(clipitem)
                    telop_start += dur
                else:
                    telop_start += gap_size + (seg['end_frames'] - seg['start_frames']) + gap_size
    
    return root


def prettify_xml(elem):
    """Return a pretty-printed XML string with DOCTYPE"""
    rough_string = ET.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    xml_string = reparsed.toprettyxml(indent="\t", encoding='UTF-8').decode('utf-8')
    
    # Add DOCTYPE declaration
    xml_lines = xml_string.split('\n')
    xml_lines.insert(1, '<!DOCTYPE xmeml>')
    
    return '\n'.join(xml_lines)


def select_files_gui():
    """GUI file selection interface (returns csv, template_xml, optional_graphic_xml)."""
    if not HAS_GUI:
        return None, None, None
    
    try:
        root = tk.Tk()
    except Exception:
        # Safety: if Tk cannot initialize here, fall back to CLI
        return None, None, None
    
    root.withdraw()  # Hide the main window
    
    try:
        # Select template XML file first
        template_xml_file = filedialog.askopenfilename(
            title="テンプレートXMLファイルを選択してください（例: 021-1.xml）",
            filetypes=[("XML files", "*.xml"), ("All files", "*.*")]
        )
        
        if not template_xml_file:
            try:
                messagebox.showinfo("キャンセル", "テンプレートXMLファイルが選択されませんでした")
            except Exception:
                pass
            return None, None, None
        
        # Select CSV file
        csv_file = filedialog.askopenfilename(
            title="CSVファイルを選択してください",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if not csv_file:
            try:
                messagebox.showinfo("キャンセル", "CSVファイルが選択されませんでした")
            except Exception:
                pass
            return None, None, None
        
        # Optional: graphic template for telop clips
        graphic_template = filedialog.askopenfilename(
            title="(任意) グラフィックテンプレートXMLがあれば選択してください（キャンセルでスキップ）",
            filetypes=[("XML files", "*.xml"), ("All files", "*.*")]
        ) or None
        
        return csv_file, template_xml_file, graphic_template
    finally:
        try:
            root.destroy()
        except Exception:
            pass


def prompt_for_files():
    """Prompt user for file paths interactively in the console."""
    print("\n対話モードでファイルパスを入力してください。")
    print("（ファイルをターミナルにドラッグ＆ドロップしても入力できます）")

    # strip("'\"") はシングルクォートとダブルクォートの両方を除去する
    csv_file = input("1. CSVファイルのパスを入力してください: ").strip().strip("'\"")
    if not os.path.exists(csv_file):
        print(f"エラー: CSVファイル '{csv_file}' が見つかりません。")
        return None, None, None

    template_xml_file = input("2. テンプレートXMLファイルのパスを入力してください: ").strip().strip("'\"")
    if not os.path.exists(template_xml_file):
        print(f"エラー: テンプレートXMLファイル '{template_xml_file}' が見つかりません。")
        return None, None, None

    # オプションのグラフィックテンプレートも聞く
    graphic_template_path = input("3. (オプション) グラフィックテンプレートXMLのパスを入力してください（不要な場合はEnter）: ").strip().strip("'\"")
    if graphic_template_path and not os.path.exists(graphic_template_path):
        print(f"警告: グラフィックテンプレート '{graphic_template_path}' が見つかりません。無視します。")
        graphic_template_path = None

    return csv_file, template_xml_file, graphic_template_path


def main():
    graphic_template = None
    # Check if command line arguments are provided
    if len(sys.argv) >= 3:
        # Command line mode
        csv_file = sys.argv[1]
        template_xml_file = sys.argv[2]
        graphic_template = None
        if len(sys.argv) >= 4:
            graphic_template = sys.argv[3]
        
        if not os.path.exists(csv_file):
            print(f"Error: CSV file '{csv_file}' not found")
            sys.exit(1)
        
        if not os.path.exists(template_xml_file):
            print(f"Error: Template XML file '{template_xml_file}' not found")
            sys.exit(1)
    else:
        # GUI mode
        if HAS_GUI:
            print("ファイル選択ダイアログを開きます...")
            csv_file, template_xml_file, graphic_template = select_files_gui()
            
            if not csv_file or not template_xml_file:
                sys.exit(0)  # User cancelled the dialog, which is not an error
            
            print(f"テンプレートXML: {template_xml_file}")
            print(f"CSVファイル: {csv_file}")
            if graphic_template:
                print(f"グラフィックテンプレート: {graphic_template}")
        else:
            print("Note: GUI mode not available (tkinter not installed).")
            print("Usage: python premiere/tools/autocut/csv_xml_cutter.py <csv_file> <template_xml_file> [graphic_template.xml]")
            print("\nEntering interactive mode...")
            csv_file, template_xml_file, graphic_template = prompt_for_files()
            if not csv_file or not template_xml_file:
                sys.exit(1)
    
    try:
        # Generate XML
        xml_root = create_cut_xml_from_template(csv_file, template_xml_file, graphic_template)
        
        if xml_root is None:
            sys.exit(1)
        
        # Output file
        output_file = f"{os.path.splitext(csv_file)[0]}_cut_from_{os.path.splitext(os.path.basename(template_xml_file))[0]}.xml"
        
        # Write XML with DOCTYPE
        xml_string = prettify_xml(xml_root)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(xml_string)
        
        success_msg = f"XML generated: {output_file}"
        print(f"\n{success_msg}")
        
        # Show success message in GUI mode
        if len(sys.argv) < 3 and HAS_GUI:
            messagebox.showinfo("完了", f"XMLファイルを生成しました:\n{output_file}")
    
    except Exception as e:
        error_msg = f"エラーが発生しました: {str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        
        # Show error message in GUI mode
        if len(sys.argv) < 3 and HAS_GUI:
            messagebox.showerror("エラー", error_msg)


if __name__ == "__main__":
    main()
