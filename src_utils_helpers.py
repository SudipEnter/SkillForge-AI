"""SkillForge AI — General utility functions."""

import hashlib
import re
import uuid
from datetime import datetime, timezone
from typing import Any


def generate_session_id(user_id: str) -> str:
    return f"sf_{user_id}_{uuid.uuid4().hex[:12]}"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sanitize_skill_name(skill: str) -> str:
    """Normalize skill names for consistent storage and comparison."""
    return re.sub(r"[^a-zA-Z0-9\s\-\./+#]", "", skill).strip()


def truncate_text(text: str, max_length: int = 200, suffix: str = "...") -> str:
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def format_salary(amount: int, currency: str = "USD") -> str:
    return f"${amount:,}" if currency == "USD" else f"{amount:,} {currency}"


def hash_user_id(user_id: str) -> str:
    """Create a deterministic hash of a user ID for logging (PII protection)."""
    return hashlib.sha256(user_id.encode()).hexdigest()[:12]