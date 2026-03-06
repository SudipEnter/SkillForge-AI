"""
SkillForge AI — Application Configuration
Centralized settings management using Pydantic Settings.
"""

from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    secret_key: str = "change-me-in-production"
    cors_origins: List[str] = ["http://localhost:3000"]
    log_level: str = "INFO"

    # AWS Core
    aws_access_key_id: str
    aws_secret_access_key: str
    aws_default_region: str = "us-east-1"

    # Amazon Nova Model IDs
    nova_lite_model_id: str = "amazon.nova-lite-v2:0"
    nova_sonic_model_id: str = "amazon.nova-sonic-v2:0"
    nova_embed_model_id: str = "amazon.nova-embed-multimodal-v1:0"

    # Nova Act
    nova_act_api_key: str
    nova_act_endpoint: str = "https://nova-act.us-east-1.amazonaws.com"

    # DynamoDB
    dynamodb_table_users: str = "skillforge-users"
    dynamodb_table_sessions: str = "skillforge-sessions"
    dynamodb_table_learning_paths: str = "skillforge-learning-paths"

    # OpenSearch
    opensearch_endpoint: str
    opensearch_index_skills: str = "skills-embeddings"
    opensearch_index_courses: str = "course-embeddings"
    opensearch_index_jobs: str = "job-embeddings"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Job Market APIs
    linkedin_api_key: str = ""
    indeed_api_key: str = ""

    # Learning Platforms (for Nova Act)
    coursera_username: str = ""
    coursera_password: str = ""
    udemy_api_key: str = ""
    linkedin_learning_token: str = ""

    # Monitoring
    sentry_dsn: str = ""

    # Agent Configuration
    max_agent_retries: int = 3
    agent_timeout_seconds: int = 30
    voice_session_timeout_minutes: int = 60
    embedding_dimensions: int = 1536
    skills_graph_max_neighbors: int = 25

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()