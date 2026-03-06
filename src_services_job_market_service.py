"""
SkillForge AI — Job Market Data Service
Abstracts job market data sources: LinkedIn, Indeed, and fallback synthetic data.
"""

import logging
import random
from typing import Optional

import httpx

from src.config import settings

logger = logging.getLogger(__name__)


class JobMarketService:
    """
    Provides job market data from multiple sources.
    Implements graceful fallback to synthetic data when API keys are not configured.
    """

    def __init__(self):
        self.http = httpx.AsyncClient(timeout=30.0)

    async def get_role_requirements(
        self,
        role: str,
        location: str = "United States",
        company: Optional[str] = None,
    ) -> dict:
        """Fetch job requirements for a target role from the market."""
        # Try LinkedIn API first
        if settings.linkedin_api_key:
            try:
                return await self._fetch_linkedin_requirements(role, location)
            except Exception as e:
                logger.warning(f"LinkedIn API failed, using synthetic data: {e}")

        # Fallback to synthetic but realistic market data
        return self._generate_synthetic_requirements(role, location)

    async def get_salary_benchmarks(
        self, role: str, location: str
    ) -> dict:
        """Fetch salary benchmark data for a role/location combination."""
        if settings.indeed_api_key:
            try:
                return await self._fetch_indeed_salaries(role, location)
            except Exception as e:
                logger.warning(f"Indeed API failed, using synthetic data: {e}")

        return self._generate_synthetic_salary(role, location)

    async def get_skill_demand(self, skill: str, role: str) -> dict:
        """Get current demand metrics for a specific skill."""
        # Synthetic demand data calibrated to 2025 market realities
        base_demand = {
            "Python": 95, "AWS": 88, "Kubernetes": 82, "dbt": 71,
            "Apache Spark": 79, "Apache Kafka": 74, "LangChain": 68,
            "Amazon Bedrock": 65, "PyTorch": 77, "MLflow": 63,
            "Terraform": 80, "Strands Agents": 55, "Amazon Nova": 60,
        }
        base = base_demand.get(skill, random.randint(40, 70))
        change_30d = random.uniform(-5, 15)

        return {
            "skill": skill,
            "demand_score": base,
            "demand_change_30d": round(change_30d, 2),
            "posting_count": int(base * 150),
            "salary_premium": int(base * 180),
            "trend": "rising" if change_30d > 2 else ("declining" if change_30d < -2 else "stable"),
        }

    async def _fetch_linkedin_requirements(
        self, role: str, location: str
    ) -> dict:
        """Fetch job requirements from LinkedIn Jobs API."""
        response = await self.http.get(
            "https://api.linkedin.com/v2/jobSearch",
            headers={"Authorization": f"Bearer {settings.linkedin_api_key}"},
            params={"keywords": role, "location": location, "count": 25},
        )
        response.raise_for_status()
        data = response.json()

        skills = []
        for job in data.get("elements", []):
            skills.extend(job.get("skills", {}).get("values", []))

        return {
            "role_title": role,
            "required_skills": list(set(skills))[:15],
            "preferred_skills": [],
            "experience_level": "mid",
            "responsibilities": [],
            "salary_benchmarks": {},
        }

    async def _fetch_indeed_salaries(self, role: str, location: str) -> dict:
        """Fetch salary data from Indeed API."""
        response = await self.http.get(
            "https://api.indeed.com/ads/apisearch",
            params={
                "publisher": settings.indeed_api_key,
                "q": role,
                "l": location,
                "format": "json",
            },
        )
        response.raise_for_status()
        return response.json().get("salaryData", self._generate_synthetic_salary(role, location))

    def _generate_synthetic_requirements(self, role: str, location: str) -> dict:
        """Generate realistic synthetic job requirements for demo purposes."""
        role_lower = role.lower()

        skills_map = {
            "data engineer": {
                "required": ["Python", "SQL", "Apache Spark", "Airflow", "dbt", "AWS"],
                "preferred": ["Apache Kafka", "Snowflake", "Databricks", "Scala"],
            },
            "ml engineer": {
                "required": ["Python", "PyTorch", "TensorFlow", "MLflow", "Docker"],
                "preferred": ["Kubeflow", "AWS SageMaker", "Feature Store", "LLMs"],
            },
            "ai engineer": {
                "required": ["Python", "Amazon Bedrock", "LangChain", "RAG", "AWS"],
                "preferred": ["Strands Agents", "Amazon Nova", "Vector Databases", "Fine-tuning"],
            },
            "devops engineer": {
                "required": ["Kubernetes", "Docker", "Terraform", "AWS", "CI/CD"],
                "preferred": ["Istio", "ArgoCD", "Prometheus", "Site Reliability Engineering"],
            },
        }

        matched = next(
            (v for k, v in skills_map.items() if k in role_lower),
            {"required": ["Python", "AWS", "SQL", "Docker", "Git"],
             "preferred": ["Kubernetes", "Terraform", "System Design"]},
        )

        return {
            "role_title": role,
            "location": location,
            "required_skills": matched["required"],
            "preferred_skills": matched["preferred"],
            "experience_level": "mid",
            "responsibilities": [
                f"Design and build scalable {role.lower()} systems",
                "Collaborate with cross-functional teams",
                "Mentor junior engineers",
                "Drive technical roadmap decisions",
            ],
            "salary_benchmarks": self._generate_synthetic_salary(role, location),
        }

    def _generate_synthetic_salary(self, role: str, location: str) -> dict:
        """Generate realistic salary data calibrated to 2025 market rates."""
        base_salaries = {
            "data engineer": 145000,
            "ml engineer": 165000,
            "ai engineer": 175000,
            "devops engineer": 140000,
            "software engineer": 135000,
            "backend engineer": 140000,
        }

        location_multipliers = {
            "san francisco": 1.35, "new york": 1.25, "seattle": 1.20,
            "austin": 1.05, "remote": 1.10, "united states": 1.0,
        }

        role_key = next(
            (k for k in base_salaries if k in role.lower()),
            "software engineer",
        )
        location_key = next(
            (k for k in location_multipliers if k in location.lower()),
            "united states",
        )

        base = base_salaries[role_key]
        multiplier = location_multipliers[location_key]
        adjusted = int(base * multiplier)

        return {
            "avg_salary_usd": adjusted,
            "min": int(adjusted * 0.75),
            "p50": adjusted,
            "p75": int(adjusted * 1.20),
            "max": int(adjusted * 1.55),
            "currency": "USD",
            "period": "annual",
        }

    async def close(self):
        await self.http.aclose()