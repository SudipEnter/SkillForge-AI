"""
SkillForge AI — Amazon Nova Multimodal Embeddings Integration
Semantic skills graph construction using state-of-the-art multimodal embeddings.

Handles:
- Text embeddings for skills, job descriptions, course content
- Image embeddings for portfolio screenshots, project images, certificates
- Document embeddings for PDFs (resumes, syllabi, research papers)
- Cross-modal semantic search (image query ↔ text results)
"""

import base64
import json
import logging
from enum import Enum
from pathlib import Path
from typing import Optional, Union

import boto3
import numpy as np
from botocore.config import Config

from src.config import settings

logger = logging.getLogger(__name__)


class EmbeddingType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    DOCUMENT = "document"
    MULTIMODAL = "multimodal"


class NovaEmbeddingsClient:
    """
    Amazon Nova Multimodal Embeddings client.

    Creates semantic vector representations of:
    - Skills and competency descriptions
    - Job posting requirements
    - Course curriculum content
    - Portfolio images and GitHub project pages
    - Resume documents and work samples
    """

    def __init__(self):
        self.client = boto3.client(
            service_name="bedrock-runtime",
            region_name=settings.aws_default_region,
            config=Config(
                connect_timeout=10,
                read_timeout=60,
                retries={"max_attempts": 3},
            ),
        )
        self.model_id = settings.nova_embed_model_id
        self.embedding_dim = settings.embedding_dimensions

    async def embed_text(self, text: str) -> list[float]:
        """
        Generate embedding vector for text content.

        Args:
            text: Skill description, job requirement, course objective, etc.

        Returns:
            1536-dimensional embedding vector
        """
        return await self._embed(
            input_data={"text": text},
            embedding_type=EmbeddingType.TEXT,
        )

    async def embed_image(
        self,
        image_source: Union[bytes, str, Path],
        caption: Optional[str] = None,
    ) -> list[float]:
        """
        Generate embedding vector for an image.
        Used for portfolio screenshots, project visualizations, certificates.

        Args:
            image_source: Raw bytes, file path, or base64-encoded string
            caption: Optional text description to guide the embedding
        """
        image_bytes = self._resolve_image_bytes(image_source)
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        input_data = {
            "image": {
                "format": "jpeg",  # or detect from magic bytes
                "source": {"bytes": image_b64},
            }
        }
        if caption:
            input_data["text"] = caption

        return await self._embed(
            input_data=input_data,
            embedding_type=EmbeddingType.IMAGE if not caption else EmbeddingType.MULTIMODAL,
        )

    async def embed_skills_profile(self, skills_profile: dict) -> list[float]:
        """
        Create a rich embedding for a learner's complete skills profile.
        Combines self-reported skills, confidence levels, and career context.

        Args:
            skills_profile: {
                "skills": [{"name": str, "confidence": str, "years": int}],
                "current_role": str,
                "target_role": str,
                "aspirations": [str],
            }

        Returns:
            Profile embedding vector for semantic matching against job requirements
        """
        # Construct a natural language representation for richer embedding
        profile_text = self._skills_profile_to_text(skills_profile)
        return await self.embed_text(profile_text)

    async def embed_job_posting(self, job_posting: dict) -> list[float]:
        """
        Embed a job posting for semantic matching against learner profiles.

        Args:
            job_posting: {
                "title": str,
                "company": str,
                "requirements": [str],
                "responsibilities": [str],
                "preferred_qualifications": [str],
            }
        """
        job_text = self._job_posting_to_text(job_posting)
        return await self.embed_text(job_text)

    async def embed_course(self, course: dict) -> list[float]:
        """
        Embed a learning resource for semantic skills matching.

        Args:
            course: {
                "title": str,
                "provider": str,
                "description": str,
                "learning_objectives": [str],
                "skills_taught": [str],
                "level": str,
                "duration_hours": float,
            }
        """
        course_text = self._course_to_text(course)
        return await self.embed_text(course_text)

    async def compute_semantic_similarity(
        self,
        embedding_a: list[float],
        embedding_b: list[float],
    ) -> float:
        """
        Compute cosine similarity between two embedding vectors.
        Returns a value between -1.0 and 1.0 (1.0 = identical).
        """
        vec_a = np.array(embedding_a)
        vec_b = np.array(embedding_b)

        dot_product = np.dot(vec_a, vec_b)
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return float(dot_product / (norm_a * norm_b))

    async def find_skills_gaps(
        self,
        learner_embedding: list[float],
        job_embedding: list[float],
        skill_embeddings: dict[str, list[float]],
        top_k: int = 10,
    ) -> list[dict]:
        """
        Identify top skills gaps by finding which individual skill embeddings
        would most increase the learner's semantic similarity to the target job.

        Args:
            learner_embedding: Current learner skills profile embedding
            job_embedding: Target job requirement embedding
            skill_embeddings: {skill_name: embedding} for candidate skills
            top_k: Number of top gap skills to return

        Returns:
            Ranked list of skills with semantic gap scores
        """
        current_similarity = await self.compute_semantic_similarity(
            learner_embedding, job_embedding
        )

        skill_impact_scores = []

        for skill_name, skill_embedding in skill_embeddings.items():
            # Simulate adding this skill to the learner's profile
            augmented_embedding = self._blend_embeddings(
                learner_embedding,
                skill_embedding,
                blend_weight=0.3,
            )
            new_similarity = await self.compute_semantic_similarity(
                augmented_embedding, job_embedding
            )
            impact = new_similarity - current_similarity
            skill_impact_scores.append({
                "skill": skill_name,
                "semantic_impact": round(impact, 4),
                "current_similarity": round(current_similarity, 4),
                "projected_similarity": round(new_similarity, 4),
            })

        # Sort by descending impact — highest-leverage skills first
        skill_impact_scores.sort(key=lambda x: x["semantic_impact"], reverse=True)
        return skill_impact_scores[:top_k]

    async def _embed(
        self, input_data: dict, embedding_type: EmbeddingType
    ) -> list[float]:
        """Core embedding API call to Nova multimodal embeddings model."""
        import asyncio

        request_body = {
            "inputType": embedding_type.value,
            "embeddingConfig": {
                "outputEmbeddingLength": self.embedding_dim,
                "normalize": True,
            },
            **input_data,
        }

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.client.invoke_model(
                modelId=self.model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(request_body),
            ),
        )

        response_body = json.loads(response["body"].read())
        return response_body["embedding"]

    def _blend_embeddings(
        self,
        base: list[float],
        addition: list[float],
        blend_weight: float = 0.3,
    ) -> list[float]:
        """Blend two embeddings to simulate skills augmentation."""
        base_arr = np.array(base)
        add_arr = np.array(addition)
        blended = (1 - blend_weight) * base_arr + blend_weight * add_arr
        # Re-normalize to unit sphere
        norm = np.linalg.norm(blended)
        return (blended / norm).tolist() if norm > 0 else blended.tolist()

    def _resolve_image_bytes(self, source: Union[bytes, str, Path]) -> bytes:
        if isinstance(source, bytes):
            return source
        if isinstance(source, Path) or (
            isinstance(source, str) and Path(source).exists()
        ):
            return Path(source).read_bytes()
        if isinstance(source, str):
            # Assume base64-encoded string
            return base64.b64decode(source)
        raise ValueError(f"Cannot resolve image source: {type(source)}")

    def _skills_profile_to_text(self, profile: dict) -> str:
        skills_desc = ". ".join([
            f"{s['name']} ({s.get('confidence', 'medium')} confidence, "
            f"{s.get('years', 1)} years)"
            for s in profile.get("skills", [])
        ])
        return (
            f"Professional Profile: {profile.get('current_role', 'Unknown Role')}. "
            f"Skills: {skills_desc}. "
            f"Career target: {profile.get('target_role', 'Not specified')}. "
            f"Aspirations: {', '.join(profile.get('aspirations', []))}."
        )

    def _job_posting_to_text(self, job: dict) -> str:
        requirements = ". ".join(job.get("requirements", []))
        preferred = ". ".join(job.get("preferred_qualifications", []))
        return (
            f"Job Title: {job.get('title', '')} at {job.get('company', '')}. "
            f"Requirements: {requirements}. "
            f"Preferred qualifications: {preferred}."
        )

    def _course_to_text(self, course: dict) -> str:
        objectives = ". ".join(course.get("learning_objectives", []))
        skills = ", ".join(course.get("skills_taught", []))
        return (
            f"Course: {course.get('title', '')} by {course.get('provider', '')}. "
            f"Level: {course.get('level', 'intermediate')}. "
            f"Skills taught: {skills}. "
            f"Learning objectives: {objectives}."
        )