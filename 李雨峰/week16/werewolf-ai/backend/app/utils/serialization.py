"""Serialization helpers for Pydantic models."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel


def model_to_dict(model: BaseModel) -> dict[str, Any]:
    """Convert a Pydantic model to a plain dict."""
    return model.model_dump()


def model_to_json(model: BaseModel, **kwargs: Any) -> str:
    """Convert a Pydantic model to a JSON string."""
    return model.model_dump_json(**kwargs)


def dict_to_model(data: dict[str, Any], model_cls: type[BaseModel]) -> BaseModel:
    """Create a Pydantic model from a dict."""
    return model_cls.model_validate(data)


def json_to_model(json_str: str, model_cls: type[BaseModel]) -> BaseModel:
    """Create a Pydantic model from a JSON string."""
    return model_cls.model_validate_json(json_str)


def safe_json_loads(text: str) -> dict[str, Any] | None:
    """Parse JSON string to dict, returning None on failure."""
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None
