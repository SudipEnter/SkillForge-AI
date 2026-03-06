"""
SkillForge AI — Centralized Configuration
All settings loaded from environment variables with safe defaults.
"""

from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Application ────────────────────────────────────────────────
    app_name: str = "SkillForge AI"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    environment: str = "development"
    log_level: str = "INFO"

    @property
    def is_development(self) -> bool:
        return self.environment.lower() in ("development", "dev", "local")

    # ── AWS Core ───────────────────────────────────────────────────
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_session_token: str = ""
    aws_default_region: str = "us-east-1"

    # ── Amazon Nova Models ─────────────────────────────────────────
    nova_lite_model_id: str = "amazon.nova-lite-v1:0"
    nova_pro_model_id: str = "amazon.nova-pro-v1:0"
    nova_micro_model_id: str = "amazon.nova-micro-v1:0"
    nova_sonic_model_id: str = "amazon.nova-sonic-v1:0"
    nova_embeddings_model_id: str = "amazon.nova-embed-text-v1"

    # Nova 2 models (latest)
    nova2_lite_model_id: str = "amazon.nova-lite-v2:0"
    nova2_sonic_model_id: str = "amazon.nova-sonic-v2:0"

    # ── Nova Act ───────────────────────────────────────────────────
    nova_act_api_key: str = ""
    nova_act_headless: bool = True
    nova_act_timeout_seconds: int = 120
    nova_act_screenshot_on_error: bool = True

    # ── Amazon Bedrock ─────────────────────────────────────────────
    bedrock_region: str = "us-east-1"
    bedrock_max_tokens: int = 4096
    bedrock_temperature: float = 0.3
    bedrock_top_p: float = 0.9

    # ── DynamoDB Tables ────────────────────────────────────────────
    dynamodb_table_users: str = "skillforge-users"
    dynamodb_table_sessions: str = "skillforge-sessions"
    dynamodb_table_learning_paths: str = "skillforge-learning-paths"
    dynamodb_table_enrollments: str = "skillforge-enrollments"

    # ── OpenSearch ─────────────────────────────────────────────────
    opensearch_endpoint: str = "https://localhost:9200"
    opensearch_index_skills: str = "skillforge-skills"
    opensearch_index_courses: str = "skillforge-courses"
    opensearch_index_jobs: str = "skillforge-jobs"
    opensearch_username: str = "admin"
    opensearch_password: str = "admin"

    # ── Nova Embeddings Config ─────────────────────────────────────
    embedding_dimensions: int = 1024
    skills_graph_max_neighbors: int = 20
    embedding_batch_size: int = 50

    # ── Voice Coaching (Nova 2 Sonic) ──────────────────────────────
    sonic_sample_rate: int = 16000
    sonic_channels: int = 1
    sonic_encoding: str = "pcm"
    sonic_session_timeout_minutes: int = 20
    voice_activity_detection_enabled: bool = True
    silence_threshold_ms: int = 1500

    # ── External Job Market APIs ───────────────────────────────────
    linkedin_api_key: Optional[str] = None
    indeed_api_key: Optional[str] = None
    github_token: Optional[str] = None

    # ── S3 Storage ─────────────────────────────────────────────────
    s3_bucket_resumes: str = "skillforge-resumes"
    s3_bucket_portfolios: str = "skillforge-portfolios"
    s3_bucket_audio: str = "skillforge-audio-sessions"

    # ── CORS & Security ────────────────────────────────────────────
    cors_origins: list[str] = [
        "http://localhost:3000",
        "https://skillforge.ai",
    ]
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 10080  # 7 days

    # ── Rate Limiting ──────────────────────────────────────────────
    rate_limit_requests_per_minute: int = 60
    max_concurrent_voice_sessions: int = 100
    max_nova_act_concurrent_browsers: int = 5

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()