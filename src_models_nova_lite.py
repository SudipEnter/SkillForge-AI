"""
SkillForge AI — Amazon Nova 2 Lite Integration
High-speed reasoning agent for skills analysis, path generation, and market intelligence.
"""

import json
import logging
from typing import Any, Optional

import boto3
from botocore.config import Config
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import settings

logger = logging.getLogger(__name__)


class NovaLiteClient:
    """
    Amazon Nova 2 Lite client for agent reasoning tasks.

    Used by all SkillForge reasoning agents:
    - Skills Gap Analysis Agent
    - Learning Path Architect Agent
    - Job Market Intelligence Agent
    - Care Gap Agent (weekly check-ins)
    """

    def __init__(self):
        self.client = boto3.client(
            service_name="bedrock-runtime",
            region_name=settings.aws_default_region,
            config=Config(
                connect_timeout=10,
                read_timeout=120,
                retries={"max_attempts": settings.max_agent_retries},
            ),
        )
        self.model_id = settings.nova_lite_model_id

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def reason(
        self,
        system_prompt: str,
        user_message: str,
        context: Optional[dict] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        response_format: str = "json",
    ) -> dict | str:
        """
        Execute a reasoning task with Nova 2 Lite.

        Args:
            system_prompt: Agent's role and task definition
            user_message: The specific query or data to reason about
            context: Additional structured context (user profile, market data, etc.)
            temperature: Creativity level (0.0-1.0). Lower = more deterministic.
            max_tokens: Maximum response length
            response_format: "json" or "text"

        Returns:
            Parsed dict if response_format="json", else raw string
        """
        messages = []

        # Inject structured context if provided
        if context:
            context_block = f"\n\n<context>\n{json.dumps(context, indent=2)}\n</context>"
            user_message = user_message + context_block

        messages.append({"role": "user", "content": user_message})

        request_body = {
            "messages": messages,
            "system": [{"text": system_prompt}],
            "inferenceConfig": {
                "temperature": temperature,
                "maxTokens": max_tokens,
                "stopSequences": ["</output>"] if response_format == "json" else [],
            },
        }

        try:
            import asyncio
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.converse(
                    modelId=self.model_id,
                    **request_body,
                ),
            )

            output_text = (
                response["output"]["message"]["content"][0]["text"]
            )

            if response_format == "json":
                # Extract JSON from potential markdown code blocks
                return self._parse_json_response(output_text)
            return output_text

        except Exception as e:
            logger.error(f"Nova 2 Lite reasoning error: {e}")
            raise

    async def reason_with_tools(
        self,
        system_prompt: str,
        user_message: str,
        tools: list[dict],
        context: Optional[dict] = None,
    ) -> dict:
        """
        Execute a tool-augmented reasoning task.
        Used for job market data retrieval, course catalog queries, etc.
        """
        messages = [{"role": "user", "content": user_message}]
        if context:
            messages[0]["content"] += f"\n\n<context>{json.dumps(context)}</context>"

        request_body = {
            "messages": messages,
            "system": [{"text": system_prompt}],
            "toolConfig": {
                "tools": tools,
                "toolChoice": {"auto": {}},
            },
            "inferenceConfig": {
                "temperature": 0.2,
                "maxTokens": 4096,
            },
        }

        import asyncio
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.client.converse(
                modelId=self.model_id,
                **request_body,
            ),
        )

        return response

    def _parse_json_response(self, text: str) -> dict:
        """Extract and parse JSON from Nova's text response."""
        # Remove markdown code fences if present
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1])

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse failed, attempting extraction: {e}")
            # Try to find JSON object within the text
            import re
            json_match = re.search(r"\{.*\}", text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            raise ValueError(f"Could not parse JSON from response: {text[:200]}")