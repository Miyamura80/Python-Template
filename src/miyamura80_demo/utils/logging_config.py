from loguru import logger
import sys
from src.utils.context import session_id
from common import global_config
from human_id import generate_id
import asyncio
import os

_logging_initialized = False


def _should_show_location(level: str) -> bool:
    """Determine if location should be shown for given log level"""
    level = level.lower()
    config = global_config.logging.format.location

    if not config.enabled:
        return False

    level_map = {
        "info": config.show_for_info,
        "debug": config.show_for_debug,
        "warning": config.show_for_warning,
        "error": config.show_for_error,
    }

    return level_map.get(level, True)  # Default to True for unknown levels


def _get_task_name() -> str:
    """Get the current asyncio task name if it exists"""
    try:
        task = asyncio.current_task()
        if task:
            # Get task name, fallback to a shorter task ID format
            name = getattr(task, "name", None)
            if name:
                return name
            return "main"  # Default to 'main' if no name set
        return "main"
    except RuntimeError:
        # If called from outside asyncio event loop
        return "main"


def _get_replica_id() -> str:
    """Get the current Railway replica ID and transform it into a simple numeric index"""
    raw_id = os.getenv("RAILWAY_REPLICA_ID")
    if not raw_id:
        return "local"

    # Extract the last few characters of the ID and convert to an integer
    # This will give us a consistent number for each replica
    try:
        # Take last 4 chars of ID and convert to int, then mod with 100 to keep numbers small
        numeric_id = int(raw_id[-4:], 16) % 100
        return f"r{numeric_id}"  # prefix with 'r' to indicate replica
    except (ValueError, TypeError):
        return raw_id  # fallback to original ID if conversion fails


def _get_session_color(session_id: str) -> str:
    """Get a consistent color for a given session ID"""
    if session_id == "---":
        return "white"

    # List of distinct colors that work well in terminals
    colors = ["green", "yellow", "blue", "magenta", "cyan", "red"]

    # Convert session ID to a consistent numeric value
    # Take last 8 chars to limit the size of the number
    numeric_id = sum(ord(c) for c in session_id[-8:])
    color_index = numeric_id % len(colors)

    return colors[color_index]


def _build_format_string(record: dict) -> str:
    """Build format string dynamically based on log level"""
    format_parts = ["<level>{level: <6}</level>"]

    if global_config.logging.format.show_time:
        format_parts.append("{time:HH:mm:ss}")

    if global_config.logging.format.show_session_id:
        session_color = _get_session_color(record["extra"]["session_id"])
        format_parts.append(f"<{session_color}>{{extra[session_id]}}</{session_color}>")

    # Add replica ID to format string instead of task name
    format_parts.append("<magenta>{extra[replica_id]}</magenta>")

    # Build the location part of the format string if needed for this level
    if _should_show_location(record["level"].name):
        location_parts = []
        config = global_config.logging.format.location

        if config.show_file:
            location_parts.append("<cyan>{file.name}</cyan>")
        if config.show_function:
            location_parts.append("<cyan>{function}</cyan>")
        if config.show_line:
            location_parts.append("<cyan>{line}</cyan>")

        if location_parts:
            format_parts.append(":".join(location_parts))

    format_parts.append("<level>{message}</level>{exception}")
    return " | ".join(format_parts) + "\n"  # Added newline here


def _should_log_level(level: str, overrides: dict | None = None) -> bool:
    """Determine if this log level should be shown based on config and overrides"""
    level = level.lower()

    if overrides is None:
        overrides = {}

    # Check overrides first if they exist
    if overrides and level in overrides:
        return overrides[level]

    # Fall back to global config
    try:
        return getattr(global_config.logging.levels, level)
    except AttributeError:
        return True


def setup_logging(*, debug=None, info=None, warning=None, error=None, critical=None):
    """Setup centralized logging configuration with optional level overrides

    Args:
        debug (bool, optional): Override global debug log level
        info (bool, optional): Override global info log level
        warning (bool, optional): Override global warning log level
        error (bool, optional): Override global error log level
        critical (bool, optional): Override global critical log level
    """
    global _logging_initialized, logger

    if _logging_initialized:
        return

    # Remove any existing handlers
    logger.remove()

    # Initialize session_id if not already set
    if session_id.get() is None:
        session_id.set(generate_id())

    # Build overrides dict from provided arguments
    overrides = {}
    if debug is not None:
        overrides["debug"] = debug
    if info is not None:
        overrides["info"] = info
    if warning is not None:
        overrides["warning"] = warning
    if error is not None:
        overrides["error"] = error
    if critical is not None:
        overrides["critical"] = critical

    # Add session_id, replica ID, and level filtering to all log records
    def log_filter(record):
        # Add session ID and replica ID
        if "extra" not in record:
            record["extra"] = {}
        record["extra"]["session_id"] = session_id.get() or "---"
        record["extra"]["replica_id"] = _get_replica_id()

        # Check if this level should be logged using overrides
        return _should_log_level(record["level"].name, overrides)

    # Add our standardized handler with dynamic format and filter
    logger.add(
        sys.stderr,
        format=lambda record: _build_format_string(record),
        colorize=True,
        enqueue=True,
        backtrace=True,
        diagnose=True,
        catch=True,
        filter=log_filter,
    )

    _logging_initialized = True
