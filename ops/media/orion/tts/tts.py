#!/usr/bin/env python3
"""TTS (Text-to-Speech) generation engine.

Handles audio synthesis using existing audio files or Gemini TTS.
Provides a mode to use pre-generated audio files to save API quota.
"""
from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

try:
    from google.cloud import texttospeech
    GOOGLE_TTS_AVAILABLE = True
except ImportError:
    GOOGLE_TTS_AVAILABLE = False

import sys
import os
import base64
import logging

logger = logging.getLogger(__name__)

ORION_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ORION_ROOT))


@dataclass
class AudioSegment:
    """Represents an audio segment with metadata."""

    index: int
    text: str
    audio_path: Path
    duration_sec: float
    sample_rate: int
    filename: str

    @classmethod
    def from_existing_file(
        cls,
        index: int,
        text: str,
        audio_path: Path
    ) -> AudioSegment:
        """Create AudioSegment from existing audio file.

        Args:
            index: Segment index
            text: Text content
            audio_path: Path to existing audio file

        Returns:
            AudioSegment with probed metadata
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        duration, sample_rate = probe_audio_metadata(audio_path)

        return cls(
            index=index,
            text=text,
            audio_path=audio_path,
            duration_sec=duration,
            sample_rate=sample_rate,
            filename=audio_path.name
        )


def probe_audio_metadata(audio_path: Path) -> tuple[float, int]:
    """Probe audio file metadata using ffprobe.

    Args:
        audio_path: Path to audio file

    Returns:
        (duration_seconds, sample_rate)

    Raises:
        RuntimeError: If ffprobe fails
    """
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "a:0",
        "-show_entries", "stream=sample_rate:format=duration",
        "-of", "json",
        str(audio_path),
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffprobe failed for {audio_path}: {e}")

    try:
        data = json.loads(result.stdout)
        duration = float(data["format"]["duration"])
        sample_rate = int(data["streams"][0]["sample_rate"])
    except (KeyError, ValueError, IndexError, TypeError) as exc:
        raise RuntimeError(
            f"Failed to parse ffprobe output for {audio_path}"
        ) from exc

    return duration, sample_rate


class TTSEngine:
    """TTS generation engine with mode switching."""

    def __init__(
        self,
        use_existing: bool = True,
        existing_audio_dir: Optional[Path] = None,
        request_delay_sec: float = 5.0
    ):
        """Initialize TTS engine.

        Args:
            use_existing: If True, use existing audio files
            existing_audio_dir: Directory with pre-generated audio files
            request_delay_sec: Delay between TTS requests to avoid quota limits
        """
        self.use_existing = use_existing
        self.existing_audio_dir = existing_audio_dir
        self.request_delay_sec = request_delay_sec

        self._gemini_client = None
        self._google_tts_client = None

        # Initialize APIs if not using existing files
        if not self.use_existing:
            if GEMINI_AVAILABLE:
                # Try both GEMINI_API_KEY and GOOGLE_API_KEY
                api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
                if api_key:
                    self._gemini_client = genai.Client(api_key=api_key)
                    print(f"  ✅ Gemini API configured")
                else:
                    print(f"  ⚠️  GEMINI_API_KEY/GOOGLE_API_KEY not found")

            if GOOGLE_TTS_AVAILABLE:
                try:
                    self._google_tts_client = texttospeech.TextToSpeechClient()
                    print(f"  ✅ Google Cloud TTS configured (fallback)")
                except Exception as e:
                    print(f"  ⚠️  Google Cloud TTS unavailable: {e}")

    def generate_segments(
        self,
        segments: List,  # List[NarrationSegment]
        output_dir: Path,
        project: str
    ) -> List[AudioSegment]:
        """Generate audio for all segments.

        Args:
            segments: List of NarrationSegment objects
            output_dir: Output directory for audio files
            project: Project name (e.g., "OrionEp11")

        Returns:
            List of AudioSegment objects with metadata
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        audio_segments: List[AudioSegment] = []

        for segment in segments:
            filename = f"{project}_{segment.index:03d}.mp3"
            output_path = output_dir / filename

            if self.use_existing and self.existing_audio_dir:
                # Use existing audio file
                existing_path = self.existing_audio_dir / filename

                if existing_path.exists():
                    try:
                        audio_seg = AudioSegment.from_existing_file(
                            index=segment.index,
                            text=segment.text,
                            audio_path=existing_path
                        )
                        audio_segments.append(audio_seg)
                        print(
                            f"  [{segment.index:03d}] ✅ Using existing: "
                            f"{filename} ({audio_seg.duration_sec:.2f}s)"
                        )
                        continue
                    except Exception as e:
                        print(
                            f"  [{segment.index:03d}] ⚠️  Failed to use existing: {e}"
                        )

            # Generate new audio with Gemini TTS
            try:
                audio_seg = self._generate_gemini_tts(
                    segment=segment,
                    output_path=output_path,
                    project=project
                )
                audio_segments.append(audio_seg)
                print(
                    f"  [{segment.index:03d}] ✅ Generated: "
                    f"{filename} ({audio_seg.duration_sec:.2f}s)"
                )

                # Rate limiting
                if segment.index < len(segments):
                    time.sleep(self.request_delay_sec)

            except Exception as e:
                print(
                    f"  [{segment.index:03d}] ❌ Failed: {e}"
                )
                # Continue with other segments even if one fails

        return audio_segments

    def _generate_gemini_tts(
        self,
        segment,  # NarrationSegment
        output_path: Path,
        project: str
    ) -> AudioSegment:
        """Generate audio using Gemini TTS API with Google TTS fallback.

        Args:
            segment: NarrationSegment with text to synthesize
            output_path: Output MP3 file path
            project: Project name

        Returns:
            AudioSegment with metadata

        Raises:
            RuntimeError: If all TTS methods fail
        """
        # Try Gemini TTS first
        if self._gemini_client:
            try:
                success = self._try_gemini_tts(segment.text, output_path)
                if success:
                    duration_sec, sample_rate = probe_audio_metadata(output_path)
                    return AudioSegment(
                        index=segment.index,
                        text=segment.text,
                        audio_path=output_path,
                        duration_sec=duration_sec,
                        sample_rate=sample_rate,
                        filename=output_path.name
                    )
            except Exception as e:
                logger.warning(f"Gemini TTS failed for segment {segment.index}: {e}")
                print(f"    ⚠️  Gemini TTS failed, falling back to Google TTS")

        # Fallback to Google Cloud TTS
        if self._google_tts_client:
            try:
                success = self._try_google_tts(segment.text, output_path)
                if success:
                    duration_sec, sample_rate = probe_audio_metadata(output_path)
                    return AudioSegment(
                        index=segment.index,
                        text=segment.text,
                        audio_path=output_path,
                        duration_sec=duration_sec,
                        sample_rate=sample_rate,
                        filename=output_path.name
                    )
            except Exception as e:
                logger.warning(f"Google TTS failed for segment {segment.index}: {e}")
                raise RuntimeError(f"All TTS methods failed: {e}")

        raise RuntimeError("No TTS clients available")

    def _try_gemini_tts(self, text: str, output_path: Path) -> bool:
        """Try to generate audio with Gemini TTS.

        Args:
            text: Text to synthesize
            output_path: Output audio file path

        Returns:
            True if successful, False otherwise
        """
        tts_model = "gemini-2.5-flash-preview-tts"
        voice_name = "Aoede"  # Default Japanese voice

        max_attempts = 5
        for attempt in range(1, max_attempts + 1):
            try:
                response = self._gemini_client.models.generate_content(
                    model=tts_model,
                    contents=text,
                    config={
                        "response_modalities": ["AUDIO"],
                        "speech_config": {
                            "voice_config": {
                                "prebuilt_voice_config": {"voice_name": voice_name}
                            }
                        },
                    },
                )

                # Extract audio data
                if not response or not response.candidates:
                    logger.warning(f"Gemini TTS returned no candidates (attempt {attempt}/{max_attempts})")
                    print(f"    ⚠️  Gemini TTS returned no candidates (attempt {attempt}/{max_attempts})")
                    if attempt < max_attempts:
                        time.sleep(2.0)
                        continue
                    return False

                parts = response.candidates[0].content.parts if response.candidates[0].content else []
                if not parts:
                    logger.warning(f"Gemini TTS returned no audio parts (attempt {attempt}/{max_attempts})")
                    print(f"    ⚠️  Gemini TTS returned no audio parts (attempt {attempt}/{max_attempts})")
                    if attempt < max_attempts:
                        time.sleep(2.0)
                        continue
                    return False

                inline_data = getattr(parts[0], "inline_data", None)
                raw_data = getattr(inline_data, "data", b"") if inline_data else b""
                pcm_bytes = base64.b64decode(raw_data) if isinstance(raw_data, str) else raw_data

                if not pcm_bytes:
                    logger.warning("Gemini TTS returned empty audio payload")
                    return False

                # Convert PCM to MP3
                self._save_pcm_as_mp3(pcm_bytes, output_path)
                return True

            except Exception as e:
                error_msg = str(e)
                # Check for quota/rate limit errors
                if "RESOURCE_EXHAUSTED" in error_msg or "429" in error_msg or "quota" in error_msg.lower():
                    retry_delay = min(5.0 * attempt, 15.0)
                    logger.info(f"Gemini TTS quota exceeded; retrying in {retry_delay}s (attempt {attempt}/{max_attempts})")
                    time.sleep(retry_delay)
                    continue
                else:
                    logger.warning(f"Gemini TTS request failed: {e}")
                    return False

        logger.warning(f"Gemini TTS failed after {max_attempts} attempts")
        return False

    def _try_google_tts(self, text: str, output_path: Path) -> bool:
        """Try to generate audio with Google Cloud TTS.

        Args:
            text: Text to synthesize
            output_path: Output audio file path

        Returns:
            True if successful, False otherwise
        """
        synthesis_input = texttospeech.SynthesisInput(text=text)

        voice = texttospeech.VoiceSelectionParams(
            language_code="ja-JP",
            name="ja-JP-Neural2-B"  # High-quality Japanese neural voice
        )

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=1.0,
            pitch=0.0
        )

        response = self._google_tts_client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )

        # Save audio content
        with output_path.open("wb") as f:
            f.write(response.audio_content)

        return True

    def _save_pcm_as_mp3(self, pcm_bytes: bytes, output_path: Path) -> None:
        """Convert PCM audio to MP3 using ffmpeg.

        Args:
            pcm_bytes: Raw PCM audio data
            output_path: Output MP3 file path
        """
        # Gemini TTS outputs 24kHz 16-bit mono PCM
        cmd = [
            "ffmpeg",
            "-f", "s16le",
            "-ar", "24000",
            "-ac", "1",
            "-i", "pipe:0",
            "-y",
            str(output_path)
        ]

        result = subprocess.run(
            cmd,
            input=pcm_bytes,
            capture_output=True
        )

        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg conversion failed: {result.stderr.decode()}")

    def validate_audio_completeness(
        self,
        segments: List,  # List[NarrationSegment]
        audio_dir: Path,
        project: str
    ) -> tuple[bool, List[str]]:
        """Validate that all segments have audio files.

        Args:
            segments: List of NarrationSegment objects
            audio_dir: Directory containing audio files
            project: Project name

        Returns:
            (all_complete, list_of_missing_filenames)
        """
        missing: List[str] = []

        if not audio_dir.exists():
            return False, [f"Audio directory not found: {audio_dir}"]

        for segment in segments:
            filename = f"{project}_{segment.index:03d}.mp3"
            audio_path = audio_dir / filename

            if not audio_path.exists():
                missing.append(filename)

        return len(missing) == 0, missing


if __name__ == "__main__":
    # Simple test
    print("Testing TTS engine...")

    # Create dummy audio file for testing
    test_dir = Path("test_audio")
    test_dir.mkdir(exist_ok=True)

    # Create a simple test audio file using ffmpeg (if available)
    test_audio = test_dir / "test_001.mp3"

    try:
        subprocess.run(
            [
                "ffmpeg", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
                "-t", "3", "-acodec", "libmp3lame", "-y", str(test_audio)
            ],
            capture_output=True,
            check=True
        )

        duration, sample_rate = probe_audio_metadata(test_audio)
        print(f"✅ Audio probe test: {duration:.2f}s @ {sample_rate}Hz")

        test_audio.unlink()
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⏭️  Skipping audio test (ffmpeg not available)")

    test_dir.rmdir()

    print("✅ TTS engine test completed")
