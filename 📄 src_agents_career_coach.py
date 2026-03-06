"""
SkillForge AI — Career Coach Agent
Structures the post-voice-session coaching data into an actionable profile.

Works alongside Nova 2 Sonic (voice layer) to:
  1. Extract structured skills data from raw conversation transcripts
  2. Build a rich learner profile from multi-turn dialogue
  3. Generate empathetic coaching insights
  4. Produce a career_profile dict consumed by the Orchestrator
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from src.models.nova_lite import NovaLiteClient
from src.config import settings

logger = logging.getLogger(__name__)

COACHING_EXTRACTION_PROMPT = """You are SkillForge AI's Career Coach Analyst.
Extract a structured learner profile from this coaching session transcript.

Output STRICT JSON:
{
  "name": str,
  "years_of_experience": float,
  "current_role": str,
  "current_company": str,
  "detected_skills": [str],
  "skill_levels": {"skill_name": "beginner|intermediate|advanced|expert"},
  "aspirations": [str],
  "target_roles": [str],
  "target_companies": [str],
  "blockers": [str],
  "motivations": [str],
  "learning_style": "visual|auditory|reading|kinesthetic|mixed",
  "weekly_hours_available": float,
  "weekly_budget_usd": float,
  "preferred_learning_platforms": [str],
  "geographic_preferences": [str],
  "remote_preference": "remote|hybrid|onsite|flexible",
  "urgency": "exploratory|active|urgent",
  "coaching_notes": str,
  "confidence_score": float
}"""

COACHING_INSIGHTS_PROMPT = """You are an empathetic career coach specializing in tech reskilling.
Based on this learner profile, generate warm, actionable coaching insights.

Output JSON:
{
  "opening_insight": "One sentence that validates their journey",
  "key_strengths": [str],
  "growth_opportunities": [str],
  "recommended_target_role": str,
  "salary_uplift_potential": str,
  "time_to_market_weeks": int,
  "motivational_message": str,
  "first_three_steps": [str]
}"""


@dataclass
class CareerProfile:
    """Structured learner career profile extracted from coaching session."""
    user_id: str
    name: str
    current_role: str
    years_of_experience: float
    detected_skills: list[str]
    skill_levels: dict[str, str]
    aspirations: list[str]
    target_roles: list[str]
    target_companies: list[str]
    blockers: list[str]
    motivations: list[str]
    learning_style: str
    weekly_hours_available: float
    weekly_budget_usd: float
    preferred_learning_platforms: list[str]
    geographic_preferences: list[str]
    remote_preference: str
    urgency: str
    coaching_notes: str
    confidence_score: float
    insights: Optional[dict] = None
    created_at: str = field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


class CareerCoachAgent:
    """
    Post-session career coach agent.

    Takes raw Nova 2 Sonic transcripts → produces structured CareerProfile
    that feeds into the Orchestrator pipeline.
    """

    def __init__(self):
        self.nova_lite = NovaLiteClient()

    async def process_session_transcript(
        self,
        user_id: str,
        transcript: str,
        session_metadata: Optional[dict] = None,
    ) -> CareerProfile:
        """
        Main entry point: convert a raw voice coaching transcript
        into a structured, actionable CareerProfile.

        Args:
            user_id: Learner ID
            transcript: Full conversation transcript from Nova 2 Sonic
            session_metadata: Optional metadata (duration, turn count, etc.)

        Returns:
            CareerProfile with all extracted fields populated
        """
        logger.info(f"Processing coaching transcript for user {user_id}")

        # Step 1: Extract structured profile via Nova 2 Lite
        profile_data = await self.nova_lite.reason(
            system_prompt=COACHING_EXTRACTION_PROMPT,
            user_message=(
                "Extract the learner profile from this coaching session transcript."
            ),
            context={
                "transcript": transcript,
                "session_metadata": session_metadata or {},
            },
            temperature=0.15,  # Low temp for reliable extraction
            response_format="json",
        )

        # Step 2: Generate empathetic coaching insights
        insights = await self.nova_lite.reason(
            system_prompt=COACHING_INSIGHTS_PROMPT,
            user_message="Generate coaching insights for this learner profile.",
            context={"learner_profile": profile_data},
            temperature=0.55,  # Slightly higher for creativity/warmth
            response_format="json",
        )

        # Step 3: Hydrate the CareerProfile dataclass
        profile = CareerProfile(
            user_id=user_id,
            name=profile_data.get("name", ""),
            current_role=profile_data.get("current_role", ""),
            years_of_experience=float(profile_data.get("years_of_experience", 0)),
            detected_skills=profile_data.get("detected_skills", []),
            skill_levels=profile_data.get("skill_levels", {}),
            aspirations=profile_data.get("aspirations", []),
            target_roles=profile_data.get("target_roles", []),
            target_companies=profile_data.get("target_companies", []),
            blockers=profile_data.get("blockers", []),
            motivations=profile_data.get("motivations", []),
            learning_style=profile_data.get("learning_style", "mixed"),
            weekly_hours_available=float(
                profile_data.get("weekly_hours_available", 12.0)
            ),
            weekly_budget_usd=float(profile_data.get("weekly_budget_usd", 50.0)),
            preferred_learning_platforms=profile_data.get(
                "preferred_learning_platforms", []
            ),
            geographic_preferences=profile_data.get("geographic_preferences", []),
            remote_preference=profile_data.get("remote_preference", "flexible"),
            urgency=profile_data.get("urgency", "active"),
            coaching_notes=profile_data.get("coaching_notes", ""),
            confidence_score=float(profile_data.get("confidence_score", 0.7)),
            insights=insights,
        )

        logger.info(
            f"Career profile built for {user_id}: "
            f"{len(profile.detected_skills)} skills detected, "
            f"confidence={profile.confidence_score:.2f}"
        )

        return profile

    async def generate_coaching_summary(
        self,
        profile: CareerProfile,
        gap_score: float,
        estimated_weeks: int,
    ) -> str:
        """
        Generate a personalized post-session coaching summary
        delivered to the learner via voice (Nova 2 Sonic) and email.
        """
        prompt = f"""You are an enthusiastic career coach delivering an inspiring 
session summary. Keep it under 150 words, warm, specific, and action-oriented.

Learner: {profile.name}
Current role: {profile.current_role}
Target role: {profile.target_roles[0] if profile.target_roles else 'their dream role'}
Career readiness: {gap_score:.0%}
Estimated weeks to job-ready: {estimated_weeks}
Top 3 gaps: {', '.join(profile.blockers[:3])}
Motivations: {', '.join(profile.motivations[:2])}

Deliver the summary now."""

        response = await self.nova_lite.reason(
            system_prompt="You are a warm, encouraging career coach.",
            user_message=prompt,
            temperature=0.65,
        )

        return response if isinstance(response, str) else str(response)

    async def adapt_coaching_style(
        self,
        profile: CareerProfile,
        coaching_history: list[dict],
    ) -> dict:
        """
        Adapt future coaching sessions based on learner history.
        Adjusts Nova 2 Sonic prompting based on learning style and progress.
        """
        adaptations = {
            "tone": "encouraging",
            "pacing": "moderate",
            "technical_depth": "intermediate",
            "check_in_frequency_days": 7,
            "preferred_session_length_minutes": 15,
        }

        if profile.urgency == "urgent":
            adaptations["check_in_frequency_days"] = 3
            adaptations["tone"] = "focused_and_energetic"

        if profile.learning_style == "visual":
            adaptations["prefer_diagrams"] = True
        elif profile.learning_style == "auditory":
            adaptations["extend_voice_explanations"] = True

        if len(coaching_history) > 5:
            adaptations["reduce_onboarding_questions"] = True
            adaptations["technical_depth"] = "advanced"

        return adaptations