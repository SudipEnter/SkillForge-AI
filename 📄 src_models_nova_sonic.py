"""
SkillForge AI — Amazon Nova 2 Sonic Integration
Real-time bidirectional voice coaching using Nova's speech-to-speech model.

Nova 2 Sonic provides:
- Sub-250ms voice-to-voice latency
- Emotional tone detection and preservation
- Contextual conversation memory across the coaching session
- Real-time interruption handling (barge-in support)
"""

import asyncio
import json
import logging
import struct
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import AsyncGenerator, Callable, Optional

import boto3
import numpy as np
from botocore.config import Config

from src.config import settings

logger = logging.getLogger(__name__)


class AudioFormat(str, Enum):
    PCM_16K = "pcm_16000"
    PCM_24K = "pcm_24000"


class EmotionalTone(str, Enum):
    CONFIDENT = "confident"
    HESITANT = "hesitant"
    ANXIOUS = "anxious"
    ENTHUSIASTIC = "enthusiastic"
    NEUTRAL = "neutral"
    UNCERTAIN = "uncertain"


@dataclass
class VoiceChunk:
    """Audio data chunk for streaming."""
    audio_bytes: bytes
    timestamp_ms: int
    is_final: bool = False


@dataclass
class CoachingTurn:
    """A complete turn in the coaching conversation."""
    speaker: str  # "learner" or "coach"
    text: str
    audio_bytes: Optional[bytes]
    emotional_tone: EmotionalTone
    confidence_signals: dict = field(default_factory=dict)
    timestamp_ms: int = field(default_factory=lambda: int(time.time() * 1000))
    clinical_flags: list = field(default_factory=list)


@dataclass
class StreamingSession:
    """Active Nova 2 Sonic streaming session state."""
    session_id: str
    user_id: str
    conversation_history: list = field(default_factory=list)
    detected_skills: list = field(default_factory=list)
    confidence_patterns: dict = field(default_factory=dict)
    session_start_ms: int = field(default_factory=lambda: int(time.time() * 1000))
    is_active: bool = True


class NovaSonicClient:
    """
    Amazon Nova 2 Sonic client for real-time bidirectional voice coaching.

    Implements:
    - Streaming audio input from learner microphone
    - Real-time voice response generation by the AI coach
    - Emotional tone analysis from voice characteristics
    - Skill confidence detection from speech patterns
    - Session memory across the conversation
    """

    SYSTEM_PROMPT = """You are SkillForge AI, an expert career coach specialized in 
    workforce reskilling and career development. Your role is to conduct a warm, 
    professional Career Discovery Conversation with the learner.

    Your objectives during this conversation:
    1. Understand the learner's current role, years of experience, and key responsibilities
    2. Identify skills they feel confident in vs. areas of anxiety or uncertainty
    3. Uncover their career aspirations and target roles
    4. Detect enthusiasm signals to understand intrinsic motivations
    5. Ask probing but supportive follow-up questions

    Communication style:
    - Warm, encouraging, and professionally supportive
    - Use natural conversational language, not formal interview-speak
    - Acknowledge emotions and validate concerns before pivoting
    - When a learner hesitates or sounds uncertain, slow down and offer reassurance
    - Surface insights gently: "It sounds like data engineering might excite you more than
      your current analytics role — is that a fair observation?"

    After each learner response, internally tag:
    - SKILL_MENTIONED: [skill name] | CONFIDENCE: high/medium/low
    - ASPIRATION: [career goal]  
    - ANXIETY: [concern area]
    - ENTHUSIASM: [topic that energized them]

    These tags will be extracted by the system — do not speak them aloud."""

    def __init__(self):
        self.bedrock_runtime = boto3.client(
            service_name="bedrock-runtime",
            region_name=settings.aws_default_region,
            config=Config(
                connect_timeout=10,
                read_timeout=300,
                retries={"max_attempts": 3},
            ),
        )
        self.model_id = settings.nova_sonic_model_id
        self.active_sessions: dict[str, StreamingSession] = {}

    def create_session(self, session_id: str, user_id: str) -> StreamingSession:
        """Initialize a new coaching voice session."""
        session = StreamingSession(session_id=session_id, user_id=user_id)
        self.active_sessions[session_id] = session
        logger.info(f"Created Nova Sonic session: {session_id} for user: {user_id}")
        return session

    def end_session(self, session_id: str) -> Optional[StreamingSession]:
        """Terminate and retrieve final session state."""
        session = self.active_sessions.pop(session_id, None)
        if session:
            session.is_active = False
            logger.info(
                f"Ended Nova Sonic session: {session_id}. "
                f"Duration: {(time.time() * 1000 - session.session_start_ms) / 1000:.1f}s. "
                f"Skills detected: {len(session.detected_skills)}"
            )
        return session

    async def stream_coaching_turn(
        self,
        session_id: str,
        audio_input: bytes,
        on_audio_chunk: Callable[[bytes], asyncio.coroutine],
        on_transcript: Callable[[str], asyncio.coroutine],
    ) -> CoachingTurn:
        """
        Process one conversational turn through Nova 2 Sonic.

        Sends learner audio → receives AI coach audio + transcript + analysis.

        Args:
            session_id: Active streaming session identifier
            audio_input: Raw PCM audio bytes from learner microphone (16kHz, 16-bit)
            on_audio_chunk: Async callback fired with each AI response audio chunk
            on_transcript: Async callback fired with real-time transcript updates

        Returns:
            Complete CoachingTurn with transcript, tone, and detected signals
        """
        session = self.active_sessions.get(session_id)
        if not session or not session.is_active:
            raise ValueError(f"No active session found: {session_id}")

        # Build the Nova 2 Sonic request payload
        request_body = self._build_sonic_request(
            audio_bytes=audio_input,
            conversation_history=session.conversation_history,
            system_prompt=self.SYSTEM_PROMPT,
        )

        learner_transcript = ""
        coach_response_text = ""
        coach_audio_chunks = []
        emotional_tone = EmotionalTone.NEUTRAL
        confidence_signals = {}

        try:
            # Invoke Nova 2 Sonic with bidirectional streaming
            response = self.bedrock_runtime.invoke_model_with_response_stream(
                modelId=self.model_id,
                contentType="application/octet-stream",
                accept="application/json",
                body=json.dumps(request_body).encode(),
            )

            event_stream = response.get("body")

            async for event in self._iter_stream_events(event_stream):
                event_type = event.get("type")

                if event_type == "transcript.learner":
                    # Real-time learner speech transcription
                    chunk_text = event.get("text", "")
                    learner_transcript += chunk_text
                    await on_transcript(chunk_text)

                elif event_type == "audio.coach":
                    # AI coach voice response audio chunk
                    audio_data = event.get("audio", b"")
                    coach_audio_chunks.append(audio_data)
                    await on_audio_chunk(audio_data)

                elif event_type == "transcript.coach":
                    # AI coach response text transcript
                    coach_response_text = event.get("text", "")

                elif event_type == "analysis.tone":
                    # Emotional tone detected from learner's voice
                    tone_label = event.get("tone", "neutral")
                    emotional_tone = EmotionalTone(tone_label)

                elif event_type == "analysis.signals":
                    # Skill mentions, confidence levels, aspirations
                    confidence_signals = event.get("signals", {})
                    self._update_session_signals(session, confidence_signals)

                elif event_type == "turn.complete":
                    break

        except Exception as e:
            logger.error(f"Nova Sonic streaming error for session {session_id}: {e}")
            raise

        # Build the complete coaching turn record
        learner_turn = CoachingTurn(
            speaker="learner",
            text=learner_transcript,
            audio_bytes=audio_input,
            emotional_tone=emotional_tone,
            confidence_signals=confidence_signals,
        )

        coach_turn = CoachingTurn(
            speaker="coach",
            text=coach_response_text,
            audio_bytes=b"".join(coach_audio_chunks),
            emotional_tone=EmotionalTone.CONFIDENT,
        )

        # Append both turns to session history for context continuity
        session.conversation_history.append(
            {"role": "user", "content": learner_transcript}
        )
        session.conversation_history.append(
            {"role": "assistant", "content": coach_response_text}
        )

        logger.debug(
            f"Session {session_id} turn complete. "
            f"Learner: '{learner_transcript[:50]}...' | "
            f"Tone: {emotional_tone.value}"
        )

        return coach_turn

    def _build_sonic_request(
        self,
        audio_bytes: bytes,
        conversation_history: list,
        system_prompt: str,
    ) -> dict:
        """Construct the Nova 2 Sonic API request payload."""
        import base64

        return {
            "modelId": self.model_id,
            "input": {
                "audio": {
                    "data": base64.b64encode(audio_bytes).decode("utf-8"),
                    "format": AudioFormat.PCM_16K.value,
                    "encoding": "pcm",
                    "sample_rate": 16000,
                    "channels": 1,
                }
            },
            "output": {
                "audio": {
                    "format": AudioFormat.PCM_24K.value,
                    "voice": "nova-coach-v1",  # SkillForge coaching voice persona
                }
            },
            "system": system_prompt,
            "conversationHistory": conversation_history,
            "inferenceConfig": {
                "temperature": 0.7,
                "maxTokens": 1024,
                "bargeInEnabled": True,  # Allow learner to interrupt coach
                "silenceTimeoutMs": 2000,
            },
            "analysisConfig": {
                "emotionalToneDetection": True,
                "confidenceSignalExtraction": True,
                "skillMentionExtraction": True,
            },
        }

    async def _iter_stream_events(self, event_stream) -> AsyncGenerator[dict, None]:
        """Iterate over Nova Sonic streaming response events."""
        loop = asyncio.get_event_loop()

        def read_next_event():
            try:
                return next(event_stream)
            except StopIteration:
                return None

        while True:
            event = await loop.run_in_executor(None, read_next_event)
            if event is None:
                break

            # Parse the event payload
            if "chunk" in event:
                chunk_data = event["chunk"].get("bytes", b"")
                try:
                    parsed = json.loads(chunk_data.decode("utf-8"))
                    yield parsed
                except json.JSONDecodeError:
                    # Raw audio bytes event
                    yield {"type": "audio.coach", "audio": chunk_data}

    def _update_session_signals(
        self, session: StreamingSession, signals: dict
    ) -> None:
        """Update session state with extracted coaching signals."""
        # Track skill mentions with confidence levels
        for skill_mention in signals.get("skills_mentioned", []):
            skill_name = skill_mention.get("skill")
            confidence = skill_mention.get("confidence", "medium")
            if skill_name and skill_name not in session.detected_skills:
                session.detected_skills.append(skill_name)
                session.confidence_patterns[skill_name] = confidence

        # Track aspirations and anxieties for skills gap analysis
        if signals.get("aspiration"):
            session.confidence_patterns["_aspirations"] = (
                session.confidence_patterns.get("_aspirations", [])
                + [signals["aspiration"]]
            )

        if signals.get("anxiety"):
            session.confidence_patterns["_anxieties"] = (
                session.confidence_patterns.get("_anxieties", [])
                + [signals["anxiety"]]
            )

    async def generate_coaching_opening(self, session_id: str) -> bytes:
        """
        Generate the coach's opening voice greeting for a new session.
        Returns audio bytes of the coach's introduction.
        """
        opening_text = (
            "Hi there! I'm your SkillForge AI career coach. "
            "I'm really glad you're here today. "
            "Over the next 15 minutes, I'd love to have a genuine conversation "
            "about where you are in your career, where you want to go, "
            "and how we can build a path to get you there. "
            "There are no right or wrong answers — just talk to me like you would "
            "a trusted colleague. Whenever you're ready, tell me a bit about what "
            "you're currently doing for work."
        )

        response = self.bedrock_runtime.invoke_model(
            modelId=self.model_id,
            contentType="application/json",
            accept="application/octet-stream",
            body=json.dumps({
                "type": "text_to_speech",
                "text": opening_text,
                "voice": "nova-coach-v1",
                "output": {"format": AudioFormat.PCM_24K.value},
            }),
        )

        return response["body"].read()

    def extract_session_profile(self, session_id: str) -> dict:
        """
        Extract structured skills profile from completed coaching session.
        Used by SkillsGapAgent to begin quantitative analysis.
        """
        session = self.active_sessions.get(session_id)
        if not session:
            return {}

        return {
            "user_id": session.user_id,
            "session_id": session_id,
            "duration_minutes": (
                time.time() * 1000 - session.session_start_ms
            ) / 60000,
            "detected_skills": session.detected_skills,
            "confidence_patterns": session.confidence_patterns,
            "conversation_turns": len(session.conversation_history) // 2,
            "aspirations": session.confidence_patterns.get("_aspirations", []),
            "anxieties": session.confidence_patterns.get("_anxieties", []),
        }