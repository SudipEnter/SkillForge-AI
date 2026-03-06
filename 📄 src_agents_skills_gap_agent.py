"""
SkillForge AI — Skills Gap Analysis Agent
Powered by Nova 2 Lite + Nova Multimodal Embeddings

Analyzes learner skills profiles against live job market requirements
to produce prioritized, impact-ranked skills gap reports.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

from src.models.nova_lite import NovaLiteClient
from src.models.nova_embeddings import NovaEmbeddingsClient
from src.services.job_market_service import JobMarketService
from src.services.skills_graph import SkillsGraphService

logger = logging.getLogger(__name__)

SKILLS_GAP_SYSTEM_PROMPT = """You are SkillForge AI's Skills Gap Analysis Agent.
Your role is to analyze a learner's skills profile against target job market 
requirements and produce a precise, actionable gap analysis.

Given:
- The learner's current skills with confidence levels
- Live job market data for their target role and location  
- Current salary benchmarks by skill

Your output must be valid JSON with this exact structure:
{
  "gap_summary": "2-3 sentence executive summary of the learner's position",
  "career_readiness_score": <0-100 integer>,
  "skills_inventory": [
    {
      "skill": "<skill name>",
      "current_level": "none|beginner|intermediate|advanced|expert",
      "market_demand": "declining|stable|growing|high_demand|critical",
      "priority_rank": <1-based integer>,
      "salary_impact_usd_annual": <estimated annual salary increase from acquiring this skill>,
      "time_to_competency_weeks": <realistic weeks to reach job-ready level>,
      "rationale": "<why this skill matters for their specific target role>"
    }
  ],
  "competitive_advantage_skills": ["<skills they have that are above market average>"],
  "urgent_gaps": ["<top 3 skills to acquire immediately>"],
  "market_positioning": "<how competitive they are vs. average applicant for target role>"
}

Be specific, data-driven, and honest about skill gaps without being discouraging.
Always acknowledge existing strengths before addressing gaps."""


@dataclass
class SkillsGapReport:
    """Complete skills gap analysis report for a learner."""
    user_id: str
    target_role: str
    target_location: str
    gap_summary: str
    career_readiness_score: int
    skills_inventory: list[dict]
    competitive_advantage_skills: list[str]
    urgent_gaps: list[str]
    market_positioning: str
    semantic_similarity_to_target: float
    generated_at: str = field(
        default_factory=lambda: __import__("datetime").datetime.utcnow().isoformat()
    )


class SkillsGapAgent:
    """
    Analyzes learner skills profiles against job market requirements.

    Combines:
    - Nova 2 Lite reasoning for structured gap analysis
    - Nova Embeddings for semantic skills-to-job matching
    - Live job market data from the JobMarketService
    - Skills knowledge graph for competency depth analysis
    """

    def __init__(self):
        self.nova_lite = NovaLiteClient()
        self.nova_embeddings = NovaEmbeddingsClient()
        self.job_market = JobMarketService()
        self.skills_graph = SkillsGraphService()

    async def analyze_gaps(
        self,
        user_id: str,
        skills_profile: dict,
        target_role: str,
        target_location: str = "United States",
        target_company: Optional[str] = None,
    ) -> SkillsGapReport:
        """
        Execute a complete skills gap analysis for a learner.

        Args:
            user_id: Learner identifier
            skills_profile: Raw skills profile from coaching session
            target_role: Target job title (e.g., "Senior Data Engineer")
            target_location: Geographic market (e.g., "San Francisco, CA")
            target_company: Optional specific company for targeted analysis

        Returns:
            Complete SkillsGapReport with prioritized gap recommendations
        """
        logger.info(
            f"Starting skills gap analysis for user {user_id}: "
            f"{target_role} in {target_location}"
        )

        # Step 1: Fetch live job market data for the target role
        market_data = await self.job_market.get_role_requirements(
            role=target_role,
            location=target_location,
            company=target_company,
        )

        # Step 2: Compute semantic similarity between learner profile and target role
        learner_embedding = await self.nova_embeddings.embed_skills_profile(
            skills_profile
        )
        job_embedding = await self.nova_embeddings.embed_text(
            self._market_data_to_text(market_data)
        )
        semantic_similarity = await self.nova_embeddings.compute_semantic_similarity(
            learner_embedding, job_embedding
        )

        # Step 3: Get all candidate skills from the skills graph
        candidate_skills = await self.skills_graph.get_skills_for_role(target_role)
        skill_embeddings = {
            skill["name"]: await self.nova_embeddings.embed_text(skill["description"])
            for skill in candidate_skills[:50]  # Top 50 candidate skills
        }

        # Step 4: Semantic skills gap identification via embeddings
        semantic_gaps = await self.nova_embeddings.find_skills_gaps(
            learner_embedding=learner_embedding,
            job_embedding=job_embedding,
            skill_embeddings=skill_embeddings,
            top_k=15,
        )

        # Step 5: Nova 2 Lite structured reasoning for the final gap report
        gap_report_raw = await self.nova_lite.reason(
            system_prompt=SKILLS_GAP_SYSTEM_PROMPT,
            user_message=(
                f"Analyze the skills gap for this learner targeting "
                f"the role of {target_role} in {target_location}."
            ),
            context={
                "learner_skills_profile": skills_profile,
                "target_role": target_role,
                "target_location": target_location,
                "target_company": target_company,
                "job_market_data": market_data,
                "semantic_gap_analysis": semantic_gaps,
                "semantic_similarity_score": round(semantic_similarity, 3),
                "market_salary_benchmarks": market_data.get("salary_benchmarks", {}),
            },
            temperature=0.2,
            response_format="json",
        )

        logger.info(
            f"Skills gap analysis complete for {user_id}. "
            f"Career readiness: {gap_report_raw.get('career_readiness_score', 0)}/100. "
            f"Semantic similarity: {semantic_similarity:.2%}"
        )

        return SkillsGapReport(
            user_id=user_id,
            target_role=target_role,
            target_location=target_location,
            gap_summary=gap_report_raw["gap_summary"],
            career_readiness_score=gap_report_raw["career_readiness_score"],
            skills_inventory=gap_report_raw["skills_inventory"],
            competitive_advantage_skills=gap_report_raw["competitive_advantage_skills"],
            urgent_gaps=gap_report_raw["urgent_gaps"],
            market_positioning=gap_report_raw["market_positioning"],
            semantic_similarity_to_target=round(semantic_similarity, 4),
        )

    def _market_data_to_text(self, market_data: dict) -> str:
        """Convert market data to text for embedding generation."""
        required_skills = ", ".join(market_data.get("required_skills", []))
        preferred_skills = ", ".join(market_data.get("preferred_skills", []))
        return (
            f"Role: {market_data.get('role_title', '')}. "
            f"Required skills: {required_skills}. "
            f"Preferred skills: {preferred_skills}. "
            f"Experience level: {market_data.get('experience_level', 'mid')}. "
            f"Key responsibilities: "
            f"{'. '.join(market_data.get('responsibilities', [])[:5])}"
        )