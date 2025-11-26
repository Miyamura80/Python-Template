"""Telegram Bot integration for sending alerts and notifications."""

import requests
from loguru import logger as log
from common import global_config
from typing import Optional


class Telegram:
    """Telegram Bot API wrapper for sending messages."""

    def __init__(self):
        """Initialize Telegram bot with credentials from environment."""
        self.bot_token = global_config.TELEGRAM_BOT_TOKEN
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"

    def send_message(
        self,
        chat_id: str,
        text: str,
        parse_mode: str = "Markdown",
    ) -> Optional[int]:
        """
        Send a message to a Telegram chat.

        Args:
            chat_id: The chat ID to send the message to
            text: The message text to send
            parse_mode: Message formatting mode (Markdown, HTML, or None)

        Returns:
            Optional[int]: The message ID if successful, None otherwise
        """
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": parse_mode,
            }

            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()

            result = response.json()
            if result.get("ok"):
                message_id = result.get("result", {}).get("message_id")
                log.debug(
                    f"Message sent successfully to chat {chat_id}. Message ID: {message_id}"
                )
                return message_id
            else:
                log.error(
                    f"Failed to send Telegram message: {result.get('description')}"
                )
                return None

        except requests.exceptions.RequestException as e:
            log.error(f"Error sending Telegram message: {str(e)}")
            return None
        except Exception as e:
            log.error(f"Unexpected error sending Telegram message: {str(e)}")
            return None

    def send_message_to_chat(
        self,
        chat_name: str,
        text: str,
        parse_mode: str = "Markdown",
    ) -> Optional[int]:
        """
        Send a message to a named chat (using configured chat IDs).

        Args:
            chat_name: The logical name of the chat (e.g., "admin_alerts", "test")
            text: The message text to send
            parse_mode: Message formatting mode (Markdown, HTML, or None)

        Returns:
            Optional[int]: The message ID if successful, None otherwise
        """
        # Get chat ID from configuration
        chat_id = getattr(global_config.telegram.chat_ids, chat_name, None)
        if not chat_id:
            log.error(f"Chat ID not found for chat name: {chat_name}")
            return None

        return self.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)

    def delete_message(
        self,
        chat_id: str,
        message_id: int,
    ) -> bool:
        """
        Delete a message from a Telegram chat.

        Args:
            chat_id: The chat ID where the message exists
            message_id: The ID of the message to delete

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            url = f"{self.base_url}/deleteMessage"
            payload = {
                "chat_id": chat_id,
                "message_id": message_id,
            }

            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()

            result = response.json()
            if result.get("ok"):
                log.debug(
                    f"Message {message_id} deleted successfully from chat {chat_id}"
                )
                return True
            else:
                log.error(
                    f"Failed to delete Telegram message: {result.get('description')}"
                )
                return False

        except requests.exceptions.RequestException as e:
            log.error(f"Error deleting Telegram message: {str(e)}")
            return False
        except Exception as e:
            log.error(f"Unexpected error deleting Telegram message: {str(e)}")
            return False
