"""
SkillForge AI — Amazon Nova Act Integration
Autonomous UI workflow automation for course enrollment, certification, and job applications.

Nova Act agents navigate real web UIs to:
- Enroll learners in courses on Coursera, Udemy, LinkedIn Learning, AWS Training
- Submit certification applications to Pearson VUE, Credly, AWS Certification
- File job applications on Workday, Greenhouse, Lever, LinkedIn Easy Apply
- Sync learning schedules to Google Calendar
"""

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from nova_act import NovaAct, NovaActConfig

from src.config import settings

logger = logging.getLogger(__name__)


class AutomationPlatform(str, Enum):
    # Learning Platforms
    COURSERA = "coursera"
    UDEMY = "udemy"
    LINKEDIN_LEARNING = "linkedin_learning"
    AWS_TRAINING = "aws_training"
    EDEX = "edx"
    # Certification Bodies
    AWS_CERTIFICATION = "aws_certification"
    CREDLY = "credly"
    PEARSON_VUE = "pearson_vue"
    # Job Portals
    WORKDAY = "workday"
    GREENHOUSE = "greenhouse"
    LEVER = "lever"
    LINKEDIN_JOBS = "linkedin_jobs"
    # Calendar
    GOOGLE_CALENDAR = "google_calendar"


class AutomationStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    REQUIRES_REVIEW = "requires_review"


@dataclass
class AutomationResult:
    """Result of a Nova Act automation workflow."""
    task_id: str
    platform: AutomationPlatform
    status: AutomationStatus
    action_taken: str
    confirmation_number: Optional[str] = None
    confirmation_url: Optional[str] = None
    screenshot_path: Optional[str] = None
    error_message: Optional[str] = None
    duration_seconds: float = 0.0
    metadata: dict = field(default_factory=dict)


class NovaActClient:
    """
    Amazon Nova Act client for autonomous UI workflow automation.

    Manages a fleet of Act agents that operate web browsers to
    complete administrative tasks on behalf of learners.
    """

    def __init__(self):
        self.act_config = NovaActConfig(
            api_key=settings.nova_act_api_key,
            endpoint=settings.nova_act_endpoint,
            timeout_seconds=120,
            screenshot_on_failure=True,
        )

    async def enroll_in_course(
        self,
        user_id: str,
        course: dict,
        payment_info: Optional[dict] = None,
    ) -> AutomationResult:
        """
        Autonomously enroll a learner in a course on the appropriate platform.

        Args:
            user_id: Learner identifier for credential lookup
            course: {
                "platform": str,
                "course_id": str,
                "course_url": str,
                "title": str,
                "price": float,
            }
            payment_info: Pre-authorized payment method or L&D budget account

        Returns:
            AutomationResult with enrollment confirmation
        """
        platform = AutomationPlatform(course["platform"])
        task_description = (
            f"Enroll the learner in the course '{course['title']}' "
            f"on {platform.value}. "
            f"Navigate to {course['course_url']}, complete enrollment, "
            f"and return the enrollment confirmation number."
        )

        return await self._execute_workflow(
            task_id=f"enroll_{user_id}_{course['course_id']}",
            platform=platform,
            task_description=task_description,
            starting_url=course["course_url"],
            credentials=self._get_platform_credentials(platform),
            additional_context={
                "payment_info": payment_info,
                "course_title": course["title"],
            },
        )

    async def submit_certification_application(
        self,
        user_id: str,
        certification: dict,
        learner_profile: dict,
    ) -> AutomationResult:
        """
        Submit a certification exam application on behalf of the learner.

        Args:
            certification: {
                "platform": str,           # e.g., "aws_certification"
                "cert_name": str,          # e.g., "AWS Solutions Architect Associate"
                "exam_code": str,          # e.g., "SAA-C03"
                "registration_url": str,
            }
            learner_profile: Full learner profile with personal info
        """
        platform = AutomationPlatform(certification["platform"])
        task_description = (
            f"Register the learner for the {certification['cert_name']} exam "
            f"(code: {certification['exam_code']}) on {platform.value}. "
            f"Complete the registration form with the provided learner information, "
            f"select an available exam date within the next 30 days, "
            f"and return the registration confirmation number."
        )

        return await self._execute_workflow(
            task_id=f"cert_{user_id}_{certification['exam_code']}",
            platform=platform,
            task_description=task_description,
            starting_url=certification["registration_url"],
            credentials=self._get_platform_credentials(platform),
            additional_context={"learner_profile": learner_profile},
        )

    async def upload_credential_to_linkedin(
        self,
        user_id: str,
        credential: dict,
    ) -> AutomationResult:
        """
        Upload an earned certification/credential to the learner's LinkedIn profile.
        """
        task_description = (
            f"Add the credential '{credential['name']}' issued by "
            f"'{credential['issuer']}' to the learner's LinkedIn profile "
            f"under the Licenses & Certifications section. "
            f"Include the credential ID: {credential.get('credential_id', 'N/A')} "
            f"and the credential URL: {credential.get('credential_url', '')}."
        )

        return await self._execute_workflow(
            task_id=f"linkedin_cred_{user_id}_{credential['name'].replace(' ', '_')}",
            platform=AutomationPlatform.LINKEDIN_JOBS,
            task_description=task_description,
            starting_url="https://www.linkedin.com/in/me/",
            credentials=self._get_platform_credentials(AutomationPlatform.LINKEDIN_JOBS),
            additional_context={"credential": credential},
        )

    async def submit_job_application(
        self,
        user_id: str,
        job: dict,
        application_materials: dict,
    ) -> AutomationResult:
        """
        Submit a tailored job application on a hiring platform.

        Args:
            job: {
                "platform": str,      # "workday", "greenhouse", "lever", etc.
                "job_url": str,
                "company": str,
                "title": str,
                "job_id": str,
            }
            application_materials: {
                "tailored_resume_path": str,
                "cover_letter": str,
                "portfolio_url": str,
                "answers": {question: answer} for application form questions
            }
        """
        platform = AutomationPlatform(job["platform"])
        task_description = (
            f"Submit a job application for the '{job['title']}' role at "
            f"'{job['company']}'. "
            f"Navigate to {job['job_url']}, complete all required application "
            f"fields using the provided resume and cover letter, "
            f"answer any screening questions using the provided answers, "
            f"upload the resume from the provided path, "
            f"and submit the application. Return the confirmation number or "
            f"application reference ID."
        )

        return await self._execute_workflow(
            task_id=f"apply_{user_id}_{job['job_id']}",
            platform=platform,
            task_description=task_description,
            starting_url=job["job_url"],
            credentials=self._get_platform_credentials(platform),
            additional_context={"application_materials": application_materials},
        )

    async def sync_to_google_calendar(
        self,
        user_id: str,
        learning_schedule: list[dict],
    ) -> AutomationResult:
        """
        Create focused learning blocks in the learner's Google Calendar.

        Args:
            learning_schedule: [
                {
                    "course_title": str,
                    "date": str,          # ISO format
                    "start_time": str,    # "09:00"
                    "duration_minutes": int,
                    "course_url": str,
                }
            ]
        """
        events_summary = ", ".join([
            f"{e['course_title']} on {e['date']}"
            for e in learning_schedule[:5]
        ])
        task_description = (
            f"Create calendar events in Google Calendar for the following "
            f"learning sessions: {events_summary}. "
            f"For each session, create a focused learning block with the course "
            f"title as the event name, add the course URL to the event description, "
            f"set the status to 'Busy', and add a 10-minute reminder. "
            f"Use the color 'Blueberry' for all learning blocks."
        )

        return await self._execute_workflow(
            task_id=f"calendar_{user_id}_{len(learning_schedule)}_events",
            platform=AutomationPlatform.GOOGLE_CALENDAR,
            task_description=task_description,
            starting_url="https://calendar.google.com",
            credentials=self._get_platform_credentials(AutomationPlatform.GOOGLE_CALENDAR),
            additional_context={"learning_schedule": learning_schedule},
        )

    async def _execute_workflow(
        self,
        task_id: str,
        platform: AutomationPlatform,
        task_description: str,
        starting_url: str,
        credentials: dict,
        additional_context: Optional[dict] = None,
    ) -> AutomationResult:
        """
        Execute a Nova Act automation workflow in a managed browser session.
        """
        import time
        start_time = time.time()
        logger.info(f"Starting Nova Act workflow: {task_id} on {platform.value}")

        try:
            async with NovaAct(
                config=self.act_config,
                starting_url=starting_url,
                credentials=credentials,
            ) as agent:

                # Build the complete task with context
                full_task = task_description
                if additional_context:
                    full_task += f"\n\nAdditional context:\n{additional_context}"

                # Execute the Nova Act agent
                result = await agent.act(
                    task=full_task,
                    extract_schema={
                        "confirmation_number": "string | null",
                        "confirmation_url": "string | null",
                        "success": "boolean",
                        "error_details": "string | null",
                    },
                )

                duration = time.time() - start_time
                extracted = result.extracted_data or {}

                if result.success and extracted.get("success"):
                    logger.info(
                        f"Nova Act workflow {task_id} completed in {duration:.1f}s. "
                        f"Confirmation: {extracted.get('confirmation_number', 'N/A')}"
                    )
                    return AutomationResult(
                        task_id=task_id,
                        platform=platform,
                        status=AutomationStatus.COMPLETED,
                        action_taken=task_description[:200],
                        confirmation_number=extracted.get("confirmation_number"),
                        confirmation_url=extracted.get("confirmation_url"),
                        screenshot_path=result.screenshot_path,
                        duration_seconds=duration,
                    )
                else:
                    error_msg = extracted.get("error_details", "Unknown error")
                    logger.warning(
                        f"Nova Act workflow {task_id} requires review: {error_msg}"
                    )
                    return AutomationResult(
                        task_id=task_id,
                        platform=platform,
                        status=AutomationStatus.REQUIRES_REVIEW,
                        action_taken=task_description[:200],
                        error_message=error_msg,
                        screenshot_path=result.screenshot_path,
                        duration_seconds=duration,
                    )

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Nova Act workflow {task_id} failed: {e}")
            return AutomationResult(
                task_id=task_id,
                platform=platform,
                status=AutomationStatus.FAILED,
                action_taken=task_description[:200],
                error_message=str(e),
                duration_seconds=duration,
            )

    def _get_platform_credentials(self, platform: AutomationPlatform) -> dict:
        """Retrieve stored credentials for a specific platform."""
        credential_map = {
            AutomationPlatform.COURSERA: {
                "username": settings.coursera_username,
                "password": settings.coursera_password,
            },
            AutomationPlatform.UDEMY: {
                "api_key": settings.udemy_api_key,
            },
            AutomationPlatform.LINKEDIN_LEARNING: {
                "token": settings.linkedin_learning_token,
            },
            AutomationPlatform.LINKEDIN_JOBS: {
                "token": settings.linkedin_learning_token,
            },
        }
        return credential_map.get(platform, {})