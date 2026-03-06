"""
SkillForge AI — Agent Fleet Orchestrator
Coordinates all Nova-powered agents using AWS Strands Agents framework.

The orchestrator manages the complete learner journey:
  Voice Coaching → Skills Gap → Learning Path → Enrollment → Job Application

All agent-to-agent communication is routed through this coordinator,
which uses Nova 2 Lite for meta-reasoning about which agents to invoke
and in what order based on learner state.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
from datetime import datetime

from strands import Agent, tool
from strands.models import BedrockModel

from src.config import settings
from src.models.nova_lite import NovaLiteClient
from src.agents.skills_gap_agent import SkillsGapAgent, SkillsGapReport
from src.agents.learning_path_agent import LearningPathAgent, LearningPath
from src.agents.job_market_agent import JobMarketAgent
from src.agents.enrollment_agent import EnrollmentAgent
from src.database.dynamodb import DynamoDBClient

logger = logging.getLogger(__name__)


class LearnerJourneyStage(str, Enum):
    """Tracks where a learner is in their SkillForge journey."""
    ONBOARDING = "onboarding"
    COACHING_COMPLETE = "coaching_complete"
    GAP_ANALYSIS_COMPLETE = "gap_analysis_complete"
    LEARNING_PATH_ACTIVE = "learning_path_active"
    ENROLLED = "enrolled"
    CERTIFYING = "certifying"
    JOB_HUNTING = "job_hunting"
    PLACED = "placed"


@dataclass
class OrchestratorState:
    """Complete state of a learner's orchestrated journey."""
    user_id: str
    stage: LearnerJourneyStage = LearnerJourneyStage.ONBOARDING
    coaching_profile: Optional[dict] = None
    gap_report: Optional[SkillsGapReport] = None
    learning_path: Optional[LearningPath] = None
    enrollment_results: list[dict] = field(default_factory=list)
    job_applications: list[dict] = field(default_factory=list)
    last_updated: str = field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )


ORCHESTRATOR_SYSTEM_PROMPT = """You are SkillForge AI's Master Orchestrator.
You coordinate a fleet of specialized agents to guide learners through 
complete career reskilling journeys.

Your available agents:
- skills_gap_agent: Analyzes skills gaps against job market data
- learning_path_agent: Designs week-by-week personalized learning paths
- job_market_agent: Provides real-time job market intelligence
- enrollment_agent: Automates course enrollment and certification registration

Decision protocol:
1. Assess the learner's current journey stage
2. Determine which agents to invoke and in what sequence
3. Pass relevant context between agents
4. Handle agent failures with graceful fallbacks
5. Surface insights to the learner interface

Always return your orchestration plan as JSON:
{
  "next_actions": [{"agent": str, "action": str, "priority": int}],
  "reasoning": str,
  "estimated_completion_minutes": int
}"""


class SkillForgeOrchestrator:
    """
    Master coordinator for the SkillForge AI agent fleet.
    Uses AWS Strands Agents for structured multi-agent workflows
    and Nova 2 Lite for orchestration meta-reasoning.
    """

    def __init__(self):
        self.nova_lite = NovaLiteClient()
        self.db = DynamoDBClient()

        # Initialize specialized agents
        self.skills_gap_agent = SkillsGapAgent()
        self.learning_path_agent = LearningPathAgent()
        self.job_market_agent = JobMarketAgent()
        self.enrollment_agent = EnrollmentAgent()

        # Initialize Strands Agent for orchestration reasoning
        self.strands_model = BedrockModel(
            model_id=settings.nova_lite_model_id,
            region_name=settings.aws_default_region,
        )
        self._build_strands_agent()

    def _build_strands_agent(self):
        """Build the Strands Agent with tool bindings for each sub-agent."""

        @tool
        async def analyze_skills_gap(
            user_id: str,
            target_role: str,
            target_location: str = "United States",
        ) -> dict:
            """Analyze a learner's skills gaps against a target job role."""
            state = await self._load_state(user_id)
            if not state.coaching_profile:
                return {"error": "Coaching session required before gap analysis"}

            report = await self.skills_gap_agent.analyze_gaps(
                user_id=user_id,
                skills_profile=state.coaching_profile,
                target_role=target_role,
                target_location=target_location,
            )
            state.gap_report = report
            state.stage = LearnerJourneyStage.GAP_ANALYSIS_COMPLETE
            await self._save_state(state)
            return {
                "career_readiness_score": report.career_readiness_score,
                "urgent_gaps": report.urgent_gaps,
                "gap_summary": report.gap_summary,
            }

        @tool
        async def build_learning_path(
            user_id: str,
            weekly_hours: float = 12.0,
            weekly_budget_usd: float = 50.0,
        ) -> dict:
            """Build a personalized learning path from the skills gap report."""
            state = await self._load_state(user_id)
            if not state.gap_report:
                return {"error": "Skills gap analysis required first"}

            path = await self.learning_path_agent.build_learning_path(
                gap_report=state.gap_report,
                weekly_hours_available=weekly_hours,
                max_weekly_budget_usd=weekly_budget_usd,
            )
            state.learning_path = path
            state.stage = LearnerJourneyStage.LEARNING_PATH_ACTIVE
            await self._save_state(state)
            return {
                "total_weeks": path.total_weeks,
                "path_summary": path.path_summary,
                "estimated_salary_increase": path.estimated_salary_increase,
                "enrollment_queue_size": len(path.get_enrollment_queue()),
            }

        @tool
        async def get_job_market_intel(
            user_id: str,
            target_role: str,
            location: str = "United States",
        ) -> dict:
            """Get real-time job market intelligence for a target role."""
            return await self.job_market_agent.get_market_intelligence(
                user_id=user_id,
                target_role=target_role,
                location=location,
            )

        @tool
        async def enroll_in_courses(
            user_id: str,
            auto_approve_under_usd: float = 20.0,
        ) -> dict:
            """Automatically enroll learner in recommended courses via Nova Act."""
            state = await self._load_state(user_id)
            if not state.learning_path:
                return {"error": "Learning path required before enrollment"}

            results = await self.enrollment_agent.process_enrollment_queue(
                user_id=user_id,
                enrollment_queue=state.learning_path.get_enrollment_queue(),
                auto_approve_under_usd=auto_approve_under_usd,
            )
            state.enrollment_results = results
            state.stage = LearnerJourneyStage.ENROLLED
            await self._save_state(state)
            return {
                "enrolled_count": sum(
                    1 for r in results if r["status"] == "completed"
                ),
                "pending_review": sum(
                    1 for r in results if r["status"] == "requires_review"
                ),
                "total_cost_usd": sum(r.get("cost_usd", 0) for r in results),
            }

        self.strands_agent = Agent(
            model=self.strands_model,
            system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
            tools=[
                analyze_skills_gap,
                build_learning_path,
                get_job_market_intel,
                enroll_in_courses,
            ],
        )

    async def process_coaching_completion(
        self,
        user_id: str,
        coaching_profile: dict,
    ) -> dict:
        """
        Triggered when a voice coaching session ends.
        Kicks off the autonomous agent pipeline:
          1. Store coaching profile
          2. Run skills gap analysis
          3. Build learning path
          4. Trigger enrollment
          5. Surface results to dashboard
        """
        logger.info(f"Processing coaching completion for user {user_id}")

        # Load or create state
        state = await self._load_state(user_id)
        state.coaching_profile = coaching_profile
        state.stage = LearnerJourneyStage.COACHING_COMPLETE
        await self._save_state(state)

        # Run the full pipeline concurrently where possible
        target_role = self._extract_target_role(coaching_profile)
        aspirations = coaching_profile.get("aspirations", [])

        # Step 1: Parallel — Gap analysis + Job market intel
        gap_task = self.skills_gap_agent.analyze_gaps(
            user_id=user_id,
            skills_profile=coaching_profile,
            target_role=target_role,
        )
        market_task = self.job_market_agent.get_market_intelligence(
            user_id=user_id,
            target_role=target_role,
        )

        gap_report, market_intel = await asyncio.gather(
            gap_task, market_task, return_exceptions=True
        )

        if isinstance(gap_report, Exception):
            logger.error(f"Gap analysis failed for {user_id}: {gap_report}")
            return {"error": str(gap_report), "stage": state.stage.value}

        state.gap_report = gap_report
        state.stage = LearnerJourneyStage.GAP_ANALYSIS_COMPLETE
        await self._save_state(state)

        # Step 2: Build learning path
        learning_path = await self.learning_path_agent.build_learning_path(
            gap_report=gap_report
        )
        state.learning_path = learning_path
        state.stage = LearnerJourneyStage.LEARNING_PATH_ACTIVE
        await self._save_state(state)

        # Step 3: Auto-enroll (fire and forget — don't block dashboard)
        asyncio.create_task(
            self._auto_enroll_background(user_id, learning_path)
        )

        return {
            "user_id": user_id,
            "stage": state.stage.value,
            "gap_report": {
                "career_readiness_score": gap_report.career_readiness_score,
                "urgent_gaps": gap_report.urgent_gaps,
                "gap_summary": gap_report.gap_summary,
                "target_role": target_role,
            },
            "learning_path": {
                "total_weeks": learning_path.total_weeks,
                "path_summary": learning_path.path_summary,
                "estimated_salary_increase": learning_path.estimated_salary_increase,
                "total_cost_usd": learning_path.total_cost_usd,
            },
            "market_intel": market_intel if not isinstance(market_intel, Exception) else {},
        }

    async def run_strands_query(
        self, user_id: str, query: str
    ) -> str:
        """
        Execute a freeform agent query through the Strands orchestrator.
        Used for dashboard chat interface and ad-hoc agent invocations.
        """
        state = await self._load_state(user_id)
        response = await self.strands_agent.invoke_async(
            f"User {user_id} (stage: {state.stage.value}): {query}",
            context={"user_state": str(state)},
        )
        return str(response)

    async def _auto_enroll_background(
        self, user_id: str, learning_path: LearningPath
    ) -> None:
        """Background task: auto-enroll learner in all queued courses."""
        try:
            results = await self.enrollment_agent.process_enrollment_queue(
                user_id=user_id,
                enrollment_queue=learning_path.get_enrollment_queue(),
                auto_approve_under_usd=25.0,
            )
            state = await self._load_state(user_id)
            state.enrollment_results = results
            state.stage = LearnerJourneyStage.ENROLLED
            await self._save_state(state)
            logger.info(
                f"Auto-enrollment complete for {user_id}: "
                f"{sum(1 for r in results if r['status'] == 'completed')} enrolled"
            )
        except Exception as e:
            logger.error(f"Auto-enrollment failed for {user_id}: {e}")

    def _extract_target_role(self, profile: dict) -> str:
        """Extract the primary target role from coaching profile."""
        aspirations = profile.get("aspirations", [])
        if aspirations:
            return aspirations[0]
        # Infer from skills and confidence patterns
        skills = profile.get("detected_skills", [])
        if "machine learning" in [s.lower() for s in skills]:
            return "Machine Learning Engineer"
        if "data" in " ".join(skills).lower():
            return "Data Engineer"
        return "Software Engineer"  # Safe default

    async def _load_state(self, user_id: str) -> OrchestratorState:
        """Load learner state from DynamoDB."""
        try:
            raw = await self.db.get_item(
                table=settings.dynamodb_table_users,
                key={"user_id": user_id},
            )
            if raw:
                return OrchestratorState(
                    user_id=user_id,
                    stage=LearnerJourneyStage(raw.get("stage", "onboarding")),
                    coaching_profile=raw.get("coaching_profile"),
                )
        except Exception as e:
            logger.warning(f"Could not load state for {user_id}: {e}")
        return OrchestratorState(user_id=user_id)

    async def _save_state(self, state: OrchestratorState) -> None:
        """Persist learner state to DynamoDB."""
        state.last_updated = datetime.utcnow().isoformat()
        try:
            await self.db.put_item(
                table=settings.dynamodb_table_users,
                item={
                    "user_id": state.user_id,
                    "stage": state.stage.value,
                    "coaching_profile": state.coaching_profile or {},
                    "last_updated": state.last_updated,
                },
            )
        except Exception as e:
            logger.error(f"Failed to save state for {state.user_id}: {e}")