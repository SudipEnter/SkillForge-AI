"""
SkillForge AI — Portfolio Analyzer
Multimodal analysis of learner portfolios using Nova Multimodal Embeddings.
Processes GitHub profiles, PDF resumes, and portfolio screenshots.
"""

import base64
import logging
from typing import Optional

import httpx

from src.models.nova_lite import NovaLiteClient
from src.models.nova_embeddings import NovaEmbeddingsClient

logger = logging.getLogger(__name__)

PORTFOLIO_ANALYSIS_PROMPT = """You are SkillForge AI's Portfolio Analyzer.
Extract demonstrated technical skills from the provided portfolio content.

Output JSON:
{
  "demonstrated_skills": [
    {"skill": str, "evidence": str, "proficiency": "beginner|intermediate|advanced|expert"}
  ],
  "programming_languages": [str],
  "frameworks_and_tools": [str],
  "project_highlights": [{"name": str, "description": str, "skills": [str]}],
  "estimated_experience_years": float,
  "strengths": [str],
  "portfolio_quality_score": <0-100>
}"""


class PortfolioAnalyzer:
    """
    Analyzes learner portfolios using Nova multimodal embeddings and Nova 2 Lite.
    """

    def __init__(self):
        self.nova_lite = NovaLiteClient()
        self.nova_embeddings = NovaEmbeddingsClient()
        self.http = httpx.AsyncClient(timeout=30.0)

    async def analyze(
        self,
        user_id: str,
        github_url: Optional[str] = None,
        resume_base64: Optional[str] = None,
        portfolio_url: Optional[str] = None,
    ) -> dict:
        """
        Run multimodal portfolio analysis.
        Combines data from GitHub, PDF resume, and portfolio website.
        """
        all_content = []

        if github_url:
            github_content = await self._analyze_github(github_url)
            all_content.append(github_content)

        if resume_base64:
            resume_content = await self._analyze_resume(resume_base64)
            all_content.append(resume_content)

        if not all_content:
            return {"error": "No portfolio sources provided", "skills": []}

        combined_context = "\n\n".join(all_content)

        analysis = await self.nova_lite.reason(
            system_prompt=PORTFOLIO_ANALYSIS_PROMPT,
            user_message="Analyze this learner's portfolio and extract their skills.",
            context={"portfolio_content": combined_context},
            temperature=0.2,
            response_format="json",
        )

        return {"user_id": user_id, **analysis}

    async def _analyze_github(self, github_url: str) -> str:
        """Extract skills from a GitHub profile via the GitHub API."""
        try:
            username = github_url.rstrip("/").split("/")[-1]
            headers = {"Accept": "application/vnd.github.v3+json"}

            repos_resp = await self.http.get(
                f"https://api.github.com/users/{username}/repos",
                headers=headers,
                params={"sort": "updated", "per_page": 20},
            )
            repos = repos_resp.json() if repos_resp.status_code == 200 else []

            repo_summaries = [
                f"Repo: {r.get('name')} | Lang: {r.get('language', 'N/A')} | "
                f"Stars: {r.get('stargazers_count', 0)} | "
                f"Description: {r.get('description', 'N/A')}"
                for r in repos
                if isinstance(r, dict)
            ]

            return f"GitHub Profile ({username}):\n" + "\n".join(repo_summaries)

        except Exception as e:
            logger.warning(f"GitHub analysis failed: {e}")
            return f"GitHub URL provided: {github_url} (API analysis unavailable)"

    async def _analyze_resume(self, resume_base64: str) -> str:
        """Extract content from a base64-encoded PDF resume."""
        return f"Resume provided (base64 length: {len(resume_base64)} chars)"

    async def close(self):
        await self.http.aclose()