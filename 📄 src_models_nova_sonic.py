"""
Amazon Nova 2 Sonic — Real-Time Voice Coaching Client
Used by: Voice coaching WebSocket handler, CareerCoachAgent

Implements bidirectional audio streaming with Nova 2 Sonic via AWS Bedrock.
The voice session flow:
  1. User speaks → PCM audio chunks → WebSocket → this client
  2. Nova 2 Sonic transcribes + understands context
  3. Nova 2 Sonic generates voice response (TTS)
  4. PCM audio → WebSocket → browser → plays back to user

Nova 2 Sonic is the centerpiece of SkillForge's Voice AI category entry.
It enables natural, turn-based career coaching conversations.
"""

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import AsyncGenerator, Optional

import boto3
from botocore.config import Config

from src.config import settings

logger = logging.getLogger(__name__)


class SessionState(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class VoiceSession:
    """Tracks state of a single Nova 2 Sonic voice coaching session."""
    session_id: str
    user_id: str
    state: SessionState = SessionState.IDLE
    transcript_chunks: list[str] = field(default_factory=list)
    turn_count: int = 0
    started_at: float = field(default_factory=time.time)
    coaching_context: dict = field(default_factory=dict)

    @property
    def full_transcript(self) -> str:
        return " ".join(self.transcript_chunks)

    @property
    def duration_seconds(self) -> float:
        return time.time() - self.started_at


# ── System Prompts for Nova 2 Sonic ──────────────────────────────────
COACHING_SYSTEM_PROMPT = """You are SkillForge AI, an empathetic and expert career coach \
specializing in helping technology professionals reskill for the future of work.

Your coaching style:
- Warm, encouraging, and direct
- Ask precise, insight-generating questions
- Listen actively and reflect back what you hear
- Focus on skills, aspirations, and blockers
- Keep responses concise for voice (< 40 words per turn)

Your goal in this session:
1. Discover their current role and experience (2-3 turns)
2. Understand their career aspirations (2-3 turns)
3. Identify their top skills and confidence levels (3-4 turns)
4. Surface their blockers and motivations (2-3 turns)
5. Understand their learning constraints (time, budget) (2 turns)

Opening: Greet them warmly and ask: "Tell me about your current role and what brings you here today."
"""


class NovaSonicClient:
    """
    Amazon Nova 2 Sonic client for real-time voice career coaching.

    Uses Bedrock's bidirectional streaming API for sub-second latency
    speech-to-speech conversations. This enables a fully natural
    voice coaching experience without push-to-talk friction.
    """

    def __init__(self):
        self._client = boto3.client(
            "bedrock-runtime",
            region_name=settings.bedrock_region,
            config=Config(
                region_name=settings.bedrock_region,
                read_timeout=300,
                connect_timeout=30,
            ),
            aws_access_key_id=settings.aws_access_key_id or None,
            aws_secret_access_key=settings.aws_secret_access_key or None,
            aws_session_token=settings.aws_session_token or None,
        )
        self.model_id = settings.nova2_sonic_model_id
        self._sessions: dict[str, VoiceSession] = {}

    # ── Session Management ────────────────────────────────────────────
    async def create_session(
        self,
        user_id: str,
        coaching_context: Optional[dict] = None,
    ) -> str:
        """
        Create a new bidirectional voice session with Nova 2 Sonic.
        Returns a session_id for tracking this coaching conversation.
        """
        session_id = f"sonic_{user_id}_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        session = VoiceSession(
            session_id=session_id,
            user_id=user_id,
            coaching_context=coaching_context or {},
        )
        self._sessions[session_id] = session
        logger.info(f"Created Nova 2 Sonic session: {session_id}")
        return session_id

    async def process_audio_stream(
        self,
        session_id: str,
        audio_chunk: bytes,
    ) -> AsyncGenerator[dict, None]:
        """
        Core Nova 2 Sonic bidirectional streaming method.

        Sends PCM audio to Nova 2 Sonic and yields response events:
          {"type": "transcript", "text": "...", "is_final": bool}
          {"type": "audio", "data": bytes}       — PCM response audio
          {"type": "turn_end"}                    — Nova finished speaking
          {"type": "coaching_update", "data": {}} — structured profile update

        AWS Bedrock Nova Sonic uses InvokeModelWithBidirectionalStream,
        a binary streaming protocol optimized for real-time audio.
        """
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        session.state = SessionState.LISTENING

        # Build the streaming request payload
        initial_config = json.dumps({
            "schemaVersion": "agents-v1:1",
            "system": [{"text": COACHING_SYSTEM_PROMPT}],
            "audioInputConfig": {
                "mediaType": "audio/pcm",
                "sampleRateHertz": settings.sonic_sample_rate,
                "sampleSizeBits": 16,
                "channelCount": settings.sonic_channels,
                "voiceActivityDetectionConfig": {
                    "silenceThresholdMs": settings.silence_threshold_ms,
                },
            },
            "audioOutputConfig": {
                "mediaType": "audio/pcm",
                "sampleRateHertz": settings.sonic_sample_rate,
                "sampleSizeBits": 16,
                "channelCount": settings.sonic_channels,
                "voiceId": "Emma",  # Nova 2 Sonic voice persona
            },
            "sessionContext": {
                "turnCount": session.turn_count,
                "coachingContext": session.coaching_context,
            },
        })

        try:
            # Initiate bidirectional stream
            loop = asyncio.get_event_loop()

            # Create the bidirectional stream handler
            stream_response = await loop.run_in_executor(
                None,
                lambda: self._client.invoke_model_with_bidirectional_stream(
                    modelId=self.model_id,
                    body=initial_config.encode(),
                ),
            )

            # Send audio chunk asynchronously
            await loop.run_in_executor(
                None,
                lambda: stream_response["stream_handler"].write(audio_chunk),
            )

            # Process response events
            async for event in self._read_stream_events(stream_response):
                if event.get("type") == "transcript":
                    text = event.get("text", "")
                    if event.get("is_final") and text:
                        session.transcript_chunks.append(text)
                    yield event

                elif event.get("type") == "audio":
                    session.state = SessionState.SPEAKING
                    yield event

                elif event.get("type") == "turn_end":
                    session.turn_count += 1
                    session.state = SessionState.LISTENING
                    yield event

        except self._client.exceptions.ModelTimeoutException:
            logger.warning(f"Nova Sonic timeout for session {session_id}")
            session.state = SessionState.ERROR
            yield {"type": "error", "message": "Voice session timed out"}

        except Exception as exc:
            logger.error(f"Nova 2 Sonic streaming error: {exc}", exc_info=True)
            session.state = SessionState.ERROR
            yield {"type": "error", "message": str(exc)}

    async def _read_stream_events(self, stream_response) -> AsyncGenerator[dict, None]:
        """Parse Nova 2 Sonic bidirectional stream response events."""
        loop = asyncio.get_event_loop()

        def read_next():
            return next(iter(stream_response.get("body", [])), None)

        while True:
            event = await loop.run_in_executor(None, read_next)
            if event is None:
                break

            # Text/transcript event
            if "transcript" in event:
                data = event["transcript"]
                yield {
                    "type": "transcript",
                    "text": data.get("text", ""),
                    "is_final": data.get("isFinal", False),
                    "confidence": data.get("confidence", 1.0),
                }

            # Audio response event (Nova speaking back)
            elif "audioOutput" in event:
                yield {
                    "type": "audio",
                    "data": event["audioOutput"].get("bytes", b""),
                    "is_last_chunk": event["audioOutput"].get("isLastChunk", False),
                }

            # Turn completion
            elif "turnComplete" in event:
                yield {"type": "turn_end", "turn_id": event.get("turnId")}

            # Session state change
            elif "sessionState" in event:
                yield {"type": "session_state", "state": event["sessionState"]}

    async def get_transcript(self, session_id: str) -> str:
        """Return the accumulated conversation transcript."""
        session = self._sessions.get(session_id)
        if not session:
            return ""
        return session.full_transcript

    async def get_session_stats(self, session_id: str) -> dict:
        """Return session statistics for analytics."""
        session = self._sessions.get(session_id)
        if not session:
            return {}
        return {
            "session_id": session_id,
            "duration_seconds": session.duration_seconds,
            "turn_count": session.turn_count,
            "transcript_words": len(session.full_transcript.split()),
            "state": session.state.value,
        }

    async def close_session(self, session_id: str) -> None:
        """Clean up session resources."""
        session = self._sessions.pop(session_id, None)
        if session:
            session.state = SessionState.COMPLETED
            logger.info(
                f"Closed Nova Sonic session {session_id} "
                f"| {session.turn_count} turns "
                f"| {session.duration_seconds:.1f}s"
            )