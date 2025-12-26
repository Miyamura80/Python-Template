from src.db.database import get_db_session
from src.utils.integration.telegram import Telegram
from loguru import logger as log
from typing import Optional
from datetime import datetime, timezone
from src.api.auth.utils import user_uuid_from_str
import re

from utils.llm.tool_display import tool_display


def escape_markdown_v2(text: str) -> str:
    """
    Escape special characters for Telegram MarkdownV2.

    Args:
        text: The text to escape

    Returns:
        str: Escaped text safe for MarkdownV2
    """
    # Characters that need to be escaped in MarkdownV2
    special_chars = r"_*[]()~`>#+-=|{}.!"
    return re.sub(f"([{re.escape(special_chars)}])", r"\\\1", text)


@tool_display("Escalating to an admin for help…")
def alert_admin(
    user_id: str, issue_description: str, user_context: Optional[str] = None
) -> dict:
    """
    Alert administrators via Telegram when the agent lacks context to complete a task.
    This should be used sparingly as an "escape hatch" when all other tools and approaches fail.

    Args:
        user_id: The ID of the user for whom the task cannot be completed
        issue_description: Clear description of what the agent cannot accomplish and why
        user_context: Optional additional context about the user's request or situation

    Returns:
        dict: Status of the alert operation
    """
    db = None
    try:
        # Get user information for context
        db = next(get_db_session())
        user_uuid = user_uuid_from_str(user_id)

        from src.db.models.public.profiles import Profiles

        user_profile = db.query(Profiles).filter(Profiles.user_id == user_uuid).first()

        # Build user context for admin alert
        user_info = f"User ID: {user_id}"
        if user_profile:
            user_info += f"\nEmail: {user_profile.email}"
            if user_profile.organization_id:
                user_info += f"\nOrganization ID: {user_profile.organization_id}"

        # Escape all dynamic content for MarkdownV2
        escaped_issue = escape_markdown_v2(issue_description)
        escaped_user_info = escape_markdown_v2(user_info)
        escaped_context = escape_markdown_v2(user_context or "None provided")
        timestamp = escape_markdown_v2(
            datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        )

        # Construct the alert message using MarkdownV2
        alert_message = f"""🚨 *Agent Escalation Alert* 🚨

*Issue:* {escaped_issue}

*User Context:*
{escaped_user_info}

*Additional Context:*
{escaped_context}

*Timestamp:* {timestamp}

\\-\\-\\-
_This alert was generated when the agent could not resolve a user's request with available tools and context\\._"""

        # Send Telegram alert
        telegram = Telegram()
        # Use test chat during testing to avoid spamming production alerts
        import sys

        is_testing = "pytest" in sys.modules or "test" in sys.argv[0].lower()
        chat_name = "test" if is_testing else "admin_alerts"

        message_id = telegram.send_message_to_chat(
            chat_name=chat_name, text=alert_message, parse_mode="MarkdownV2"
        )

        if message_id:
            log.info(
                f"Admin alert sent successfully for user {user_id}. Message ID: {message_id}"
            )
            return {
                "status": "success",
                "message": "Administrator has been alerted about the issue.",
                "telegram_message_id": message_id,
            }
        else:
            log.error(f"Failed to send admin alert for user {user_id}")
            return {
                "status": "error",
                "error": "Failed to send admin alert. Please contact support directly.",
            }

    except Exception as e:
        log.error(f"Error sending admin alert for user {user_id}: {str(e)}")
        return {
            "status": "error",
            "error": f"Failed to send admin alert: {str(e)}. Please contact support directly.",
        }
    finally:
        if db is not None:
            db.close()
