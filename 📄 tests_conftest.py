"""
SkillForge AI — pytest fixtures and configuration.
Uses moto for DynamoDB mocking and unittest.mock for Nova API calls.
"""

import asyncio
import json
import os
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

# Set test environment before app imports
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "test-key")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test-secret")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("OPENSEARCH_ENDPOINT", "http://localhost:9200")


@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for all tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_nova_lite():
    """Mock NovaLiteClient to avoid real Bedrock calls."""
    with patch("src.models.nova_lite.NovaLiteClient") as MockClass:
        instance = MockClass.return_value
        instance.reason = AsyncMock(return_value={
            "career_readiness_score": 62.5,
            "gap_summary": "You need Apache Kafka and dbt to target Data Engineer roles.",
            "urgent_gaps": [
                {
                    "skill": "Apache Kafka",
                    "current_level": 1,
                    "required_level": 4,
                    "gap_severity": "critical",
                    "salary_impact_usd": 12000,
                }
            ],
        })
        yield instance


@pytest.fixture
def mock_nova_embeddings():
    """Mock NovaEmbeddingsClient to return deterministic test vectors."""
    with patch("src.models.nova_embeddings.NovaEmbeddingsClient") as MockClass:
        instance = MockClass.return_value
        instance.embed_text = AsyncMock(return_value=[0.1] * 1024)
        instance.embed_skills_profile = AsyncMock(return_value=[0.2] * 1024)
        instance.embed_multimodal = AsyncMock(return_value=[0.3] * 1024)
        yield instance


@pytest.fixture
def mock_nova_sonic():
    """Mock NovaSONicClient for voice session tests."""
    with patch("src.models.nova_sonic.NovaSonicClient") as MockClass:
        instance = MockClass.return_value
        instance.create_session = AsyncMock(return_value="mock-session-id-001")
        instance.stream_audio = AsyncMock()
        instance.get_transcript = AsyncMock(return_value=(
            "I'm a software engineer with 5 years of Python experience. "
            "I want to transition to data engineering."
        ))
        instance.get_coaching_profile = AsyncMock(return_value={
            "detected_skills": ["Python", "SQL", "REST APIs"],
            "aspirations": ["Senior Data Engineer"],
            "years_of_experience": 5.0,
            "weekly_hours_available": 10.0,
            "weekly_budget_usd": 50.0,
        })
        instance.close_session = AsyncMock()
        yield instance


@pytest.fixture
def mock_nova_act():
    """Mock NovaActClient for enrollment automation tests."""
    with patch("src.models.nova_act.NovaActClient") as MockClass:
        instance = MockClass.return_value

        from src.models.nova_act import AutomationResult, AutomationStatus
        success = AutomationResult(
            status=AutomationStatus.COMPLETED,
            confirmation_number="CONF-TEST-001",
            confirmation_url="https://example.com/confirm",
            screenshot_path=None,
            duration_seconds=8.5,
            steps_taken=4,
        )
        instance.enroll_in_course = AsyncMock(return_value=success)
        instance.submit_certification_application = AsyncMock(return_value=success)
        instance.sync_to_google_calendar = AsyncMock(return_value=success)
        yield instance


@pytest.fixture
def mock_dynamodb():
    """Mock DynamoDB client for unit tests."""
    with patch("src.database.dynamodb.DynamoDBClient") as MockClass:
        instance = MockClass.return_value
        instance.get_item = AsyncMock(return_value=None)
        instance.put_item = AsyncMock()
        instance.update_item = AsyncMock(return_value={})
        instance.query_items = AsyncMock(return_value=[])
\<Streaming stoppped because the conversation grew too long for this model\>