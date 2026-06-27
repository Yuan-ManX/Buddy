"""
Buddy Voice Interface Engine - Voice interaction and audio processing.

Provides a comprehensive voice interface for the Buddy platform, enabling
speech-to-text, text-to-speech, voice command recognition, and audio
processing capabilities. The engine supports multiple voice profiles,
real-time streaming, and emotion detection from voice tone.

Core capabilities:
- Speech-to-text transcription with multi-language support
- Text-to-speech synthesis with voice profile selection
- Voice command recognition and intent mapping
- Audio emotion/tone analysis
- Voice profile management and customization
- Real-time audio streaming support
- Voice activity detection and silence handling
- Multi-speaker diarization
"""

from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger("buddy.voice_interface")


# ═══════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════

class VoiceCommand(str, Enum):
    """Common voice commands recognized by the system."""
    START = "start"
    STOP = "stop"
    PAUSE = "pause"
    RESUME = "resume"
    CANCEL = "cancel"
    CONFIRM = "confirm"
    DENY = "deny"
    HELP = "help"
    REPEAT = "repeat"
    SUMMARIZE = "summarize"
    SEARCH = "search"
    NAVIGATE = "navigate"


class AudioFormat(str, Enum):
    """Supported audio formats."""
    WAV = "wav"
    MP3 = "mp3"
    FLAC = "flac"
    OGG = "ogg"
    WEBM = "webm"
    PCM = "pcm"


class VoiceProfile(str, Enum):
    """Predefined voice profiles for text-to-speech."""
    DEFAULT = "default"
    PROFESSIONAL = "professional"
    FRIENDLY = "friendly"
    AUTHORITATIVE = "authoritative"
    WARM = "warm"
    CONCISE = "concise"


class EmotionTone(str, Enum):
    """Detected emotional tones from voice audio."""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    FRUSTRATED = "frustrated"
    EXCITED = "excited"
    CALM = "calm"
    ANXIOUS = "anxious"
    CONFIDENT = "confident"
    UNCERTAIN = "uncertain"


class SpeechLanguage(str, Enum):
    """Supported languages for speech processing."""
    EN = "en"
    ZH = "zh"
    JA = "ja"
    KO = "ko"
    ES = "es"
    FR = "fr"
    DE = "de"
    AUTO = "auto"


# ═══════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════

@dataclass
class TranscriptionResult:
    """Result of a speech-to-text transcription."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    text: str = ""
    language: SpeechLanguage = SpeechLanguage.AUTO
    confidence: float = 0.0
    duration_ms: float = 0.0
    speaker_count: int = 1
    segments: list[dict[str, Any]] = field(default_factory=list)
    words: list[dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class SynthesisRequest:
    """Request for text-to-speech synthesis."""
    text: str
    voice_profile: VoiceProfile = VoiceProfile.DEFAULT
    language: SpeechLanguage = SpeechLanguage.EN
    speed: float = 1.0
    pitch: float = 1.0
    format: AudioFormat = AudioFormat.MP3


@dataclass
class SynthesisResult:
    """Result of a text-to-speech synthesis."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    text: str = ""
    audio_url: str = ""
    duration_ms: float = 0.0
    format: AudioFormat = AudioFormat.MP3
    voice_profile: VoiceProfile = VoiceProfile.DEFAULT
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ToneAnalysis:
    """Voice tone/emotion analysis result."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    primary_emotion: EmotionTone = EmotionTone.NEUTRAL
    secondary_emotions: dict[str, float] = field(default_factory=dict)
    confidence: float = 0.0
    energy_level: float = 0.5
    speaking_rate_wpm: float = 0.0
    pitch_variation: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class VoiceSession:
    """An active voice interaction session."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    status: str = "active"
    language: SpeechLanguage = SpeechLanguage.AUTO
    transcription_history: list[TranscriptionResult] = field(default_factory=list)
    synthesis_history: list[SynthesisResult] = field(default_factory=list)
    tone_history: list[ToneAnalysis] = field(default_factory=list)
    commands_recognized: list[VoiceCommand] = field(default_factory=list)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: datetime | None = None


# ═══════════════════════════════════════════════════════════
# Voice Interface Engine
# ═══════════════════════════════════════════════════════════

class VoiceInterfaceEngine:
    """Comprehensive voice interaction and audio processing engine.

    Provides speech-to-text, text-to-speech, voice command recognition,
    and emotion/tone analysis capabilities. Supports multiple voice
    profiles, languages, and audio formats.

    In production, this engine connects to ASR/TTS APIs (Whisper,
    ElevenLabs, etc.) and local audio devices. The current implementation
    provides a simulation layer for testing and development.
    """

    # Voice command keyword mappings
    COMMAND_KEYWORDS: dict[str, VoiceCommand] = {
        "start": VoiceCommand.START,
        "begin": VoiceCommand.START,
        "stop": VoiceCommand.STOP,
        "end": VoiceCommand.STOP,
        "pause": VoiceCommand.PAUSE,
        "hold": VoiceCommand.PAUSE,
        "resume": VoiceCommand.RESUME,
        "continue": VoiceCommand.RESUME,
        "cancel": VoiceCommand.CANCEL,
        "abort": VoiceCommand.CANCEL,
        "confirm": VoiceCommand.CONFIRM,
        "yes": VoiceCommand.CONFIRM,
        "deny": VoiceCommand.DENY,
        "no": VoiceCommand.DENY,
        "help": VoiceCommand.HELP,
        "repeat": VoiceCommand.REPEAT,
        "again": VoiceCommand.REPEAT,
        "summarize": VoiceCommand.SUMMARIZE,
        "summary": VoiceCommand.SUMMARIZE,
        "search": VoiceCommand.SEARCH,
        "find": VoiceCommand.SEARCH,
        "navigate": VoiceCommand.NAVIGATE,
        "go to": VoiceCommand.NAVIGATE,
    }

    def __init__(self) -> None:
        self._sessions: dict[str, VoiceSession] = {}
        self._transcriptions: list[TranscriptionResult] = []
        self._syntheses: list[SynthesisResult] = []
        self._tone_analyses: list[ToneAnalysis] = []
        self._voice_profiles: dict[str, dict[str, Any]] = {
            "default": {"speed": 1.0, "pitch": 1.0, "description": "Default balanced voice"},
            "professional": {"speed": 0.9, "pitch": 1.0, "description": "Clear professional tone"},
            "friendly": {"speed": 1.1, "pitch": 1.1, "description": "Warm and friendly"},
            "authoritative": {"speed": 0.85, "pitch": 0.9, "description": "Commanding and clear"},
            "warm": {"speed": 1.0, "pitch": 1.05, "description": "Gentle and warm"},
            "concise": {"speed": 1.2, "pitch": 1.0, "description": "Fast and to the point"},
        }
        self._total_sessions: int = 0
        self._total_transcriptions: int = 0
        self._total_syntheses: int = 0

    # ── Session Management ─────────────────────────────────────────

    def create_session(
        self,
        language: SpeechLanguage = SpeechLanguage.AUTO,
    ) -> VoiceSession:
        """Create a new voice interaction session.

        Args:
            language: Preferred language for the session.

        Returns:
            A new VoiceSession instance.
        """
        session = VoiceSession(language=language)
        self._sessions[session.id] = session
        self._total_sessions += 1
        logger.info("Voice session created: %s", session.id)
        return session

    def end_session(self, session_id: str) -> VoiceSession | None:
        """End an active voice session.

        Args:
            session_id: The session to end.

        Returns:
            The ended session, or None if not found.
        """
        session = self._sessions.get(session_id)
        if session:
            session.status = "ended"
            session.ended_at = datetime.now(timezone.utc)
            logger.info("Voice session ended: %s", session_id)
        return session

    def get_session(self, session_id: str) -> VoiceSession | None:
        """Get a voice session by ID."""
        return self._sessions.get(session_id)

    # ── Speech-to-Text ─────────────────────────────────────────────

    def transcribe(
        self,
        session_id: str,
        audio_text: str = "",
        language: SpeechLanguage = SpeechLanguage.AUTO,
    ) -> TranscriptionResult:
        """Transcribe speech to text.

        In production, this would process actual audio data. The current
        implementation accepts pre-transcribed text for simulation.

        Args:
            session_id: The voice session ID.
            audio_text: Simulated transcription text.
            language: Language of the audio.

        Returns:
            TranscriptionResult with the transcribed text.
        """
        session = self._sessions.get(session_id)
        if not session:
            session = self.create_session(language)

        result = TranscriptionResult(
            text=audio_text or "Simulated transcription",
            language=language,
            confidence=0.95,
            duration_ms=len(audio_text) * 80.0 if audio_text else 1500.0,
            segments=[
                {"start_ms": 0, "end_ms": 1500, "text": audio_text or "Simulated transcription"}
            ],
        )
        self._transcriptions.append(result)
        session.transcription_history.append(result)
        self._total_transcriptions += 1

        # Check for voice commands
        self._detect_commands(result, session)

        return result

    def _detect_commands(
        self, result: TranscriptionResult, session: VoiceSession
    ) -> None:
        """Internal: detect voice commands in transcription."""
        text_lower = result.text.lower().strip()
        for keyword, command in self.COMMAND_KEYWORDS.items():
            if keyword in text_lower:
                if command not in session.commands_recognized:
                    session.commands_recognized.append(command)
                logger.debug("Voice command detected: %s -> %s", keyword, command.value)

    # ── Text-to-Speech ─────────────────────────────────────────────

    def synthesize(self, request: SynthesisRequest) -> SynthesisResult:
        """Synthesize speech from text.

        Generates a simulated audio URL. In production, this would
        call a TTS API and return actual audio data.

        Args:
            request: SynthesisRequest with text and voice settings.

        Returns:
            SynthesisResult with the audio URL and metadata.
        """
        # Estimate duration based on text length and speed
        word_count = len(request.text.split())
        base_duration = word_count * 300.0  # ~300ms per word
        duration = base_duration / request.speed

        result = SynthesisResult(
            text=request.text,
            audio_url=f"voice://synthesis/{uuid.uuid4().hex[:12]}.{request.format.value}",
            duration_ms=duration,
            format=request.format,
            voice_profile=request.voice_profile,
        )
        self._syntheses.append(result)
        self._total_syntheses += 1

        logger.debug(
            "Speech synthesized: %d words, %.0fms, profile=%s",
            word_count, duration, request.voice_profile.value,
        )
        return result

    def synthesize_and_add_to_session(
        self,
        session_id: str,
        request: SynthesisRequest,
    ) -> SynthesisResult:
        """Synthesize speech and add to a session's history.

        Args:
            session_id: The voice session ID.
            request: SynthesisRequest with text and voice settings.

        Returns:
            SynthesisResult with the audio URL.
        """
        result = self.synthesize(request)
        session = self._sessions.get(session_id)
        if session:
            session.synthesis_history.append(result)
        return result

    # ── Tone Analysis ──────────────────────────────────────────────

    def analyze_tone(
        self,
        session_id: str,
        text: str = "",
        energy_level: float = 0.5,
        speaking_rate: float = 150.0,
    ) -> ToneAnalysis:
        """Analyze emotional tone from voice or text.

        Simulates emotion detection. In production, this would use
        audio signal processing and ML models.

        Args:
            session_id: The voice session ID.
            text: Text content for sentiment analysis.
            energy_level: Simulated energy level (0.0-1.0).
            speaking_rate: Simulated words per minute.

        Returns:
            ToneAnalysis with detected emotions.
        """
        # Simple keyword-based emotion detection
        primary = EmotionTone.NEUTRAL
        secondary: dict[str, float] = {}

        text_lower = text.lower()
        if any(w in text_lower for w in ["great", "awesome", "wonderful", "love", "amazing"]):
            primary = EmotionTone.HAPPY
            secondary = {"excited": 0.3, "confident": 0.2}
        elif any(w in text_lower for w in ["sad", "unfortunate", "sorry", "miss", "lost"]):
            primary = EmotionTone.SAD
            secondary = {"neutral": 0.3}
        elif any(w in text_lower for w in ["angry", "furious", "upset", "annoyed"]):
            primary = EmotionTone.ANGRY
            secondary = {"frustrated": 0.4}
        elif any(w in text_lower for w in ["worried", "concerned", "nervous", "afraid"]):
            primary = EmotionTone.ANXIOUS
            secondary = {"uncertain": 0.3}
        elif any(w in text_lower for w in ["sure", "confident", "certain", "definitely"]):
            primary = EmotionTone.CONFIDENT

        analysis = ToneAnalysis(
            primary_emotion=primary,
            secondary_emotions=secondary,
            confidence=0.8,
            energy_level=energy_level,
            speaking_rate_wpm=speaking_rate,
            pitch_variation=0.3,
        )
        self._tone_analyses.append(analysis)

        session = self._sessions.get(session_id)
        if session:
            session.tone_history.append(analysis)

        return analysis

    # ── Voice Profiles ─────────────────────────────────────────────

    def get_voice_profiles(self) -> dict[str, dict[str, Any]]:
        """Get all available voice profiles."""
        return dict(self._voice_profiles)

    def create_voice_profile(
        self,
        name: str,
        speed: float = 1.0,
        pitch: float = 1.0,
        description: str = "",
    ) -> dict[str, Any]:
        """Create a custom voice profile.

        Args:
            name: Profile name.
            speed: Speaking speed multiplier.
            pitch: Voice pitch multiplier.
            description: Profile description.

        Returns:
            The created profile dictionary.
        """
        profile = {
            "speed": max(0.5, min(2.0, speed)),
            "pitch": max(0.5, min(2.0, pitch)),
            "description": description or f"Custom voice: {name}",
        }
        self._voice_profiles[name] = profile
        return profile

    # ── Statistics ─────────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        """Get voice interface statistics."""
        return {
            "total_sessions": self._total_sessions,
            "active_sessions": sum(
                1 for s in self._sessions.values() if s.status == "active"
            ),
            "total_transcriptions": self._total_transcriptions,
            "total_syntheses": self._total_syntheses,
            "total_tone_analyses": len(self._tone_analyses),
            "voice_profiles": list(self._voice_profiles.keys()),
            "languages_supported": [lang.value for lang in SpeechLanguage],
            "commands_available": [cmd.value for cmd in VoiceCommand],
            "recent_transcriptions": [
                {"text": t.text[:100], "confidence": t.confidence}
                for t in self._transcriptions[-5:]
            ],
        }

    def reset(self) -> None:
        """Reset all voice interface state."""
        self._sessions.clear()
        self._transcriptions.clear()
        self._syntheses.clear()
        self._tone_analyses.clear()
        self._total_sessions = 0
        self._total_transcriptions = 0
        self._total_syntheses = 0


# ═══════════════════════════════════════════════════════════
# Singleton Accessors
# ═══════════════════════════════════════════════════════════

_voice_interface: VoiceInterfaceEngine | None = None


def get_voice_interface() -> VoiceInterfaceEngine:
    """Get or create the singleton VoiceInterfaceEngine."""
    global _voice_interface
    if _voice_interface is None:
        _voice_interface = VoiceInterfaceEngine()
    return _voice_interface


def reset_voice_interface() -> None:
    """Reset the singleton VoiceInterfaceEngine."""
    global _voice_interface
    if _voice_interface is not None:
        _voice_interface.reset()
    _voice_interface = None