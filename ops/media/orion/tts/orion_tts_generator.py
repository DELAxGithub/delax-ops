"""Google Cloud + Gemini hybrid TTS generator for narration workflows."""
from __future__ import annotations

import base64
import logging
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, Optional

from google.cloud import texttospeech

from .orion_ssml_builder import build_ssml


logger = logging.getLogger(__name__)


class OrionTTSGenerator:
    """Wrapper around Google Cloud Text-to-Speech for Orion content."""

    def __init__(self, config: Dict[str, Any]):
        self._load_env_file()
        self.config = config
        self.pronunciation_hints: Dict[str, str] = {}
        hints = config.get("pronunciation_hints")
        if isinstance(hints, dict):
            self.pronunciation_hints = hints
        self._google_client: texttospeech.TextToSpeechClient | None = None
        raw_root = config.get("raw") if isinstance(config.get("raw"), dict) else {}
        google_raw = raw_root.get("google_tts", {}) if isinstance(raw_root, dict) else {}
        if not google_raw and isinstance(config.get("google_tts"), dict):
            google_raw = config.get("google_tts", {})
        self._gemini_settings: Dict[str, Any] = {}
        if isinstance(google_raw, dict):
            settings = google_raw.get("gemini_dialogue")
            if isinstance(settings, dict):
                self._gemini_settings = settings
        logger.info(f"[DEBUG] Gemini settings loaded: {self._gemini_settings}")
        self._request_delay_sec = 0.0
        if self._gemini_settings:
            try:
                self._request_delay_sec = float(self._gemini_settings.get("request_delay_sec", 0.0))
            except (TypeError, ValueError):
                self._request_delay_sec = 0.0
        self._gemini_client = None
        self._gemini_api_keys = self._gather_gemini_keys()
        self._gemini_key_index = 0
        self._keys_tried_this_request = 0  # Track keys tried per request
        # TTS model fallback: Flash → Pro
        self._tts_model_primary = "gemini-2.5-flash-preview-tts"
        self._tts_model_fallback = "gemini-2.5-pro-preview-tts"
        self._using_fallback_model = False

    def generate(
        self,
        text: str,
        character: str,
        output_path: Path,
        segment_no: int | None = None,
        *,
        scene: str | None = None,
        prev_scene: str | None = None,
        gemini_voice: str | None = None,
        gemini_style_prompt: str | None = None,
    ) -> bool:
        """Generate an MP3 file for the supplied segment."""

        try:
            adjusted_text = text
            if self._should_rewrite_dialogue(character):
                adjusted_text = self._rewrite_with_gemini(text, character, scene)

            use_gemini = self._should_use_gemini_tts(character)
            require_gemini = use_gemini or bool(gemini_voice or gemini_style_prompt)
            if not use_gemini and (gemini_voice or gemini_style_prompt):
                # If voice or style is explicitly specified, use Gemini TTS if API keys are available
                if self._gemini_api_keys:
                    use_gemini = True
                else:
                    use_gemini = self._should_use_gemini(character)

            logger.info(f"[DEBUG] use_gemini={use_gemini}, gemini_voice={gemini_voice}, style_prompt={gemini_style_prompt}")
            if use_gemini:
                if self._synthesize_with_gemini_tts(
                    adjusted_text,
                    character,
                    scene,
                    output_path,
                    segment_no,
                    voice_override=gemini_voice,
                    style_override=gemini_style_prompt,
                ):
                    return True
                if require_gemini:
                    return False

            ssml = build_ssml(
                adjusted_text,
                character,
                self.config,
                scene=scene,
                prev_scene=prev_scene,
            )
            if segment_no is not None:
                logger.debug(f"[{segment_no:03d}] SSML => %s", ssml)

            voice_params = self._get_voice_config(character)
            audio_config = self._get_audio_config(character)

            synthesis_input = texttospeech.SynthesisInput(ssml=ssml)
            client = self._ensure_google_client()
            response = client.synthesize_speech(
                input=synthesis_input,
                voice=voice_params,
                audio_config=audio_config,
            )

            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(response.audio_content)

            display_no = f"[{segment_no:03d}] " if segment_no is not None else ""
            logger.info("%s%s -> %s", display_no, character, output_path.name)
            return True
        except Exception as exc:  # pragma: no cover - defensive
            display_no = f"[{segment_no:03d}] " if segment_no is not None else ""
            logger.error("%sFailed to synthesize %s: %s", display_no, character, exc)
            return False

    def _get_voice_config(self, character: str) -> texttospeech.VoiceSelectionParams:
        voices = self.config.get("google_tts", {}).get("voices", {})
        voice_info = voices.get(character, {}) if isinstance(voices, dict) else {}

        voice_name = voice_info.get("name") or os.getenv("GOOGLE_TTS_VOICE") or "ja-JP-Neural2-C"

        language_code = os.getenv("GOOGLE_TTS_LANGUAGE", "ja-JP")
        return texttospeech.VoiceSelectionParams(language_code=language_code, name=voice_name)

    def _get_audio_config(self, character: str) -> texttospeech.AudioConfig:
        voices = self.config.get("google_tts", {}).get("voices", {})
        voice_info = voices.get(character, {}) if isinstance(voices, dict) else {}

        speaking_rate = os.getenv("GOOGLE_TTS_SPEAKING_RATE")
        if speaking_rate is not None:
            rate_value = float(speaking_rate)
        else:
            rate_value = float(voice_info.get("speaking_rate", 1.0))

        pitch_setting = os.getenv("GOOGLE_TTS_PITCH")
        if pitch_setting is not None:
            pitch_value = float(pitch_setting)
        else:
            pitch_value = float(voice_info.get("pitch", 0.0))

        return texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=rate_value,
            pitch=pitch_value,
        )

    # ------------------------------------------------------------------
    # Gemini-assisted dialogue rewriting

    def _should_use_gemini(self, character: str) -> bool:
        if not self._gemini_settings or not isinstance(self._gemini_settings, dict):
            return False
        if not self._gemini_settings.get("enabled"):
            return False
        if character in {"", None}:
            return False
        narrator_aliases = {"ナレーター", "ナレーション", "Narrator"}
        if (
            character in narrator_aliases
            and not bool(self._gemini_settings.get("allow_narration"))
        ):
            return False
        if not self._gemini_api_keys:
            logger.debug("Gemini disabled because no GEMINI_API_KEY values were found.")
            return False
        return True

    def _should_rewrite_dialogue(self, character: str) -> bool:
        if not self._should_use_gemini(character):
            return False
        if not self._gemini_settings.get("rewrite_enabled", True):
            return False
        model = self._gemini_settings.get("rewrite_model") or os.getenv("GEMINI_MODEL")
        return bool(model)

    def _should_use_gemini_tts(self, character: str) -> bool:
        if not self._should_use_gemini(character):
            return False
        model = self._gemini_settings.get("tts_model") or os.getenv("GEMINI_TTS_MODEL")
        return bool(model)

    def _ensure_gemini_client(self) -> None:
        if self._gemini_client is not None:
            return
        api_key = self._current_gemini_key()
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set; cannot adjust dialogue with Gemini.")
        try:
            from google import genai  # type: ignore
        except ImportError as exc:  # pragma: no cover - defensive
            raise RuntimeError(
                "google-generativeai package is required for Gemini adjustments."
            ) from exc

        self._gemini_client = genai.Client(api_key=api_key)

    def _rewrite_with_gemini(self, text: str, character: str, scene: Optional[str]) -> str:
        if not self._should_rewrite_dialogue(character):
            return text
        for _ in range(max(len(self._gemini_api_keys), 1)):
            try:
                self._ensure_gemini_client()
            except Exception as exc:
                logger.warning("Gemini unavailable (%s); using original dialogue for %s.", exc, character)
                return text

            model = (
                self._gemini_settings.get("rewrite_model")
                or os.getenv("GEMINI_MODEL")
                or "gemini-2.5-pro"
            )
            base_instruction = self._gemini_settings.get("base_instruction", "").strip()
            style_prompts = self._gemini_settings.get("style_prompts", {})
            style_prompt = ""
            if isinstance(style_prompts, dict):
                style_prompt = style_prompts.get(character) or style_prompts.get("default", "")

            parts = [p.strip() for p in [base_instruction, style_prompt] if p and p.strip()]
            prompt_header = "\n".join(parts) if parts else "Rewrite the dialogue naturally for spoken Japanese."
            scene_note = f"Scene context: {scene}" if scene else ""
            prompt = "\n".join([prompt_header, scene_note, "---", text.strip(), "---"]).strip()

            try:
                response = self._gemini_client.models.generate_content(
                    model=model,
                    contents=prompt,
                )
                rewritten = self._extract_response_text(response)
                if rewritten:
                    logger.debug("Gemini rewrote dialogue for %s: %s", character, rewritten)
                    return rewritten
                logger.warning("Gemini returned empty rewrite for %s; falling back to original text.", character)
                return text
            except Exception as exc:
                if self._is_rate_limit_error(exc) and self._rotate_gemini_key():
                    continue
                logger.warning("Gemini rewrite failed for %s: %s", character, exc)
                return text
        return text

    @staticmethod
    def _extract_response_text(response: object) -> str:
        text = getattr(response, "text", None)
        if isinstance(text, str) and text.strip():
            return text.strip()

        candidates = getattr(response, "candidates", None)
        if not candidates:
            return ""

        for candidate in candidates:
            content = getattr(candidate, "content", None)
            if not content:
                continue
            parts = getattr(content, "parts", None)
            if not parts:
                continue
            for part in parts:
                part_text = getattr(part, "text", None)
                if isinstance(part_text, str) and part_text.strip():
                    return part_text.strip()
        return ""

    # ------------------------------------------------------------------
    # Gemini TTS synthesis

    def _synthesize_with_gemini_tts(
        self,
        text: str,
        character: str,
        scene: Optional[str],
        output_path: Path,
        segment_no: Optional[int],
        *,
        voice_override: Optional[str] = None,
        style_override: Optional[str] = None,
    ) -> bool:
        try:
            self._ensure_gemini_client()
        except Exception as exc:
            logger.warning("Gemini TTS unavailable (%s); falling back to Google for %s.", exc, character)
            return False

        tts_model = self._get_current_tts_model()
        voice_name = voice_override or self._pick_gemini_voice(character)

        annotated_text = self._annotate_text_for_gemini(text)
        logger.info(f"[DEBUG] Original text: {text[:50]}...")
        logger.info(f"[DEBUG] Cleaned text: {annotated_text[:50]}...")
        prompt = self._build_gemini_prompt(
            character,
            scene,
            annotated_text,
            custom_style=style_override,
        )

        attempts = 0
        max_attempts = 5
        response = None
        parts = []
        self._keys_tried_this_request = 0  # Reset for new segment
        while attempts < max_attempts:
            attempts += 1
            # Ensure client is valid before each attempt (may have been corrupted by 429)
            if self._gemini_client is None:
                self._ensure_gemini_client()
            try:
                response = self._gemini_client.models.generate_content(
                    model=tts_model,
                    contents=prompt,
                    config={
                        "response_modalities": ["AUDIO"],
                        "speech_config": {
                            "voice_config": {
                                "prebuilt_voice_config": {"voice_name": voice_name}
                            }
                        },
                    },
                )
            except Exception as exc:  # pragma: no cover - defensive
                logger.info("[DEBUG] Exception type: %s, message: %s", type(exc).__name__, str(exc)[:100])
                if self._is_rate_limit_error(exc):
                    self._keys_tried_this_request += 1
                    total_keys = len(self._gemini_api_keys) or 1
                    logger.info("[DEBUG] Rate limit detected, keys tried: %d/%d", self._keys_tried_this_request, total_keys)

                    # Try rotating API key first (but only if we haven't tried all keys)
                    if self._keys_tried_this_request < total_keys and self._rotate_gemini_key():
                        logger.info("[DEBUG] Rotated to next key")
                        continue

                    # All keys exhausted - try switching to fallback model
                    logger.info("[DEBUG] All keys exhausted, trying fallback. using_fallback=%s", self._using_fallback_model)
                    if self._switch_to_fallback_model():
                        tts_model = self._get_current_tts_model()
                        self._keys_tried_this_request = 0  # Reset for new model
                        self._ensure_gemini_client()  # Recreate client for new model
                        logger.info("[DEBUG] Switched to fallback model: %s", tts_model)
                        continue
                    logger.info("[DEBUG] Already on fallback, waiting...")
                    # Already on fallback, wait and retry
                    message = str(exc)
                    retry_delay = self._extract_retry_delay_seconds(exc)
                    if retry_delay is None:
                        if "per_day" in message or "per day" in message:
                            retry_delay = 60.0
                        else:
                            retry_delay = min(5.0 * attempts, 15.0)
                    logger.info(
                        "Gemini TTS quota exceeded for %s; retrying in %.1fs (attempt %d/%d)",
                        character,
                        retry_delay,
                        attempts,
                        max_attempts,
                    )
                    time.sleep(retry_delay)
                    continue
                if self._is_retryable_error(exc):
                    retry_delay = min(5.0 * attempts, 15.0)
                    logger.info(
                        "Gemini TTS transient error for %s; retrying in %.1fs (attempt %d/%d)",
                        character,
                        retry_delay,
                        attempts,
                        max_attempts,
                    )
                    time.sleep(retry_delay)
                    continue
                logger.warning("Gemini TTS request failed for %s: %s", character, exc)
                return False

            logger.info("[DEBUG] Response: %s, has candidates: %s", type(response).__name__ if response else "None", bool(response and response.candidates) if response else False)
            if response is None:
                # No response likely means rate limiting - try fallback immediately
                if not self._using_fallback_model:
                    if self._switch_to_fallback_model():
                        tts_model = self._get_current_tts_model()
                        self._gemini_client = None
                        logger.info("No response, switching to fallback: %s", tts_model)
                continue

            parts = (
                response.candidates[0].content.parts
                if response.candidates and response.candidates[0].content
                else []
            )
            if parts:
                break
            # Empty response likely means rate limiting - try fallback immediately
            if not self._using_fallback_model:
                if self._switch_to_fallback_model():
                    tts_model = self._get_current_tts_model()
                    self._gemini_client = None  # Force client recreation
                    logger.info("Empty response, switching to fallback: %s", tts_model)
                    continue
            if attempts < max_attempts:
                logger.warning(
                    "Gemini TTS returned no audio for %s; retrying (%d/%d)",
                    character,
                    attempts,
                    max_attempts,
                )
                time.sleep(1.0)
                continue
            logger.warning("Gemini TTS returned no audio for %s", character)
            return False

        if not parts:
            return False

        inline_data = getattr(parts[0], "inline_data", None)
        raw_data = getattr(inline_data, "data", b"") if inline_data else b""
        pcm_bytes = base64.b64decode(raw_data) if isinstance(raw_data, str) else raw_data
        if not pcm_bytes:
            logger.warning("Gemini TTS returned empty audio payload for %s", character)
            return False

        try:
            self._save_pcm_as_mp3(pcm_bytes, output_path)
        except Exception as exc:
            logger.warning("Failed to convert Gemini PCM to MP3 for %s: %s", character, exc)
            return False

        display_no = f"[{segment_no:03d}] " if segment_no is not None else ""
        model_label = "Pro" if self._using_fallback_model else "Flash"
        logger.info("%s%s (Gemini TTS/%s) -> %s", display_no, character, model_label, output_path.name)
        if self._request_delay_sec > 0:
            time.sleep(self._request_delay_sec)
        return True

    def _annotate_text_for_gemini(self, text: str) -> str:
        """Clean text for Gemini TTS by converting SSML to phonetic readings.

        Gemini TTS reads text literally, so:
        - SSML tags would be read aloud ("sub alias...")
        - We need to extract the phonetic reading (alias) instead

        Solution: Replace <sub alias='reading'>word</sub> with just 'reading'.
        """
        import re

        # Step 1: Extract phonetic reading from <sub alias> tags
        # Pattern: <sub alias='reading'>word</sub> -> reading
        # We keep ONLY the alias (phonetic reading), discard the word
        annotated = re.sub(
            r'<sub alias=[\'"]([^\'"]+)[\'"]>([^<]+)</sub>',
            r'\1',  # Keep only the alias (group 1) - the phonetic reading
            text
        )

        # Step 2: Remove ALL other SSML tags (like <break time='...'>)
        annotated = re.sub(r'<[^>]+>', '', annotated)

        # Step 3: Clean up any extra spaces left by tag removal
        annotated = re.sub(r'\s+', ' ', annotated).strip()

        return annotated

    @staticmethod
    def _is_rate_limit_error(exc: Exception) -> bool:
        message = str(exc)
        if "RESOURCE_EXHAUSTED" in message or "429" in message:
            return True
        # google-genai client corruption after 429 response
        if "'NoneType' object has no attribute" in message:
            return True
        errors = getattr(exc, "errors", None)
        if errors:
            for item in errors:
                reason = getattr(item, "reason", "")
                if reason and "rate" in reason.lower():
                    return True
        return False

    @staticmethod
    def _is_retryable_error(exc: Exception) -> bool:
        message = str(exc)
        if "500" in message or "INTERNAL" in message:
            return True
        if "temporarily" in message.lower():
            return True
        return False

    @staticmethod
    def _extract_retry_delay_seconds(exc: Exception) -> Optional[float]:
        retry_delay = getattr(exc, "retry_delay", None)
        if retry_delay:
            try:
                return float(retry_delay)
            except (TypeError, ValueError):
                pass
        message = str(exc)
        match = re.search(r"retryDelay['\"]?:\\s*'?([0-9.]+)s", message)
        if match:
            try:
                return float(match.group(1))
            except (TypeError, ValueError):
                return None
        return None

    def _get_current_tts_model(self) -> str:
        """Get the current TTS model, considering fallback state."""
        if self._using_fallback_model:
            return self._tts_model_fallback
        # Check config/env override first
        configured = (
            self._gemini_settings.get("tts_model")
            or os.getenv("GEMINI_TTS_MODEL")
        )
        if configured:
            return configured
        return self._tts_model_primary

    def _switch_to_fallback_model(self) -> bool:
        """Switch to fallback model (Pro). Returns True if switched."""
        if self._using_fallback_model:
            return False  # Already using fallback
        self._using_fallback_model = True
        self._gemini_key_index = 0  # Reset key index for new model
        self._gemini_client = None  # Force client recreation
        logger.warning(
            "⚠️  Switching to fallback model: %s → %s",
            self._tts_model_primary,
            self._tts_model_fallback,
        )
        return True

    def _pick_gemini_voice(self, character: str) -> str:
        overrides = self._gemini_settings.get("voice_overrides", {})
        if isinstance(overrides, dict):
            voice = overrides.get(character) or overrides.get("default")
            if voice:
                return voice
        return self._gemini_settings.get("voice_name", "kore")

    def _build_gemini_prompt(
        self,
        character: str,
        scene: Optional[str],
        text: str,
        *,
        custom_style: Optional[str] = None,
    ) -> str:
        # Gemini TTS reads the ENTIRE prompt aloud, so we ONLY send the text
        # No instructions, no style prompts - just the text to be spoken
        return text.strip()

    def _save_pcm_as_mp3(self, pcm_data: bytes, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "s16le",
            "-ar",
            "24000",
            "-ac",
            "1",
            "-i",
            "-",
            "-filter:a",
            "atempo=0.9",  # 0.9倍速（少しゆっくり目）
            str(output_path),
        ]
        proc = subprocess.run(cmd, input=pcm_data, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.decode("utf-8", errors="ignore"))

    def _current_gemini_key(self) -> Optional[str]:
        if not self._gemini_api_keys:
            return None
        index = self._gemini_key_index % len(self._gemini_api_keys)
        return self._gemini_api_keys[index]

    def _rotate_gemini_key(self) -> bool:
        if len(self._gemini_api_keys) <= 1:
            return False
        self._gemini_key_index = (self._gemini_key_index + 1) % len(self._gemini_api_keys)
        self._gemini_client = None
        return True

    def _gather_gemini_keys(self) -> list[str]:
        self._load_env_file()
        keys: list[str] = []

        def add(value: Optional[str]) -> None:
            if value and value not in keys:
                keys.append(value)

        add(os.getenv("GEMINI_API_KEY"))
        for idx in range(1, 10):
            add(os.getenv(f"GEMINI_API_KEY_{idx}"))
        return keys

    def _load_env_file(self) -> None:
        env_path = REPO_ROOT / ".env"
        if not env_path.exists():
            return
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if not line or line.strip().startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if not key or key in os.environ:
                continue
            os.environ[key] = value.strip()

    @staticmethod
    def _ensure_env_var(name: str) -> None:
        if os.getenv(name):
            return
        env_path = REPO_ROOT / ".env" if 'REPO_ROOT' in globals() else Path(__file__).resolve().parents[2] / ".env"
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                if not line or line.strip().startswith("#"):
                    continue
                if line.startswith(f"{name}="):
                    _, value = line.split("=", 1)
                    os.environ[name] = value.strip()
                    return

    def _ensure_google_client(self) -> texttospeech.TextToSpeechClient:
        if self._google_client is None:
            self._google_client = texttospeech.TextToSpeechClient()
        return self._google_client
REPO_ROOT = Path(__file__).resolve().parents[1]
