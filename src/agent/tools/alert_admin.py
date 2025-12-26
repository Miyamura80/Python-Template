
import requests
import os
from loguru import logger as log

class AdminAgentTools:
    def __init__(self):
        self.telegram_bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        # Assuming there is a chat_id either in env or passed.
        # For now I'll check env.
        self.telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    def alert_admin(self, message: str, context: str = None) -> dict:
        """
        Sends an alert to the admin via Telegram.
        """
        if not self.telegram_bot_token or not self.telegram_chat_id:
            return {"status": "error", "message": "Telegram credentials not found"}

        url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"

        text = message
        if context:
            text += f"\n\nContext: {context}"

        try:
            response = requests.post(url, json={
                "chat_id": self.telegram_chat_id,
                "text": text,
                "parse_mode": "Markdown"
            })

            res_json = response.json()
            if res_json.get("ok"):
                return {"status": "success", "response": res_json}
            else:
                return {"status": "error", "message": res_json.get("description")}
        except Exception as e:
            log.error(f"Failed to alert admin: {e}")
            return {"status": "error", "message": str(e)}
