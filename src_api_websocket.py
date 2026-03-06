"""
SkillForge AI — WebSocket Voice Coaching Handler
Real-time bidirectional audio streaming for Nova 2 Sonic coaching sessions.
"""

import asyncio
import json
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState

from src.models.nova_sonic import NovaSonicClient
from src.agents.career_coach import CareerCoachAgent

logger = logging.getLogger(__name__)
router = APIRouter()

nova_sonic = NovaSonicClient()
career_coach = CareerCoachAgent()


class VoiceSessionManager:
    """Manages active WebSocket voice coaching sessions."""

    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, session_id: str) -> None:
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"Voice session connected: {session_id}")

    def disconnect(self, session_id: str) -> None:
        self.active_connections.pop(session_id, None)
        logger.info(f"Voice session disconnected: {session_id}")

    async def send_audio(self, session_id: str, audio_bytes: bytes) -> None:
        ws = self.active_connections.get(session_id)
        if ws and ws.client_state == WebSocketState.CONNECTED:
            await ws.send_bytes(audio_bytes)

    async def send_event(self, session_id: str, event: dict) -> None:
        ws = self.active_connections.get(session_id)
        if ws and ws.client_state == WebSocketState.CONNECTED:
            await ws.send_json(event)


session_manager = VoiceSessionManager()


@router.websocket("/coaching/{session_id}")
async def voice_coaching_endpoint(
    websocket: WebSocket,
    session_id: str,
    user_id: Optional[str] = None,
):
    """
    WebSocket endpoint for real-time voice coaching with Nova 2 Sonic.

    Protocol:
    Client → Server: Binary audio chunks (PCM 16kHz 16-bit mono)
    Server → Client: Binary audio (coach voice) + JSON events

    JSON Events:
    - {"type": "session.started", "session_id": str}
    - {"type": "transcript.learner", "text": str, "is_final": bool}
    - {"type": "transcript.coach", "text": str}
    - {"type": "analysis.tone", "tone": str}
    - {"type": "analysis.skill_detected", "skill": str, "confidence": str}
    - {"type": "session.summary", "profile": dict}
    - {"type": "error", "message": str}
    """
    await session_manager.connect(websocket, session_id)

    # Use session_id as user_id fallback for demo purposes
    effective_user_id = user_id or session_id

    # Create Nova Sonic session
    voice_session = nova_sonic.create_session(
        session_id=session_id,
        user_id=effective_user_id,
    )

    try:
        # Send session started event
        await session_manager.send_event(session_id, {
            "type": "session.started",
            "session_id": session_id,
            "user_id": effective_user_id,
        })

        # Send opening greeting audio
        opening_audio = await nova_sonic.generate_coaching_opening(session_id)
        await session_manager.send_audio(session_id, opening_audio)
        await session_manager.send_event(session_id, {
            "type": "transcript.coach",
            "text": (
                "Hi there! I'm your SkillForge AI career coach. "
                "Tell me about what you're currently doing for work."
            ),
        })

        # Main audio streaming loop
        audio_buffer = bytearray()
        CHUNK_SIZE = 32768  # 32KB chunks for streaming

        while True:
            try:
                # Receive audio data from client
                message = await asyncio.wait_for(
                    websocket.receive(),
                    timeout=60.0  # 60s silence timeout
                )

                if message["type"] == "websocket.disconnect":
                    break

                if message["type"] == "websocket.receive":
                    if "bytes" in message and message["bytes"]:
                        # Accumulate audio data
                        audio_buffer.extend(message["bytes"])

                        # Process when we have enough audio
                        if len(audio_buffer) >= CHUNK_SIZE:
                            audio_chunk = bytes(audio_buffer)
                            audio_buffer = bytearray()

                            # Define callbacks for streaming responses
                            async def on_audio_chunk(chunk: bytes):
                                await session_manager.send_audio(session_id, chunk)

                            async def on_transcript(text: str):
                                await session_manager.send_event(session_id, {
                                    "type": "transcript.learner",
                                    "text": text,
                                    "is_final": False,
                                })

                            # Process through Nova 2 Sonic
                            coach_turn = await nova_sonic.stream_coaching_turn(
                                session_id=session_id,
                                audio_input=audio_chunk,
                                on_audio_chunk=on_audio_chunk,
                                on_transcript=on_transcript,
                            )

                            # Send analysis events
                            await session_manager.send_event(session_id, {
                                "type": "analysis.tone",
                                "tone": coach_turn.emotional_tone.value,
                            })

                            # Notify of any detected skills
                            for skill, confidence in (
                                coach_turn.confidence_signals.items()
                            ):
                                if not skill.startswith("_"):
                                    await session_manager.send_event(session_id, {
                                        "type": "analysis.skill_detected",
                                        "skill": skill,
                                        "confidence": confidence,
                                    })

                    elif "text" in message:
                        # Handle control messages
                        control = json.loads(message["text"])
                        if control.get("action") == "end_session":
                            break

            except asyncio.TimeoutError:
                logger.info(f"Session {session_id}: silence timeout, ending session")
                break

    except WebSocketDisconnect:
        logger.info(f"Client disconnected from session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error in session {session_id}: {e}")
        await session_manager.send_event(session_id, {
            "type": "error",
            "message": str(e),
        })
    finally:
        # Extract and send final session profile
        session_profile = nova_sonic.extract_session_profile(session_id)
        if session_profile:
            await session_manager.send_event(session_id, {
                "type": "session.summary",
                "profile": session_profile,
            })

        # Cleanup
        nova_sonic.end_session(session_id)
        session_manager.disconnect(session_id)