"""
Amazon Nova Embeddings — Multimodal Skills & Portfolio Matching
Used by: SkillsGapAgent, OpenSearch vector indexing, portfolio analysis

Generates 1024-dimensional embeddings for:
  - Individual skills (to build the skills knowledge graph)
  - Complete learner profiles (for similarity-based job matching)
  - Portfolio artifacts (GitHub repos, resumes, projects)
  - Job descriptions (for semantic job-skill matching)
"""

import asyncio
import base64
import json
import logging
from functools import partial
from typing import Optional

import boto3
from botocore.config import Config

from src.config import settings

logger = logging.getLogger(__name__)


class NovaEmbeddingsClient:
    """
    Amazon Nova multimodal embeddings client.

    Supports both text-only and image+text embeddings, enabling
    SkillForge to match skills semantically rather than by keyword.

    Example: "Kafka" embedding will be close to "Apache Kafka",
    "distributed messaging", "event streaming" — enabling smart gap detection.
    """

    def __init__(self):
        self._client = boto3.client(
            "bedrock-runtime",
            region_name=settings.bedrock_region,
            config=Config(retries={"max_attempts": 3, "mode": "adaptive"}),
            aws_access_key_id=settings.aws_access_key_id or None,
            aws_secret_access_key=settings.aws_secret_access_key or None,
            aws_session_token=settings.aws_session_token or None,
        )
        self.model_id = settings.nova_embeddings_model_id
        self.dimensions = settings.embedding_dimensions

    async def _embed(self, payload: dict) -> list[float]:
        """Core embedding invocation — runs in thread pool."""
        loop = asyncio.get_event_loop()
        call = partial(
            self._client.invoke_model,
            modelId=self.model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload),
        )
        try:
            response = await loop.run_in_executor(None, call)
            result = json.loads(response["body"].read())
            return result.get("embedding", [0.0] * self.dimensions)
        except Exception as exc:
            logger.error(f"Nova Embeddings error: {exc}")
            return [0.0] * self.dimensions

    async def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a text string."""
        return await self._embed({"inputText": text[:8192]})  # Nova Embed text limit

    async def embed_multimodal(
        self,
        text: str,
        image_bytes: Optional[bytes] = None,
    ) -> list[float]:
        """
        Generate multimodal embedding from text + optional image.
        Used for portfolio screenshots, GitHub profile cards, certifications.
        """
        payload: dict = {"inputText": text}
        if image_bytes:
            payload["inputImage"] = base64.b64encode(image_bytes).decode()
        return await self._embed(payload)

    async def embed_skills_profile(self, profile: dict) -> list[float]:
        """
        Generate a unified embedding for a complete skills profile.
        Concatenates skills, experience, and context into a rich text
        representation before embedding — enabling semantic job matching.
        """
        skills = profile.get("detected_skills", [])
        role = profile.get("current_role", "")
        aspirations = profile.get("aspirations", [])
        experience = profile.get("years_of_experience", 0)

        text = (
            f"Professional profile: {role} with {experience} years of experience. "
            f"Technical skills: {', '.join(skills[:30])}. "
            f"Career aspirations: {', '.join(aspirations[:5])}."
        )
        return await self.embed_text(text)

    async def embed_job_description(self, jd: dict) -> list[float]:
        """Embed a job description for semantic skill matching."""
        text = (
            f"Job: {jd.get('title', '')} at {jd.get('company', '')}. "
            f"Required skills: {', '.join(jd.get('required_skills', []))}. "
            f"Description: {jd.get('description', '')[:2000]}"
        )
        return await self.embed_text(text)

    async def batch_embed(self, texts: list[str]) -> list[list[float]]:
        """
        Batch embed multiple texts concurrently.
        Respects rate limits via controlled concurrency.
        """
        semaphore = asyncio.Semaphore(settings.embedding_batch_size)

        async def embed_with_limit(text: str) -> list[float]:
            async with semaphore:
                return await self.embed_text(text)

        return await asyncio.gather(*[embed_with_limit(t) for t in texts])

    async def cosine_similarity(
        self,
        vec_a: list[float],
        vec_b: list[float],
    ) -> float:
        """Compute cosine similarity between two embedding vectors."""
        import math
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        mag_a = math.sqrt(sum(a ** 2 for a in vec_a))
        mag_b = math.sqrt(sum(b ** 2 for b in vec_b))
        if mag_a == 0 or mag_b == 0:
            return 0.0
        return dot / (mag_a * mag_b)