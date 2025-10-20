import yaml
import stripe
from loguru import logger as log
from common import global_config
from src.utils.logging_config import setup_logging

setup_logging()

# Load webhook event configuration from env_config.yaml
with open("src/stripe/dev/env_config.yaml", "r") as file:
    config = yaml.safe_load(file)


def create_or_update_webhook_endpoint():
    """Create a new webhook endpoint or update existing one with subscription and invoice event listeners."""

    stripe.api_key = global_config.STRIPE_API_KEY

    try:
        webhook_config = config["webhook"]

        # Get URL from global config
        webhook_url = global_config.stripe.webhook.url

        # Ensure URL ends with /webhook/stripe
        base_url = webhook_url.rstrip("/")
        if not base_url.endswith("/webhook/stripe"):
            webhook_url = f"{base_url}/webhook/stripe"
            log.info(f"Adjusted webhook URL to: {webhook_url}")

        # List existing webhooks
        existing_webhooks = stripe.WebhookEndpoint.list(limit=10)

        # Find webhook with matching URL if it exists
        existing_webhook = next(
            (hook for hook in existing_webhooks.data if hook.url == webhook_url),
            None,
        )

        if existing_webhook:
            # Update existing webhook
            webhook_endpoint = stripe.WebhookEndpoint.modify(
                existing_webhook.id,
                enabled_events=webhook_config["enabled_events"],
                description=webhook_config["description"],
            )
            log.info(f"Updated webhook endpoint: {webhook_endpoint.id}")

        else:
            # Create new webhook
            webhook_endpoint = stripe.WebhookEndpoint.create(
                url=webhook_url,
                enabled_events=webhook_config["enabled_events"],
                description=webhook_config["description"],
            )
            log.info(f"Created webhook endpoint: {webhook_endpoint.id}")
            log.info(f"Webhook signing secret: {webhook_endpoint.secret}")
            with open(f"src/stripe/{webhook_endpoint.id}.secret", "w") as secret_file:
                secret_file.write(f"WEBHOOK_ENDPOINT_ID: {webhook_endpoint.id}\n")
                secret_file.write(
                    f"WEBHOOK_SIGNING_SECRET: {webhook_endpoint.secret}\n"
                )
            log.info(
                f"Webhook endpoint and signing secret have been dumped to {webhook_endpoint.id}.secret file."
            )

        return webhook_endpoint

    except stripe.error.StripeError as e:
        log.error(f"Failed to create/update webhook endpoint: {str(e)}")
        raise
    except Exception as e:
        log.error(f"Unexpected error creating/updating webhook endpoint: {str(e)}")
        raise


if __name__ == "__main__":
    # Example usage
    _endpoint = create_or_update_webhook_endpoint()
