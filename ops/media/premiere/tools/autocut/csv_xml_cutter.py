#!/usr/bin/env python3
"""
CSV + XML Timeline Cutter
Takes existing Premiere XML and cuts it based on CSV timecodes
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


TIMELINE_FPS = 30000 / 1001  # Premiere NTSC timeline fps (~29.97)


def timecode_to_frames(timecode, fps=TIMELINE_FPS):
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


def frames_to_ppro_ticks(frames, fps=TIMELINE_FPS):
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


def extract_audio_files_from_xml(xml_file_path):
    """Extract audio file information from existing XML.
    Returns a list of dicts with keys: name, pathurl, element, source_duration, file_id, masterclipid.
    """
    tree = ET.parse(xml_file_path)
    root = tree.getroot()

    audio_files = []
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
                audio_files.append(file_info)

    print(f"XMLから抽出したファイル: {len(audio_files)}個")
    for i, file_info in enumerate(audio_files):
        print(f"  {i+1}: {file_info['name']}")

    return audio_files


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
    
    # Extract audio files from template XML
    audio_files = extract_audio_files_from_xml(template_xml_path)
    
    if not audio_files:
        print("エラー: テンプレートXMLからオーディオファイルが見つかりません")
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
    
    # Copy rate from template
    template_rate = template_sequence.find('rate')
    if template_rate is not None:
        rate = ET.SubElement(sequence, 'rate')
        for child in template_rate:
            new_child = ET.SubElement(rate, child.tag)
            new_child.text = child.text
    
    # Name
    name_elem = ET.SubElement(sequence, 'name')
    name_elem.text = f"{os.path.splitext(os.path.basename(csv_file_path))[0]}_cut"
    
    # Copy media structure from template
    template_media = template_sequence.find('media')
    media = ET.SubElement(sequence, 'media')
    
    # Copy video section completely
    template_video = template_media.find('video')
    if template_video is not None:
        video = ET.SubElement(media, 'video')
        # Copy all video content (deep copy semantics via serialization)
        for child in template_video:
            video.append(ET.fromstring(ET.tostring(child)))
    
    # Copy audio structure but replace clipitems
    template_audio = template_media.find('audio')
    audio = ET.SubElement(media, 'audio')
    
    # Copy audio format and outputs
    for child in template_audio:
        if child.tag != 'track':
            audio.append(child)
    
    # Read CSV into segments: normal blocks grouped by color, and gaps with telop text
    segments = []
    current_color = None
    current_block = None
    
    with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        
        for row in reader:
            speaker = row.get('Speaker Name', '').strip()
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
                start_frames = timecode_to_frames(in_point)
                end_frames = timecode_to_frames(out_point)
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
            in_frames = timecode_to_frames(in_point)
            out_frames = timecode_to_frames(out_point)
            
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
    blocks = [s for s in segments if s['type']=='block']
    gaps = [s for s in segments if s['type']=='gap']
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

    template_has_links = bool(template_root.findall('.//sequence/media/audio/track/clipitem/link'))

    audio_file_map = {}
    audio_file_name_map = {}
    for af in audio_files:
        fid = af.get('file_id')
        if fid and fid not in audio_file_map:
            audio_file_map[fid] = af
        name = af.get('name')
        if name and name not in audio_file_name_map:
            audio_file_name_map[name] = af

    # Build per-track source mapping from template (file id/name + source channel)
    track_sources = []
    for t_idx, t_track in enumerate(template_root.findall('.//sequence/media/audio/track')):
        # Find first clipitem with a file reference in this template track
        src = {
            'file_id': None,
            'name': None,
            'pathurl': None,
            'element': None,
            'source_channel': None,
        }
        ci = t_track.find('clipitem')
        if ci is not None:
            clipitem_name = None
            name_elem = ci.find('name')
            if name_elem is not None and name_elem.text:
                clipitem_name = name_elem.text.strip()
            masterclipid_elem = ci.find('masterclipid')
            if masterclipid_elem is not None and masterclipid_elem.text:
                src['masterclipid'] = masterclipid_elem.text.strip()
            file_elem = ci.find('file')
            if file_elem is not None:
                fid = file_elem.get('id')
                if fid:
                    src['file_id'] = fid
                    full = template_root.find(f".//media/file[@id='{fid}']")
                    if full is None:
                        full = file_elem
                    src['element'] = full
                    n = full.find('name')
                    p = full.find('pathurl')
                    if n is not None and n.text:
                        src['name'] = n.text
                    if p is not None and p.text:
                        src['pathurl'] = p.text
                    dur_elem = full.find('duration')
                    if dur_elem is not None and (dur_elem.text or '').isdigit():
                        src['source_duration'] = int(dur_elem.text)
            st = ci.find('sourcetrack/trackindex')
            if st is not None and (st.text or '').strip().isdigit():
                src['source_channel'] = int(st.text)
            if src['name'] is None and clipitem_name:
                src['name'] = clipitem_name
        # Heuristic fallback for missing mapping
        if src['source_channel'] is None:
            src['source_channel'] = 1 if (t_idx % 2 == 0) else 2
        # If file info is missing, try to map from extracted audio_files by index roll-over
        if src['file_id'] is None and audio_files:
            af = audio_files[min(t_idx, len(audio_files)-1)]
            src['file_id'] = af.get('file_id')
            src['element'] = af.get('element')
            src['name'] = af.get('name')
            src['pathurl'] = af.get('pathurl')
            if af.get('source_duration'):
                src['source_duration'] = af['source_duration']
            if af.get('masterclipid'):
                src['masterclipid'] = af['masterclipid']

        lookup = None
        if src.get('file_id') and src['file_id'] in audio_file_map:
            lookup = audio_file_map[src['file_id']]
        elif src.get('name') and src['name'] in audio_file_name_map:
            lookup = audio_file_name_map[src['name']]
        if lookup:
            if not src.get('name') and lookup.get('name'):
                src['name'] = lookup['name']
            if not src.get('pathurl') and lookup.get('pathurl'):
                src['pathurl'] = lookup['pathurl']
            element = lookup.get('element')
            if element is not None:
                existing = src.get('element')
                if existing is None or len(list(existing)) == 0:
                    src['element'] = element
            if not src.get('source_duration') and lookup.get('source_duration'):
                src['source_duration'] = lookup['source_duration']
            if not src.get('masterclipid') and lookup.get('masterclipid'):
                src['masterclipid'] = lookup['masterclipid']
        track_sources.append(src)

    # Create audio tracks based on template
    template_tracks = template_audio.findall('track')
    gap_size = 149  # Like original between non-gap blocks
    used_file_ids = set()
    block_clipitems = [[] for _ in range(len(blocks))]
    
    max_timeline_end = 0

    for track_idx, template_track in enumerate(template_tracks):
        template_has_clip = template_track.find('clipitem') is not None
        if not template_has_clip:
            # Copy the track structure as-is (keeps empty tracks untouched)
            audio.append(ET.fromstring(ET.tostring(template_track)))
            continue

        # Track container
        track = ET.SubElement(audio, 'track')
        for attr_name, attr_value in template_track.attrib.items():
            track.set(attr_name, attr_value)

        # Create clipitems for this track
        timeline_position = 0
        # Use per-track source mapping to match template channel layout
        srcmap = track_sources[track_idx] if track_idx < len(track_sources) else {}
        audio_file = {
            'name': srcmap.get('name'),
            'pathurl': srcmap.get('pathurl'),
            'element': srcmap.get('element'),
            'file_id': srcmap.get('file_id'),
            'source_duration': srcmap.get('source_duration'),
            'masterclipid': srcmap.get('masterclipid'),
        }
        if not audio_file.get('name'):
            if audio_file.get('pathurl'):
                audio_file['name'] = os.path.splitext(os.path.basename(audio_file['pathurl']))[0]
            else:
                audio_file['name'] = f'Audio Track {track_idx + 1}'
        # IDs to reuse from template (avoid collisions with video section)
        template_file_id = audio_file.get('file_id')
        template_masterclip_id = audio_file.get('masterclipid') or f'masterclip-{track_idx + 2}'
        template_clipitem = template_track.find('clipitem')
        template_file_element = audio_file.get('element')
        # For logging: per-track block counter
        block_index = 1
        block_counter = -1

        for seg in segments:
            if seg['type'] == 'gap':
                # Only advance timeline by gap; no audio clip
                timeline_position += seg['duration_frames']
                continue
            block = seg
            start_frames = block['start_frames']
            end_frames = block['end_frames']
            duration_frames = end_frames - start_frames
            block_counter += 1

            # Add pre-gap before placing the block
            timeline_position += gap_size

            # Create clipitem
            if template_clipitem is not None:
                clipitem = ET.fromstring(ET.tostring(template_clipitem))
            else:
                clipitem = ET.Element('clipitem', premiereChannelType='mono')
            clipitem.set('id', f'clipitem-{next_clip_num}')
            track.append(clipitem)

            # Remove existing link nodes; new ones get added later
            for existing_link in list(clipitem.findall('link')):
                clipitem.remove(existing_link)

            # Master clip ID
            def ensure(parent, tag):
                child = parent.find(tag)
                if child is None:
                    child = ET.SubElement(parent, tag)
                return child

            masterclipid = ensure(clipitem, 'masterclipid')
            masterclipid.text = template_masterclip_id

            # Name
            clip_name = ensure(clipitem, 'name')
            clip_name.text = audio_file.get('name') or f'Audio Track {track_idx + 1}'

            # Enabled
            ensure(clipitem, 'enabled').text = 'TRUE'

            # Duration (total source file duration)
            if template_clipitem is None:
                clip_duration = ensure(clipitem, 'duration')
                if audio_file.get('source_duration'):
                    clip_duration.text = str(audio_file['source_duration'])
                else:
                    clip_duration.text = str(duration_frames)

            # Rate
            clip_rate = ensure(clipitem, 'rate')
            clip_timebase = ensure(clip_rate, 'timebase')
            clip_timebase.text = '30'
            clip_ntsc = ensure(clip_rate, 'ntsc')
            clip_ntsc.text = 'TRUE'

            # Start and end in timeline
            ensure(clipitem, 'start').text = str(timeline_position)
            end_frame_on_timeline = timeline_position + duration_frames
            ensure(clipitem, 'end').text = str(end_frame_on_timeline)

            # In and out of source media
            ensure(clipitem, 'in').text = str(start_frames)
            ensure(clipitem, 'out').text = str(end_frames)

            # Premiere Pro ticks
            ensure(clipitem, 'pproTicksIn').text = str(frames_to_ppro_ticks(start_frames))
            ensure(clipitem, 'pproTicksOut').text = str(frames_to_ppro_ticks(end_frames))
            
            # File reference
            existing_files = clipitem.findall('file')
            if existing_files:
                # Keep only the first file element from the template copy
                file_elem = existing_files[0]
                for extra in existing_files[1:]:
                    clipitem.remove(extra)
            else:
                file_elem = ET.SubElement(clipitem, 'file')

            if template_file_id:
                file_elem.set('id', template_file_id)
            else:
                file_elem.set('id', f'file-{track_idx + 100}')

            if template_file_id:
                if template_file_id not in used_file_ids and template_file_element is not None:
                    # Fresh definition: replace with template metadata
                    file_elem.clear()
                    file_elem.set('id', template_file_id)
                    for child in template_file_element:
                        file_elem.append(ET.fromstring(ET.tostring(child)))
                    used_file_ids.add(template_file_id)
                else:
                    # Subsequent references should not carry embedded metadata
                    to_remove = list(file_elem)
                    for child in to_remove:
                        file_elem.remove(child)
            else:
                if audio_file.get('name'):
                    ET.SubElement(file_elem, 'name').text = audio_file['name']
                if audio_file.get('pathurl'):
                    ET.SubElement(file_elem, 'pathurl').text = audio_file['pathurl']

            # Source track channel mapping (L/R)
            st = ET.SubElement(clipitem, 'sourcetrack')
            ET.SubElement(st, 'mediatype').text = 'audio'
            ET.SubElement(st, 'trackindex').text = str(srcmap.get('source_channel', 1))
            
            # Labels - CSVの色選択を反映
            labels = ensure(clipitem, 'labels')
            label2 = ensure(labels, 'label2')
            premiere_label = csv_color_to_premiere_label(block['color'])
            label2.text = premiere_label

            print(f"A{track_idx + 1}トラック: ブロック{block_index} ({timeline_position} - {timeline_position + duration_frames}) - {audio_file['name']} [ラベル: {premiere_label}]")

            if 0 <= block_counter < len(block_clipitems):
                block_clipitems[block_counter].append({
                    'clipitem': clipitem,
                    'clip_id': clipitem.get('id'),
                    'track_index': track_idx + 1
                })

            # Update timeline position with block duration and post-gap
            timeline_position += duration_frames + gap_size
            if end_frame_on_timeline > max_timeline_end:
                max_timeline_end = end_frame_on_timeline
            next_clip_num += 1
            block_index += 1
        
        # Copy non-clipitem children from template (pan, outputchannelindex etc.)
        for child in template_track:
            if child.tag != 'clipitem':
                track.append(ET.fromstring(ET.tostring(child)))

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
                    ET.SubElement(link, 'mediatype').text = 'audio'
                    ET.SubElement(link, 'trackindex').text = str(target['track_index'])
                    ET.SubElement(link, 'clipindex').text = str(block_idx + 1)

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
                    clipitem = ET.fromstring(ET.tostring(template_clip))
                    clipitem.set('id', f'vclipitem-{uuid.uuid4()}')
                    clipitem.find('start').text = str(telop_start)
                    clipitem.find('end').text = str(telop_start + dur)
                    clipitem.find('in').text = '0'
                    clipitem.find('out').text = str(dur)
                    ppin = clipitem.find('pproTicksIn')
                    if ppin is None:
                        ppin = ET.SubElement(clipitem, 'pproTicksIn')
                    ppin.text = str(frames_to_ppro_ticks(0))
                    ppout = clipitem.find('pproTicksOut')
                    if ppout is None:
                        ppout = ET.SubElement(clipitem, 'pproTicksOut')
                    ppout.text = str(frames_to_ppro_ticks(dur))
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
