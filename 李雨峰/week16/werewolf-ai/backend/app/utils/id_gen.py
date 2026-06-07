"""ID generation utilities."""

import uuid


def generate_id() -> str:
    """Generate a short UUID-style ID."""
    return str(uuid.uuid4())


def generate_short_id() -> str:
    """Generate a shorter ID (8 hex chars) suitable for room codes."""
    return uuid.uuid4().hex[:8]
