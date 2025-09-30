from src.db.database import get_db_session
from src.utils.integration.telegram import Telegram
from loguru import logger as log
import uuid
from datetime import datetime, timezone


def alert_admin(user_id: str, issue_description: str, user_context: str = None) -> dict:
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
    try:
        # Get user information for context
        db = next(get_db_session())
        user_uuid = uuid.UUID(user_id)

        from src.db.tables.profiles import Profiles
        from src.db.tables.user_twitter_auth import UserTwitterAuth

        user_profile = db.query(Profiles).filter(Profiles.user_id == user_uuid).first()
        twitter_auth = (
            db.query(UserTwitterAuth)
            .filter(UserTwitterAuth.user_id == user_uuid)
            .first()
        )

        # Build user context for admin alert
        user_info = f"User ID: {user_id}"
        if user_profile:
            user_info += f"\nEmail: {user_profile.email}"
            if user_profile.organization_id:
                user_info += f"\nOrganization ID: {user_profile.organization_id}"

        if twitter_auth:
            user_info += f"\nTwitter Handle: {twitter_auth.display_name}"

        # Construct the alert message
        alert_message = f"""🚨 *Agent Escalation Alert* 🚨

*Issue:* {issue_description}

*User Context:*
{user_info}

*Additional Context:*
{user_context or 'None provided'}

*Timestamp:* {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}

---
_This alert was generated when the agent could not resolve a user's request with available tools and context._"""

        # Send Telegram alert
        telegram = Telegram()
        # Use test chat during testing to avoid spamming production alerts
        import sys

        is_testing = "pytest" in sys.modules or "test" in sys.argv[0].lower()
        chat_name = "test" if is_testing else "admin_alerts"

        message_id = telegram.send_message_to_chat(
            chat_name=chat_name, text=alert_message
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
                "error": "Failed to send admin alert. Please contact support directly."
            }

    except Exception as e:
        log.error(f"Error sending admin alert for user {user_id}: {str(e)}")
        return {
            "error": f"Failed to send admin alert: {str(e)}. Please contact support directly."
        }
