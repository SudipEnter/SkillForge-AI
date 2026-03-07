"""
Amazon Nova 2 Lite — Text Reasoning & Analysis Client
Used by: SkillsGapAgent, LearningPathAgent, JobMarketAgent, CareerCoachAgent

Capabilities leveraged:
  - Complex multi-step reasoning for skills gap analysis
  - Structured JSON extraction from coaching transcripts
  - Market intelligence synthesis from multiple data sources
  - Multimodal document analysis (resume PDFs, GitHub code)
"""

import asyncio
import json
import logging
import re
from functools import partial
from typing import Any, Optional, Union

import boto3
from botocore.config import Config

from src.config import settings

logger = logging.getLogger(__name__)

_BEDROCK_CONFIG = Config(
    region_name=settings.bedrock_region,
    retries={"max_attempts": 3, "mode": "adaptive"},
    read_timeout=120,
    connect_timeout=30,
)


class NovaLiteClient:
    """
    Wrapper around Amazon Nova 2 Lite via AWS Bedrock.

    Nova 2 Lite is used for all agentic reasoning tasks in SkillForge:
    - Skills gap analysis (comparing user profile vs. job requirements)
    - Learning path generation (week-by-week curriculum building)
    - Job market intelligence synthesis
    - Career coaching profile extraction from transcripts
    """

    def __init__(self):
        self._client = boto3.client(
            "bedrock-runtime",
            config=_BEDROCK_CONFIG,
            aws_access_key_id=settings.aws_access_key_id or None,
            aws_secret_access_key=settings.aws_secret_access_key or None,
            aws_session_token=settings.aws_session_token or None,
        )
        self.model_id = settings.nova2_lite_model_id

    # ── Internal: sync → async wrapper ───────────────────────────────
    async def _invoke(self, payload: dict) -> dict:
        """Run boto3 invoke_model in thread pool to avoid blocking the event loop."""
        loop = asyncio.get_event_loop()
        call = partial(
            self._client.invoke_model,
            modelId=self.model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload),
        )
        response = await loop.run_in_executor(None, call)
        return json.loads(response["body"].read())

    # ── Public API ────────────────────────────────────────────────────
    async def reason(
        self,
        system_prompt: str,
        user_message: str,
        context: Optional[dict] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        response_format: str = "text",   # "text" | "json"
    ) -> Union[dict, str]:
        """
        Core reasoning method used by all agents.

        When response_format="json", Nova 2 Lite is prompted to return
        strict JSON and the response is automatically parsed.
        """
        full_message = user_message
        if context:
            full_message = (
                f"<context>\n{json.dumps(context, indent=2, default=str)}\n</context>\n\n"
                f"{user_message}"
            )

        system = system_prompt
        if response_format == "json":
            system += "\n\nCRITICAL: Respond ONLY with valid JSON. No markdown, no explanation."

        payload = {
            "messages": [
                {"role": "user", "content": [{"text": full_message}]}
            ],
            "system": [{"text": system}],
            "inferenceConfig": {
                "temperature": temperature,
                "maxTokens": max_tokens,
                "topP": settings.bedrock_top_p,
            },
        }

        try:
            result = await self._invoke(payload)
            text: str = result["output"]["message"]["content"][0]["text"]

            if response_format == "json":
                return self._parse_json(text)
            return text

        except Exception as exc:
            logger.error(f"Nova 2 Lite error [{self.model_id}]: {exc}", exc_info=True)
            return {} if response_format == "json" else ""

    async def analyze_multimodal(
        self,
        system_prompt: str,
        user_message: str,
        image_bytes: Optional[bytes] = None,
        document_text: Optional[str] = None,
        temperature: float = 0.3,
    ) -> str:
        """
        Multimodal analysis — used for portfolio screenshots, resume parsing.
        Nova 2 Lite supports image + text inputs natively.
        """
        import base64

        content: list[dict] = []

        if image_bytes:
            content.append({
                "image": {
                    "format": "jpeg",
                    "source": {"bytes": base64.b64encode(image_bytes).decode()},
                }
            })

        if document_text:
            content.append({"text": f"<document>\n{document_text}\n</document>"})

        content.append({"text": user_message})

        payload = {
            "messages": [{"role": "user", "content": content}],
            "system": [{"text": system_prompt}],
            "inferenceConfig": {
                "temperature": temperature,
                "maxTokens": settings.bedrock_max_tokens,
            },
        }

        try:
            result = await self._invoke(payload)
            return result["output"]["message"]["content"][0]["text"]
        except Exception as exc:
            logger.error(f"Nova 2 Lite multimodal error: {exc}")
            return ""

    async def stream_reason(
        self,
        system_prompt: str,
        user_message: str,
        context: Optional[dict] = None,
        temperature: float = 0.4,
    ):
        """
        Async generator for streaming Nova 2 Lite responses.
        Used to stream real-time analysis results to the frontend via WebSocket.
        """
        full_message = user_message
        if context:
            full_message = (
                f"<context>\n{json.dumps(context, indent=2, default=str)}\n</context>\n\n"
                f"{user_message}"
            )

        payload = {
            "messages": [{"role": "user", "content": [{"text": full_message}]}],
            "system": [{"text": system_prompt}],
            "inferenceConfig": {
                "temperature": temperature,
                "maxTokens": settings.bedrock_max_tokens,
            },
        }

        loop = asyncio.get_event_loop()
        call = partial(
            self._client.invoke_model_with_response_stream,
            modelId=self.model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload),
        )

        try:
            response = await loop.run_in_executor(None, call)
            stream = response.get("body")
            if stream:
                for event in stream:
                    chunk = event.get("chunk")
                    if chunk:
                        data = json.loads(chunk["bytes"].decode())
                        if data.get("type") == "content_block_delta":
                            delta = data.get("delta", {}).get("text", "")
                            if delta:
                                yield delta
        except Exception as exc:
            logger.error(f"Nova 2 Lite stream error: {exc}")

    @staticmethod
    def _parse_json(text: str) -> dict:
        """Robustly extract JSON from Nova 2 Lite response."""
        text = text.strip()
        # Try direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        # Extract JSON block
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        logger.warning(f"Failed to parse JSON from Nova 2 Lite: {text[:200]}")
        return {}