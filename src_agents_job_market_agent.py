"""
SkillForge AI — Job Market Intelligence Agent
Real-time job market analysis powered by Nova 2 Lite reasoning.

Provides:
- Live demand signals for skills and roles
- Salary benchmarks by skill, level, and location
- Company hiring trend analysis
- Skills gaining / losing market velocity
- Remote work availability by role
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from src.models.nova_lite import NovaLiteClient
from src.models.nova_embeddings import NovaEmbeddingsClient
from src.services.job_market_service import JobMarketService
from src.database.opensearch_client import OpenSearchClient

logger = logging.getLogger(__name__)

JOB_MARKET_SYSTEM_PROMPT = """You are SkillForge AI's Job Market Intelligence Agent.
Analyze real-time job market data and produce actionable career intelligence.

Given job postings, salary data, and skills demand metrics, output JSON:
{
  "market_summary": "2-sentence market overview for this role",
  "demand_level": "low|moderate|high|critical",
  "total_open_positions": <integer>,
  "avg_salary_usd": <annual USD>,
  "salary_range": {"min": <int>, "p50": <int>, "p75": <int>, "max": <int>},
  "top_hiring_companies": [{"company": str, "openings": int, "is_remote": bool}],
  "trending_skills": [{"skill": str, "demand_change_pct": float, "trend": "rising|stable|declining"}],
  "remote_percentage": <0-100 float>,
  "yoe_distribution": {"0-2": <pct>, "2-5": <pct>, "5-10": <pct>, "10+": <pct>},
  "time_to_hire_days": <integer>,
  "competition_level": "low|moderate|high|very_high",
  "insider_tip": "one actionable insight not visible from the raw data"
}"""


@dataclass
class MarketIntelligence:
    """Real-time job market intelligence for a target role."""
    role: str
    location: str
    market_summary: str
    demand_level: str
    total_open_positions: int
    avg_salary_usd: int
    salary_range: dict
    top_hiring_companies: list[dict]
    trending_skills: list[dict]
    remote_percentage: float
    yoe_distribution: dict
    time_to_hire_days: int
    competition_level: str
    insider_tip: str
    generated_at: str = field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )


class JobMarketAgent:
    """
    Provides real-time job market intelligence using Nova 2 Lite reasoning
    over live job posting data indexed in OpenSearch.
    """

    def __init__(self):
        self.nova_lite = NovaLiteClient()
        self.nova_embeddings = NovaEmbeddingsClient()
        self.job_market_service = JobMarketService()
        self.opensearch = OpenSearchClient()

    async def get_market_intelligence(
        self,
        user_id: str,
        target_role: str,
        location: str = "United States",
        company: Optional[str] = None,
    ) -> dict:
        """
        Generate comprehensive job market intelligence for a role.

        Args:
            user_id: Learner identifier
            target_role: Job title to analyze
            location: Geographic market
            company: Optional specific company focus

        Returns:
            MarketIntelligence as dict
        """
        logger.info(f"Running market intelligence: {target_role} in {location}")

        # Fetch live job postings via semantic search
        role_embedding = await self.nova_embeddings.embed_text(
            f"{target_role} job requirements and qualifications"
        )
        job_postings = await self.opensearch.semantic_search(
            index="job-embeddings",
            query_vector=role_embedding,
            filters={"location": location},
            top_k=50,
        )

        # Fetch salary data from job market service
        salary_data = await self.job_market_service.get_salary_benchmarks(
            role=target_role,
            location=location,
        )

        # Nova 2 Lite synthesizes market intelligence
        intel_raw = await self.nova_lite.reason(
            system_prompt=JOB_MARKET_SYSTEM_PROMPT,
            user_message=(
                f"Analyze the job market for {target_role} in {location}. "
                f"Focus on: current demand, salary trends, and competitive landscape."
                + (f" Company focus: {company}" if company else "")
            ),
            context={
                "job_postings_sample": job_postings[:20],
                "salary_data": salary_data,
                "total_postings_found": len(job_postings),
                "target_role": target_role,
                "location": location,
            },
            temperature=0.2,
            response_format="json",
        )

        return {
            "role": target_role,
            "location": location,
            **intel_raw,
        }

    async def get_skills_velocity(
        self, skills: list[str], role: str
    ) -> list[dict]:
        """
        Track which skills are gaining vs. losing market value.

        Returns ranked list of skills with velocity metrics.
        """
        velocity_data = []
        for skill in skills:
            market_data = await self.job_market_service.get_skill_demand(
                skill=skill, role=role
            )
            velocity_data.append({
                "skill": skill,
                "demand_change_30d": market_data.get("demand_change_30d", 0),
                "job_posting_count": market_data.get("posting_count", 0),
                "salary_premium_usd": market_data.get("salary_premium", 0),
                "trend": market_data.get("trend", "stable"),
            })

        return sorted(
            velocity_data,
            key=lambda x: x["demand_change_30d"],
            reverse=True,
        )

    async def find_matching_jobs(
        self,
        user_id: str,
        skills_profile: dict,
        target_role: str,
        min_salary: int = 0,
        remote_only: bool = False,
    ) -> list[dict]:
        """
        Find the most semantically matching job postings for a learner profile.
        Uses Nova embeddings for deep skills-to-job matching (not keyword matching).
        """
        profile_embedding = await self.nova_embeddings.embed_skills_profile(
            skills_profile
        )

        filters = {"role_category": target_role}
        if remote_only:
            filters["is_remote"] = True
        if min_salary:
            filters["salary_min_usd"] = min_salary

        matches = await self.opensearch.semantic_search(
            index="job-embeddings",
            query_vector=profile_embedding,
            filters=filters,
            top_k=20,
        )

        # Enrich with match percentage
        for job in matches:
            job["profile_match_pct"] = round(
                job.get("_score", 0) * 100, 1
            )

        return matches