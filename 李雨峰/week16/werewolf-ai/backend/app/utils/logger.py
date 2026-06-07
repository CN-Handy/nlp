"""Structured logging configuration using structlog."""

import logging
import sys
from pathlib import Path
from typing import Any

import structlog
from structlog.typing import EventDict


def setup_logging(log_level: str = "INFO", log_dir: str | None = None) -> None:
    """Configure structlog for the application."""
    # Shared processors
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    # Console renderer
    structlog.configure(
        processors=[
            *shared_processors,
            structlog.processors.dict_tracebacks,
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )


def get_game_logger(game_id: str, log_dir: Path | None = None) -> Any:
    """Get a logger that writes to a game-specific JSONL file."""
    if log_dir is None:
        log_dir = Path(__file__).resolve().parent.parent / "data" / "logs"

    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{game_id}.jsonl"

    def jsonl_processor(logger: Any, method_name: str, event_dict: EventDict) -> bytes:
        """Write log events as JSON lines to the game log file."""
        from structlog.processors import JSONRenderer

        json_renderer = JSONRenderer()
        json_bytes = json_renderer(logger, method_name, event_dict)
        if isinstance(json_bytes, str):
            json_bytes = json_bytes.encode("utf-8")
        with open(log_file, "ab") as f:
            f.write(json_bytes + b"\n")
        return json_bytes

    file_logger = structlog.wrap_logger(
        structlog.PrintLoggerFactory(),
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            jsonl_processor,
        ],
    )

    return file_logger.bind(game_id=game_id)
