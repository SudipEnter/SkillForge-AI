"""SkillForge AI — Learning Path API Routes"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from src.agents.learning_path_agent import LearningPathAgent
from src.agents.enrollment_agent import EnrollmentAgent
from src.agents.skills_gap_agent import SkillsGapAgent, SkillsGapReport
from src.database.dynamodb import DynamoDBClient
from src.config import settings

router = APIRouter()
learning_path_agent = LearningPathAgent()
enrollment_agent = EnrollmentAgent()
db = DynamoDBClient()


class BuildPathRequest(BaseModel):
    user_id: str
    target_role: str
    target_location: str = "United States"
    weekly_hours: float = 12.0
    weekly_budget_usd: float = 50.0
    preferred_providers: Optional[list[str]] = None


class EnrollRequest(BaseModel):
    user_id: str
    auto_approve_under_usd: float = 25.0


class CalendarSyncRequest(BaseModel):
    user_id: str
    start_date: str = ""  # ISO date string


@router.get("/{user_id}/path")
async def get_learning_path(user_id: str):
    """Get a learner's active learning path."""
    path_data = await db.get_item(
        table=settings.dynamodb_table_learning_paths,
        key={"user_id": user_id},
    )
    if not path_data:
        raise HTTPException(
            status_code=404,
            detail="No learning path found. Complete a coaching session first.",
        )
    return path_data


@router.post("/build")
async def build_learning_path(request: BuildPathRequest):
    """
    Build a personalized learning path.
    Requires a completed skills gap analysis (run /skills/analyze first).
    """
    # Load gap report from DynamoDB
    user_data = await db.get_item(
        table=settings.dynamodb_table_users,
        key={"user_id": request.user_id},
    )

    if not user_data or not user_data.get("gap_report"):
        raise HTTPException(
            status_code=400,
            detail="Skills gap analysis required before building a learning path. "
                   "Call POST /api/v1/skills/analyze first.",
        )

    # Reconstruct gap report object (simplified for route layer)
    gap_data = user_data["gap_report"]

    # For a full implementation, deserialize the complete SkillsGapReport
    # For demo, pass the essential fields through the agent
    gap_agent = SkillsGapAgent()
    full_report = await gap_agent.analyze_gaps(
        user_id=request.user_id,
        skills_profile=user_data.get("coaching_profile", {}),
        target_role=request.target_role,
        target_location=request.target_location,
    )

    path = await learning_path_agent.build_learning_path(
        gap_report=full_report,
        weekly_hours_available=request.weekly_hours,
        max_weekly_budget_usd=request.weekly_budget_usd,
        preferred_providers=request.preferred_providers,
    )

    # Persist learning path
    await db.put_item(
        table=settings.dynamodb_table_learning_paths,
        item={
            "user_id": request.user_id,
            "path_summary": path.path_summary,
            "total_weeks": path.total_weeks,
            "estimated_salary_increase": path.estimated_salary_increase,
            "weekly_time_commitment_hours": path.weekly_time_commitment_hours,
            "total_cost_usd": path.total_cost_usd,
            "weeks": path.weeks,
            "certifications": path.certifications,
            "portfolio_projects": path.portfolio_projects,
            "created_at": datetime.utcnow().isoformat(),
        },
    )

    return {
        "user_id": request.user_id,
        "path_summary": path.path_summary,
        "total_weeks": path.total_weeks,
        "estimated_salary_increase": path.estimated_salary_increase,
        "weekly_time_commitment_hours": path.weekly_time_commitment_hours,
        "total_cost_usd": path.total_cost_usd,
        "certifications_count": len(path.certifications),
        "portfolio_projects_count": len(path.portfolio_projects),
        "enrollment_queue_size": len(path.get_enrollment_queue()),
    }


@router.post("/enroll")
async def trigger_enrollment(
    request: EnrollRequest,
    background_tasks: BackgroundTasks,
):
    """
    Trigger Nova Act autonomous enrollment for all queued courses.
    Runs in background — returns immediately with job ID.
    """
    path_data = await db.get_item(
        table=settings.dynamodb_table_learning_paths,
        key={"user_id": request.user_id},
    )

    if not path_data:
        raise HTTPException(status_code=404, detail="Learning path not found")

    enrollment_queue = [
        {
            "platform": week_resource.get("provider", "other").lower(),
            "course_url": week_resource.get("url", ""),
            "title": week_resource.get("title", ""),
            "cost_usd": week_resource.get("cost_usd", 0),
        }
        for week in path_data.get("weeks", [])
        for week_resource in week.get("resources", [])
        if week_resource.get("type") == "course"
    ]

    background_tasks.add_task(
        enrollment_agent.process_enrollment_queue,
        user_id=request.user_id,
        enrollment_queue=enrollment_queue,
        auto_approve_under_usd=request.auto_approve_under_usd,
    )

    return {
        "status": "enrollment_queued",
        "user_id": request.user_id,
        "courses_to_enroll": len(enrollment_queue),
        "auto_approve_threshold": f"${request.auto_approve_under_usd}",
        "message": (
            f"Nova Act is enrolling you in {len(enrollment_queue)} courses. "
            f"Check the dashboard for real-time progress."
        ),
    }


@router.post("/calendar/sync")
async def sync_calendar(request: CalendarSyncRequest):
    """Sync the learning path schedule to Google Calendar via Nova Act."""
    path_data = await db.get_item(
        table=settings.dynamodb_table_learning_paths,
        key={"user_id": request.user_id},
    )

    if not path_data:
        raise HTTPException(status_code=404, detail="Learning path not found")

    from src.agents.learning_path_agent import LearningPath
    start = (
        datetime.fromisoformat(request.start_date)
        if request.start_date
        else datetime.utcnow()
    )

    # Build simplified schedule from stored path
    schedule = []
    for week in path_data.get("weeks", []):
        week_offset = week.get("week_number", 1) - 1
        week_start = start.replace(day=start.day + week_offset * 7)
        for idx, resource in enumerate(week.get("resources", [])):
            from datetime import timedelta
            session_date = week_start + timedelta(days=idx * 2)
            schedule.append({
                "course_title": resource.get("title", "Learning Session"),
                "date": session_date.strftime("%Y-%m-%d"),
                "start_time": "09:00",
                "duration_minutes": int(resource.get("duration_hours", 2) * 60),
                "course_url": resource.get("url", ""),
            })

    success = await enrollment_agent.sync_learning_calendar(
        user_id=request.user_id,
        learning_schedule=schedule,
    )

    return {
        "status": "synced" if success else "failed",
        "events_created": len(schedule) if success else 0,
    }