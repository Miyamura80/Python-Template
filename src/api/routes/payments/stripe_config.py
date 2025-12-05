"""Shared Stripe configuration and constants for payment routes."""

import stripe
from common import global_config
from loguru import logger

# Initialize Stripe with test credentials in dev mode
# Use test key in dev, production key in prod
stripe.api_key = (
    global_config.STRIPE_SECRET_KEY
    if global_config.DEV_ENV == "prod"
    else global_config.STRIPE_TEST_SECRET_KEY
)
stripe.api_version = global_config.stripe.api_version

# Single metered price with graduated tiers
# Stripe handles "included units" via tier 1 at $0
STRIPE_PRICE_ID = (
    global_config.subscription.stripe.price_ids.prod
    if global_config.DEV_ENV == "prod"
    else global_config.subscription.stripe.price_ids.test
)

# Metered billing configuration (for display/calculation)
INCLUDED_UNITS = global_config.subscription.metered.included_units
OVERAGE_UNIT_AMOUNT = global_config.subscription.metered.overage_unit_amount
UNIT_LABEL = global_config.subscription.metered.unit_label


def verify_stripe_price():
    """Verify Stripe price ID is valid. Call at startup."""
    try:
        price = stripe.Price.retrieve(STRIPE_PRICE_ID, api_key=stripe.api_key)

        # Check price type
        is_metered = price.recurring and price.recurring.get("usage_type") == "metered"
        is_tiered = price.billing_scheme == "tiered"

        logger.debug(
            f"Price verified: {price.id} "
            f"(metered: {is_metered}, tiered: {is_tiered}, livemode: {price.livemode})"
        )

        if not is_metered:
            logger.warning(
                f"Price {STRIPE_PRICE_ID} is not metered. "
                "For usage-based billing, create a metered price with graduated tiers."
            )

        if is_metered and not is_tiered:
            logger.info(
                f"Price {STRIPE_PRICE_ID} is metered but not tiered. "
                "All usage will be charged. Consider graduated tiers for included units."
            )

    except Exception as e:
        logger.error(f"Error verifying price: {str(e)}")
        raise


# Verify price on module load
verify_stripe_price()
