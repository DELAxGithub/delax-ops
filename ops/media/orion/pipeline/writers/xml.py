#!/usr/bin/env python3
"""FCP7 XML writer for DaVinci Resolve import.

Generates Final Cut Pro 7 compatible XML (version 4) for timeline import.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List
from xml.dom import minidom


def frames_to_timecode(frames: int, fps: float, drop_frame: bool = False) -> str:
    """Convert frames to FCP7 timecode format.

    Args:
        frames: Total frame count
        fps: Frames per second
        drop_frame: Use drop frame format (for NTSC)

    Returns:
        Timecode string (HH:MM:SS:FF)
    """
    fps_int = int(round(fps))

    frame_num = frames % fps_int
    total_seconds = frames // fps_int

    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    separator = ";" if drop_frame else ":"
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}{separator}{frame_num:02d}"


def write_fcp7_xml(
    output_path: Path,
    timeline_segments: List,  # List[TimelineSegment]
    audio_segments: List,  # List[AudioSegment]
    project_name: str,
    fps: float,
    audio_sample_rate: int = 24000,
    timebase: int = 30,
    audio_dir: Path = None
) -> bool:
    """Write FCP7 XML timeline compatible with DaVinci Resolve.

    Args:
        output_path: Output XML file path
        timeline_segments: Calculated timeline segments
        project_name: Project name for XML metadata
        fps: Frames per second
        audio_sample_rate: Audio sample rate (default: 24000 for Gemini TTS)
        timebase: Video timebase (default: 30)
        audio_dir: Directory containing audio files (for absolute paths)

    Returns:
        True if successful, False otherwise

    XML Structure (DaVinci Resolve compatible):
        <xmeml version="4">
          <sequence>
            <uuid>timeline_name</uuid>
            <duration>total_frames</duration>
            <name>timeline_name</name>
            <rate><timebase>30</timebase><ntsc>TRUE</ntsc></rate>
            <media>
              <video><format/></video>
              <audio>
                <track>
                  <clipitem id="clipitem-1">
                    <name>audio.mp3</name>
                    <enabled>TRUE</enabled>
                    <duration>frames</duration>
                    <rate><timebase>30</timebase><ntsc>TRUE</ntsc></rate>
                    <start>0</start>
                    <end>frames</end>
                    <in>0</in>
                    <out>frames</out>
                    <file id="file-1">
                      <name>audio.mp3</name>
                      <pathurl>file:///absolute/path/audio.mp3</pathurl>
                      <rate><timebase>24000</timebase><ntsc>FALSE</ntsc></rate>
                      <media>
                        <audio>
                          <channelcount>1</channelcount>
                          <samplecharacteristics>
                            <samplerate>24000</samplerate>
                            <samplesize>16</samplesize>
                          </samplecharacteristics>
                        </audio>
                      </media>
                    </file>
                    <sourcetrack>
                      <mediatype>audio</mediatype>
                      <trackindex>1</trackindex>
                    </sourcetrack>
                    <comments/>
                  </clipitem>
                </track>
              </audio>
            </media>
          </sequence>
        </xmeml>
    """
    try:
        # Root element - version 4 for DaVinci Resolve compatibility
        root = ET.Element("xmeml", version="4")

        # Sequence (no <project> wrapper)
        sequence = ET.SubElement(root, "sequence")

        timeline_name = f"{project_name}_timeline"
        ET.SubElement(sequence, "uuid").text = timeline_name

        # Calculate total duration
        total_duration = int(timeline_segments[-1].end_time_sec * fps) if timeline_segments else 0
        ET.SubElement(sequence, "duration").text = str(total_duration)
        ET.SubElement(sequence, "name").text = timeline_name

        # Rate settings
        rate = ET.SubElement(sequence, "rate")
        ET.SubElement(rate, "timebase").text = str(timebase)
        ET.SubElement(rate, "ntsc").text = "TRUE"

        # Media
        media = ET.SubElement(sequence, "media")

        # Video track (empty but required)
        video = ET.SubElement(media, "video")
        ET.SubElement(video, "format")

        # Audio track
        audio_media = ET.SubElement(media, "audio")
        audio_track = ET.SubElement(audio_media, "track")

        # Create index map for audio segments (for actual durations/sample rates from ffprobe)
        audio_seg_map = {aseg.index: aseg for aseg in audio_segments}

        # Add clips
        for seg in timeline_segments:
            clipitem = ET.SubElement(audio_track, "clipitem", id=f"clipitem-{seg.index}")

            # Use audio_filename directly (already has .mp3 extension)
            clip_name = seg.audio_filename

            ET.SubElement(clipitem, "name").text = clip_name
            ET.SubElement(clipitem, "enabled").text = "TRUE"

            # Duration (in frames) - this is the segment duration on timeline
            start_frame = int(seg.start_time_sec * fps)
            end_frame = int(seg.end_time_sec * fps)
            duration_frames = end_frame - start_frame

            ET.SubElement(clipitem, "duration").text = str(duration_frames)

            # Clip rate
            clip_rate = ET.SubElement(clipitem, "rate")
            ET.SubElement(clip_rate, "timebase").text = str(timebase)
            ET.SubElement(clip_rate, "ntsc").text = "TRUE"

            ET.SubElement(clipitem, "start").text = str(start_frame)
            ET.SubElement(clipitem, "end").text = str(end_frame)

            # Audio file trim points (in AUDIO SAMPLES, not frames)
            # Use ACTUAL audio file duration and sample rate from ffprobe (not assumptions)
            audio_seg = audio_seg_map.get(seg.index)
            if audio_seg:
                actual_duration_sec = audio_seg.duration_sec
                actual_sample_rate = audio_seg.sample_rate
            else:
                # Fallback to timeline segment duration and default sample rate
                actual_duration_sec = getattr(seg, "audio_duration_sec", seg.end_time_sec - seg.start_time_sec)
                actual_sample_rate = audio_sample_rate

            in_samples = 0
            out_samples = int(round(actual_duration_sec * actual_sample_rate))

            ET.SubElement(clipitem, "in").text = str(in_samples)
            ET.SubElement(clipitem, "out").text = str(out_samples)

            # File reference with absolute path
            file_elem = ET.SubElement(clipitem, "file", id=f"file-{seg.index}")
            ET.SubElement(file_elem, "name").text = clip_name

            # Absolute file path (use audio index for correct file)
            if audio_dir:
                abs_path = (audio_dir / clip_name).resolve()
                ET.SubElement(file_elem, "pathurl").text = f"file://{abs_path}"
            else:
                ET.SubElement(file_elem, "pathurl").text = f"file:///audio/{clip_name}"

            # File rate (ACTUAL audio sample rate from ffprobe, not hardcoded assumption)
            file_rate = ET.SubElement(file_elem, "rate")
            ET.SubElement(file_rate, "timebase").text = str(actual_sample_rate)
            ET.SubElement(file_rate, "ntsc").text = "FALSE"

            # Media properties (ACTUAL sample rate from ffprobe)
            file_media = ET.SubElement(file_elem, "media")
            audio_elem = ET.SubElement(file_media, "audio")
            ET.SubElement(audio_elem, "channelcount").text = "1"  # Mono

            sample_chars = ET.SubElement(audio_elem, "samplecharacteristics")
            ET.SubElement(sample_chars, "samplerate").text = str(actual_sample_rate)
            ET.SubElement(sample_chars, "samplesize").text = "16"

            # Source track
            sourcetrack = ET.SubElement(clipitem, "sourcetrack")
            ET.SubElement(sourcetrack, "mediatype").text = "audio"
            ET.SubElement(sourcetrack, "trackindex").text = "1"

            # Comments (empty but present)
            ET.SubElement(clipitem, "comments")

        # Pretty print XML
        xml_string = ET.tostring(root, encoding="unicode")
        dom = minidom.parseString(xml_string)
        pretty_xml = dom.toprettyxml(indent="  ")

        # Write to file
        with output_path.open("w", encoding="utf-8") as f:
            f.write(pretty_xml)

        return True

    except Exception as e:
        print(f"❌ Failed to write FCP7 XML: {e}")
        return False


if __name__ == "__main__":
    print("FCP7 XML Writer Test")
    print("=" * 60)
    print("FCP7 XML writer implementation complete")
    print("Generates timeline XML for DaVinci Resolve import")
