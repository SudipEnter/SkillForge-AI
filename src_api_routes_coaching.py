"""
SkillForge AI — Coaching API Routes
REST endpoints for managing voice coaching sessions and processing results.
"""

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from src.agents.orchestrator import SkillForgeOrchestrator
from src.database.dynamodb import DynamoDBClient
from src.config import settings

router = APIRouter()
orchestrator = SkillForgeOrchestrator()
db = DynamoDBClient()


class StartSessionRequest(BaseModel):
    user_id: str
    target_role: Optional[str] = None
    location: Optional[str] = "United States"


class SessionResponse(BaseModel):
    session_id: str
    user_id: str
    ws_url: str
    created_at: str


class CoachingCompleteRequest(BaseModel):
    session_id: str
    user_id: str
    coaching_profile: dict
    target_role: Optional[str] = None


@router.post("/start", response_model=SessionResponse)
async def start_coaching_session(request: StartSessionRequest):
    """
    Initialize a new voice coaching session.
    Returns WebSocket URL for the Nova 2 Sonic voice connection.
    """
    session_id = f"sf_{request.user_id}_{uuid.uuid4().hex[:8]}"

    # Store session in DynamoDB
    await db.put_item(
        table=settings.dynamodb_table_sessions,
        item={
            "session_id": session_id,
            "user_id": request.user_id,
            "status": "initialized",
            "target_role": request.target_role or "",
            "location": request.location or "United States",
            "created_at": datetime.utcnow().isoformat(),
        },
    )

    ws_url = (
        f"ws://localhost:{settings.app_port}/ws/coaching/{session_id}"
        f"?user_id={request.user_id}"
    )

    return SessionResponse(
        session_id=session_id,
        user_id=request.user_id,
        ws_url=ws_url,
        created_at=datetime.utcnow().isoformat(),
    )


@router.post("/complete")
async def process_coaching_completion(
    request: CoachingCompleteRequest,
    background_tasks: BackgroundTasks,
):
    """
    Process the end of a coaching session.
    Triggers the autonomous agent pipeline in the background:
    Skills Gap Analysis → Learning Path → Enrollment
    """
    # Update session status
    await db.update_item(
        table=settings.dynamodb_table_sessions,
        key={"session_id": request.session_id, "user_id": request.user_id},
        updates={"status": "complete", "completed_at": datetime.utcnow().isoformat()},
    )

    # Enrich profile with target role if provided
    profile = request.coaching_profile
    if request.target_role:
        profile["aspirations"] = profile.get("aspirations", [])
        if request.target_role not in profile["aspirations"]:
            profile["aspirations"].insert(0, request.target_role)

    # Fire the agent pipeline in background (non-blocking)
    background_tasks.add_task(
        orchestrator.process_coaching_completion,
        user_id=request.user_id,
        coaching_profile=profile,
    )

    return {
        "status": "processing",
        "message": "Coaching session complete. Running AI analysis pipeline...",
        "session_id": request.session_id,
        "pipeline_stages": [
            "Skills Gap Analysis",
            "Learning Path Generation",
            "Course Enrollment",
            "Calendar Sync",
        ],
    }


@router.get("/history/{user_id}")
async def get_coaching_history(user_id: str):
    """Get all coaching sessions for a user."""
    sessions = await db.query_items(
        table=settings.dynamodb_table_sessions,
        key_condition="user_id = :uid",
        expression_values={":uid": user_id},
        limit=20,
    )
    return {"user_id": user_id, "sessions": sessions}


@router.get("/session/{session_id}")
async def get_session(session_id: str, user_id: str):
    """Get details of a specific coaching session."""
    session = await db.get_item(
        table=settings.dynamodb_table_sessions,
        key={"session_id": session_id, "user_id": user_id},
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session