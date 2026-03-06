"""SkillForge AI — Skills API Routes"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from src.agents.skills_gap_agent import SkillsGapAgent
from src.services.skills_graph import SkillsGraphService
from src.services.portfolio_analyzer import PortfolioAnalyzer
from src.database.dynamodb import DynamoDBClient
from src.config import settings

router = APIRouter()
skills_gap_agent = SkillsGapAgent()
skills_graph = SkillsGraphService()
portfolio_analyzer = PortfolioAnalyzer()
db = DynamoDBClient()


class SkillsAnalysisRequest(BaseModel):
    user_id: str
    skills_profile: dict
    target_role: str
    target_location: str = "United States"
    target_company: Optional[str] = None


class PortfolioAnalysisRequest(BaseModel):
    user_id: str
    github_url: Optional[str] = None
    resume_base64: Optional[str] = None
    portfolio_url: Optional[str] = None


@router.get("/{user_id}")
async def get_skills_profile(user_id: str):
    """Get a learner's complete skills profile."""
    profile = await db.get_item(
        table=settings.dynamodb_table_users,
        key={"user_id": user_id},
    )
    if not profile:
        raise HTTPException(status_code=404, detail="User profile not found")
    return profile


@router.post("/analyze")
async def analyze_skills_gap(request: SkillsAnalysisRequest):
    """
    Run a full skills gap analysis against live job market data.
    Returns prioritized gap report with salary impact projections.
    """
    report = await skills_gap_agent.analyze_gaps(
        user_id=request.user_id,
        skills_profile=request.skills_profile,
        target_role=request.target_role,
        target_location=request.target_location,
        target_company=request.target_company,
    )

    # Persist report to DynamoDB
    await db.update_item(
        table=settings.dynamodb_table_users,
        key={"user_id": request.user_id},
        updates={
            "gap_report": {
                "career_readiness_score": report.career_readiness_score,
                "urgent_gaps": report.urgent_gaps,
                "gap_summary": report.gap_summary,
                "target_role": report.target_role,
                "generated_at": report.generated_at,
            }
        },
    )

    return {
        "user_id": request.user_id,
        "target_role": report.target_role,
        "career_readiness_score": report.career_readiness_score,
        "gap_summary": report.gap_summary,
        "urgent_gaps": report.urgent_gaps,
        "skills_inventory": report.skills_inventory,
        "competitive_advantage_skills": report.competitive_advantage_skills,
        "market_positioning": report.market_positioning,
        "semantic_similarity": report.semantic_similarity_to_target,
    }


@router.post("/portfolio/analyze")
async def analyze_portfolio(request: PortfolioAnalysisRequest):
    """
    Analyze a learner's portfolio using Nova multimodal embeddings.
    Extracts demonstrated skills from GitHub, PDF resume, or portfolio site.
    """
    analysis = await portfolio_analyzer.analyze(
        user_id=request.user_id,
        github_url=request.github_url,
        resume_base64=request.resume_base64,
        portfolio_url=request.portfolio_url,
    )
    return analysis


@router.get("/graph/roles/{role}")
async def get_role_skills(role: str):
    """Get required skills for a target role from the skills graph."""
    skills = await skills_graph.get_skills_for_role(role)
    return {"role": role, "skills": skills}


@router.get("/graph/related/{skill}")
async def get_related_skills(skill: str, top_k: int = 10):
    """Get semantically related skills for a given skill."""
    related = await skills_graph.get_related_skills(skill=skill, top_k=top_k)
    return {"skill": skill, "related_skills": related}