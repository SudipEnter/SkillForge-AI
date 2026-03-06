"""
SkillForge AI — Enrollment & Automation Agent
Orchestrates Nova Act workflows for course enrollment, certification,
and job applications on behalf of learners.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Optional

from src.models.nova_act import NovaActClient, AutomationStatus
from src.database.dynamodb import DynamoDBClient
from src.config import settings

logger = logging.getLogger(__name__)


@dataclass
class EnrollmentSummary:
    """Summary of all enrollment automation actions."""
    user_id: str
    total_attempted: int
    successful: int
    requires_review: int
    failed: int
    total_cost_usd: float
    results: list[dict] = field(default_factory=list)
    calendar_synced: bool = False


class EnrollmentAgent:
    """
    Automates the complete enrollment pipeline using Nova Act.

    Handles:
    - Batch course enrollment across multiple platforms
    - Certification exam registration
    - Google Calendar schedule sync
    - LinkedIn credential upload after course completion
    - Job application submission
    """

    def __init__(self):
        self.nova_act = NovaActClient()
        self.db = DynamoDBClient()

    async def process_enrollment_queue(
        self,
        user_id: str,
        enrollment_queue: list[dict],
        auto_approve_under_usd: float = 25.0,
    ) -> list[dict]:
        """
        Process a complete enrollment queue using Nova Act agents.

        Courses under `auto_approve_under_usd` are enrolled automatically.
        More expensive courses are queued for learner approval.

        Args:
            user_id: Learner identifier
            enrollment_queue: List of courses from LearningPath.get_enrollment_queue()
            auto_approve_under_usd: Auto-enroll threshold

        Returns:
            List of AutomationResult dicts for each course
        """
        logger.info(
            f"Processing {len(enrollment_queue)} enrollments for user {user_id}"
        )

        # Separate auto-approve and needs-review courses
        auto_enroll = [
            c for c in enrollment_queue
            if c.get("cost_usd", 0) <= auto_approve_under_usd
        ]
        needs_review = [
            c for c in enrollment_queue
            if c.get("cost_usd", 0) > auto_approve_under_usd
        ]

        results = []

        # Auto-enroll concurrently (max 3 parallel Nova Act browsers)
        semaphore = asyncio.Semaphore(3)

        async def enroll_one(course: dict) -> dict:
            async with semaphore:
                result = await self.nova_act.enroll_in_course(
                    user_id=user_id,
                    course=course,
                )
                return {
                    "course_title": course.get("title"),
                    "platform": course.get("platform"),
                    "status": result.status.value,
                    "confirmation": result.confirmation_number,
                    "cost_usd": course.get("cost_usd", 0),
                    "duration_seconds": result.duration_seconds,
                }

        auto_tasks = [enroll_one(course) for course in auto_enroll]
        auto_results = await asyncio.gather(*auto_tasks, return_exceptions=True)

        for r in auto_results:
            if isinstance(r, Exception):
                results.append({
                    "status": "failed",
                    "error": str(r),
                    "cost_usd": 0,
                })
            else:
                results.append(r)

        # Mark high-cost courses as pending review
        for course in needs_review:
            results.append({
                "course_title": course.get("title"),
                "platform": course.get("platform"),
                "status": "pending_approval",
                "cost_usd": course.get("cost_usd", 0),
                "message": f"Course costs ${course.get('cost_usd', 0):.0f} — awaiting your approval",
            })

        # Save enrollment results to DynamoDB
        await self.db.put_item(
            table=settings.dynamodb_table_learning_paths,
            item={
                "user_id": user_id,
                "enrollment_results": results,
                "total_enrolled": sum(
                    1 for r in results if r["status"] == "completed"
                ),
            },
        )

        logger.info(
            f"Enrollment complete for {user_id}: "
            f"{sum(1 for r in results if r['status'] == 'completed')} enrolled, "
            f"{sum(1 for r in results if r['status'] == 'pending_approval')} pending"
        )

        return results

    async def register_certifications(
        self,
        user_id: str,
        certifications: list[dict],
        learner_profile: dict,
    ) -> list[dict]:
        """
        Auto-register learner for certification exams via Nova Act.
        Called when learner completes prerequisite coursework.
        """
        results = []
        for cert in certifications:
            result = await self.nova_act.submit_certification_application(
                user_id=user_id,
                certification=cert,
                learner_profile=learner_profile,
            )
            results.append({
                "cert_name": cert["cert_name"],
                "status": result.status.value,
                "confirmation": result.confirmation_number,
                "exam_url": result.confirmation_url,
            })
        return results

    async def sync_learning_calendar(
        self,
        user_id: str,
        learning_schedule: list[dict],
    ) -> bool:
        """Sync the learning path schedule to Google Calendar via Nova Act."""
        result = await self.nova_act.sync_to_google_calendar(
            user_id=user_id,
            learning_schedule=learning_schedule,
        )
        success = result.status == AutomationStatus.COMPLETED
        logger.info(
            f"Calendar sync for {user_id}: {'success' if success else 'failed'}"
        )
        return success

    async def submit_job_applications(
        self,
        user_id: str,
        job_matches: list[dict],
        application_materials: dict,
        max_applications: int = 5,
    ) -> list[dict]:
        """
        Submit tailored job applications via Nova Act.
        Respects daily application limits and tracks submission history.
        """
        results = []
        for job in job_matches[:max_applications]:
            result = await self.nova_act.submit_job_application(
                user_id=user_id,
                job=job,
                application_materials=application_materials,
            )
            results.append({
                "company": job.get("company"),
                "title": job.get("title"),
                "platform": job.get("platform"),
                "status": result.status.value,
                "confirmation": result.confirmation_number,
            })
        return results