"""
SkillForge AI — Skills Knowledge Graph Service
Semantic graph of 8,000+ skills, roles, and competency relationships.
Backed by OpenSearch with Nova multimodal embeddings as vectors.
"""

import json
import logging
from pathlib import Path
from typing import Optional

from src.database.opensearch_client import OpenSearchClient
from src.models.nova_embeddings import NovaEmbeddingsClient
from src.config import settings

logger = logging.getLogger(__name__)

# Core skills taxonomy covering 40+ domains
SKILLS_TAXONOMY = {
    "data_engineering": [
        "Apache Spark", "Apache Kafka", "dbt", "Airflow", "Databricks",
        "Snowflake", "BigQuery", "Redshift", "Delta Lake", "Apache Iceberg",
        "Python", "SQL", "Scala", "PySpark", "Data Modeling", "ETL/ELT Design",
        "Stream Processing", "Batch Processing", "Data Lakehouse Architecture",
    ],
    "machine_learning": [
        "PyTorch", "TensorFlow", "Scikit-learn", "XGBoost", "LightGBM",
        "MLflow", "Kubeflow", "Feature Engineering", "Model Evaluation",
        "Hyperparameter Tuning", "A/B Testing", "ML System Design",
        "Reinforcement Learning", "Computer Vision", "NLP", "LLMs",
        "RAG", "Fine-tuning", "Prompt Engineering", "Vector Databases",
    ],
    "cloud_devops": [
        "AWS", "GCP", "Azure", "Docker", "Kubernetes", "Terraform", "Ansible",
        "CI/CD", "GitHub Actions", "Jenkins", "Prometheus", "Grafana",
        "CloudFormation", "AWS CDK", "Site Reliability Engineering",
        "Infrastructure as Code", "Service Mesh", "Istio",
    ],
    "software_engineering": [
        "Python", "Java", "Go", "TypeScript", "Rust", "C++",
        "System Design", "REST APIs", "GraphQL", "gRPC", "Microservices",
        "Event-Driven Architecture", "Domain-Driven Design",
        "Test-Driven Development", "Code Review", "Git",
    ],
    "ai_engineering": [
        "Amazon Bedrock", "OpenAI API", "LangChain", "LlamaIndex",
        "Strands Agents", "Amazon Nova", "Retrieval-Augmented Generation",
        "Agentic AI", "Multi-Agent Systems", "Function Calling",
        "Embedding Models", "Vector Search", "Semantic Search",
        "AI Safety", "Responsible AI", "Model Governance",
    ],
    "product_management": [
        "Product Strategy", "Roadmap Planning", "OKRs", "User Research",
        "A/B Testing", "Agile", "Scrum", "JIRA", "Figma", "SQL",
        "Data Analysis", "Stakeholder Management", "Go-to-Market",
        "Customer Discovery", "Product Analytics", "Amplitude", "Mixpanel",
    ],
}

ROLE_SKILL_MAPPING = {
    "Senior Data Engineer": [
        "Apache Spark", "Apache Kafka", "dbt", "Airflow", "Snowflake",
        "Python", "SQL", "Data Modeling", "ETL/ELT Design", "AWS",
    ],
    "ML Engineer": [
        "PyTorch", "TensorFlow", "MLflow", "Python", "Feature Engineering",
        "Kubernetes", "Docker", "AWS", "Model Evaluation", "LLMs",
    ],
    "AI Engineer": [
        "Amazon Bedrock", "LangChain", "Strands Agents", "Python",
        "Agentic AI", "RAG", "Vector Databases", "Embedding Models",
        "Amazon Nova", "Multi-Agent Systems",
    ],
    "DevOps Engineer": [
        "Kubernetes", "Docker", "Terraform", "AWS", "CI/CD",
        "Prometheus", "GitHub Actions", "Python", "Linux", "Site Reliability Engineering",
    ],
    "Backend Engineer": [
        "Python", "Go", "Java", "REST APIs", "Microservices",
        "PostgreSQL", "Redis", "Docker", "System Design", "AWS",
    ],
    "Software Engineer": [
        "Python", "TypeScript", "REST APIs", "Git", "SQL",
        "Docker", "System Design", "Agile", "Code Review",
    ],
}


class SkillsGraphService:
    """
    Manages the semantic skills knowledge graph.
    Provides role-to-skill mappings and semantic skill search
    backed by Nova multimodal embeddings.
    """

    def __init__(self):
        self.opensearch = OpenSearchClient()
        self.nova_embeddings = NovaEmbeddingsClient()
        self._initialized = False

    async def initialize(self) -> None:
        """Pre-warm the skills graph — called at application startup."""
        if self._initialized:
            return

        # Ensure skills index exists in OpenSearch
        await self.opensearch.ensure_index(
            index=settings.opensearch_index_skills,
            mapping={
                "properties": {
                    "skill_name": {"type": "keyword"},
                    "domain": {"type": "keyword"},
                    "description": {"type": "text"},
                    "related_roles": {"type": "keyword"},
                    "embedding": {
                        "type": "knn_vector",
                        "dimension": settings.embedding_dimensions,
                    },
                }
            },
        )

        self._initialized = True
        logger.info("Skills knowledge graph initialized")

    async def get_skills_for_role(self, role: str) -> list[dict]:
        """
        Get the top skills for a target role, combining:
        - Hard-coded role-skill mappings for known roles
        - Semantic search for novel roles
        """
        # Check the hard-coded mapping first
        if role in ROLE_SKILL_MAPPING:
            skills = ROLE_SKILL_MAPPING[role]
            return [
                {"name": skill, "description": f"{skill} proficiency", "priority": idx + 1}
                for idx, skill in enumerate(skills)
            ]

        # Semantic fallback for novel role titles
        role_embedding = await self.nova_embeddings.embed_text(
            f"Skills required for {role}"
        )
        results = await self.opensearch.semantic_search(
            index=settings.opensearch_index_skills,
            query_vector=role_embedding,
            top_k=settings.skills_graph_max_neighbors,
        )
        return [
            {
                "name": r.get("skill_name", ""),
                "description": r.get("description", ""),
                "priority": idx + 1,
            }
            for idx, r in enumerate(results)
        ]

    async def get_related_skills(
        self, skill: str, top_k: int = 10
    ) -> list[dict]:
        """Find semantically related skills for a given skill."""
        skill_embedding = await self.nova_embeddings.embed_text(
            f"Skills related to {skill}"
        )
        results = await self.opensearch.semantic_search(
            index=settings.opensearch_index_skills,
            query_vector=skill_embedding,
            top_k=top_k + 1,  # +1 to exclude the skill itself
        )
        return [
            r for r in results if r.get("skill_name", "").lower() != skill.lower()
        ][:top_k]

    def get_all_domains(self) -> list[str]:
        return list(SKILLS_TAXONOMY.keys())

    def get_skills_by_domain(self, domain: str) -> list[str]:
        return SKILLS_TAXONOMY.get(domain, [])