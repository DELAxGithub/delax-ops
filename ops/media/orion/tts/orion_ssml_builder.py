"""SSML builder tailored for the Orion narration workflows."""
from __future__ import annotations

import html
import logging
import re
from typing import Any, Dict


logger = logging.getLogger(__name__)


class OrionSSMLBuilder:
    """Create SSML strings with pronunciation and pacing controls."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.pronunciation_hints: Dict[str, str] = config.get("pronunciation_hints", {})

        google_settings = config.get("google_tts", {})
        self.custom_breaks: Dict[str, int] = google_settings.get("custom_breaks", {})
        self.default_break_ms: int = int(google_settings.get("default_break_ms", google_settings.get("break_ms", 500)))
        self.segment_gap_ms: int = self._coerce_positive_int(
            google_settings.get("segment_gap_ms", 0), default=0
        )
        quote_breaks = google_settings.get("quote_breaks", {})
        if not isinstance(quote_breaks, dict):
            quote_breaks = {}
        self.quote_open_break_ms = self._coerce_positive_int(quote_breaks.get("open_ms", 120), default=0)
        self.quote_close_break_ms = self._coerce_positive_int(quote_breaks.get("close_ms", 0), default=0)
        replacements = google_settings.get("replacements", {})
        if isinstance(replacements, dict):
            # Apply longer patterns first to avoid partial overlaps.
            self.replacements = dict(
                sorted(((str(k), str(v)) for k, v in replacements.items()), key=lambda item: len(item[0]), reverse=True)
            )
        else:
            self.replacements = {}

    def build(
        self,
        text: str,
        character: str | None = None,
        scene: str | None = None,
        prev_scene: str | None = None,
    ) -> str:
        """Return an SSML string from raw text."""

        processed = self._preprocess(text)
        processed = self._apply_replacements(processed)
        processed = self._escape_html(processed)
        processed = self._apply_pronunciation_hints(processed)
        processed = self._insert_breaks(processed)
        processed = self._process_special_symbols(processed)

        if character:
            processed = self._apply_character_style(processed, character)

        if (
            self.segment_gap_ms > 0
            and self._needs_gap_after(text)
            and not self._has_trailing_break(processed)
        ):
            processed += f'<break time="{self.segment_gap_ms}ms"/>'

        prefix = ""
        if prev_scene is not None and scene is not None and scene != prev_scene:
            scene_ms = self.custom_breaks.get("scene_transition")
            if scene_ms is None:
                pacing = self.config.get("pacing", {})
                if isinstance(pacing, dict):
                    scene_ms = pacing.get("scene_pause_ms")
            if not scene_ms:
                scene_ms = self.default_break_ms
            try:
                scene_ms_int = int(scene_ms)
            except (TypeError, ValueError):
                try:
                    scene_ms_int = int(float(scene_ms))
                except (TypeError, ValueError):
                    scene_ms_int = int(self.default_break_ms)
            prefix = f'<break time="{scene_ms_int}ms"/>'

        ssml = f"<speak>{prefix}{processed}</speak>"
        self._validate_ssml(ssml)
        return ssml

    def _preprocess(self, text: str) -> str:
        translated = text.translate(
            str.maketrans(
                "０１２３４５６７８９ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ",
                "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
            )
        )
        normalized = translated.replace("\r\n", "\n").replace("\r", "\n")
        normalized = re.sub(r"[ \t]+", " ", normalized)
        normalized = re.sub(r"\n{3,}", "\n\n", normalized)
        return normalized.strip()

    def _escape_html(self, text: str) -> str:
        return html.escape(text, quote=True)

    def _apply_pronunciation_hints(self, text: str) -> str:
        updated = text
        for word, reading in self.pronunciation_hints.items():
            escaped_word = html.escape(word, quote=True)
            replacement = f'<sub alias="{html.escape(str(reading), quote=True)}">{escaped_word}</sub>'
            updated = updated.replace(escaped_word, replacement)
        return updated

    def _insert_breaks(self, text: str) -> str:
        working = text

        dash_patterns = ["——", "ーー", "−−", "--"]
        dash_break_ms = None
        for pattern in dash_patterns:
            if pattern in self.custom_breaks:
                dash_break_ms = self.custom_breaks[pattern]
                break
        if dash_break_ms is None:
            dash_break_ms = self.default_break_ms

        for pattern in dash_patterns:
            if pattern in working:
                working = working.replace(pattern, f'<break time="{dash_break_ms}ms"/>')

        # Handle multi-character breaks (e.g., ellipsis).
        for symbol, duration in self.custom_breaks.items():
            if symbol in dash_patterns:
                continue
            if len(symbol) > 1:
                working = working.replace(symbol, f'<break time="{duration}ms"/>')

        symbol_breaks = {
            symbol: duration
            for symbol, duration in self.custom_breaks.items()
            if len(symbol) == 1 and symbol in {"、", "。", "？", "！", "：", "，", "．", ",", ".", "?", "!", ":", ";"}
        }
        for symbol, duration in symbol_breaks.items():
            pattern = re.escape(symbol) + r"(?![^<]*</sub>)"
            working = re.sub(
                pattern,
                f"{symbol}<break time=\"{duration}ms\"/>",
                working,
            )

        scene_break = self.custom_breaks.get("scene_transition")
        if scene_break is None:
            pacing = self.config.get("pacing", {})
            if isinstance(pacing, dict):
                scene_break = pacing.get("scene_pause_ms")
        if scene_break:
            working = working.replace("\n\n", f'<break time="{scene_break}ms"/>')

        working = working.replace("\n", " ")

        return working

    def _process_special_symbols(self, text: str) -> str:
        def replace_quotes(match: re.Match[str]) -> str:
            inner = match.group(1)
            quoted = f'「{inner}」'
            parts: list[str] = []
            if self.quote_open_break_ms:
                parts.append(f'<break time="{self.quote_open_break_ms}ms"/>')
            parts.append(f'<emphasis level="moderate">{quoted}</emphasis>')
            if self.quote_close_break_ms:
                parts.append(f'<break time="{self.quote_close_break_ms}ms"/>')
            return "".join(parts)

        updated = re.sub(r"「([^」]+)」", replace_quotes, text)

        updated = re.sub(
            r"(\d{4})年",
            r'<say-as interpret-as="date" format="y">\1</say-as>年',
            updated,
        )

        updated = re.sub(
            r"(\d+)％",
            r'<say-as interpret-as="cardinal">\1</say-as>パーセント',
            updated,
        )

        return updated

    def _apply_character_style(self, text: str, character: str) -> str:
        if character == "孫子":
            return f'<prosody rate="85%" pitch="-2st">{text}</prosody>'
        if character == "マキャベリ":
            return f'<prosody rate="90%" pitch="-1st">{text}</prosody>'
        if character == "課長":
            return f'<prosody rate="105%" pitch="+1st">{text}</prosody>'
        if character == "部長":
            return f'<prosody rate="92%" pitch="-1st">{text}</prosody>'
        if character in {"若手", "若手社員"}:
            return f'<prosody rate="108%" pitch="+2st">{text}</prosody>'
        return text

    def _validate_ssml(self, ssml: str) -> None:
        if ssml.count("<speak>") != 1 or ssml.count("</speak>") != 1:
            logger.warning("SSML speak tag imbalance detected")

        if "<<" in ssml or ">>" in ssml:
            logger.error("Malformed SSML detected: duplicate angle brackets")

    def _needs_gap_after(self, raw_text: str) -> bool:
        text = raw_text.strip()
        if not text:
            return False

        # Remove closing quotes or brackets at the end for analysis.
        trailing_closers = ("」", "』", "）", "】", "》", "＞", ">", "'", '"')
        while text and text.endswith(trailing_closers):
            text = text[:-1].rstrip()

        if not text:
            return False

        sentence_endings = ("。", "！", "？", "…")
        if text.endswith(sentence_endings):
            return True

        # Dash variants imply continuation.
        if text.endswith(("——", "ーー", "−−", "--")):
            return False

        continuing_suffixes = (
            "が",
            "で",
            "に",
            "を",
            "と",
            "は",
            "も",
            "や",
            "へ",
            "し",
            "から",
            "ので",
            "けど",
            "けれど",
            "けれども",
            "ながら",
            "って",
            "たり",
        )
        for suffix in continuing_suffixes:
            if text.endswith(suffix):
                return False

        return True

    def _has_trailing_break(self, processed: str) -> bool:
        return bool(re.search(r"(<break\b[^>]*?/>)\s*$", processed.strip()))

    @staticmethod
    def _coerce_positive_int(value, default: int = 0) -> int:
        try:
            number = int(value)
        except (TypeError, ValueError):
            try:
                number = int(float(value))
            except (TypeError, ValueError):
                return default
        return number if number > 0 else default

    def _apply_replacements(self, text: str) -> str:
        if not getattr(self, "replacements", None):
            return text
        updated = text
        for src, dest in self.replacements.items():
            updated = updated.replace(src, dest)
        return updated


def build_ssml(
    text: str,
    character: str | None,
    config: Dict[str, Any],
    *,
    scene: str | None = None,
    prev_scene: str | None = None,
) -> str:
    builder = OrionSSMLBuilder(config)
    return builder.build(text, character, scene=scene, prev_scene=prev_scene)
