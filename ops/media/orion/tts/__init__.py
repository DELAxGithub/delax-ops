"""TTS adapters and configuration for Orion."""
from .orion_tts_generator import OrionTTSGenerator
from .tts_config_loader import load_merged_tts_config

__all__ = ["OrionTTSGenerator", "load_merged_tts_config"]
