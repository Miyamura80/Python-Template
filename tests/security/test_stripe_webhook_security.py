
import os
import sys
import pytest
import stripe
import time
from unittest.mock import MagicMock, patch
from fastapi import Request, HTTPException

# We need to add the root to sys.path to import src
sys.path.append(os.getcwd())

# Import the module under test
from src.api.routes.payments.webhooks import _try_construct_event

def test_stripe_webhook_vuln_repro():
    """
    Verify that _try_construct_event REJECTS a payload signed with the
    TEST secret when configured for PROD.
    """

    # Setup test secrets
    PROD_SECRET = "whsec_prod_secret_12345"
    TEST_SECRET = "whsec_test_secret_67890"

    # Mock global_config to simulate PROD environment
    with patch("src.api.routes.payments.webhooks.global_config") as mock_config:
        mock_config.DEV_ENV = "prod"
        mock_config.STRIPE_WEBHOOK_SECRET = PROD_SECRET
        mock_config.STRIPE_TEST_WEBHOOK_SECRET = TEST_SECRET

        # Create a payload
        payload = b'{"id": "evt_test", "object": "event"}'
        timestamp = int(time.time())
        header = f"t={timestamp},v1=dummy_signature"

        # The function under test
        try:
            with patch("stripe.Webhook.construct_event") as mock_construct:
                # This mock simulates:
                # - Fails if secret is PROD_SECRET (simulating bad signature because payload signed with TEST)
                # - Succeeds if secret is TEST_SECRET
                def side_effect(payload, sig_header, secret):
                    if secret == TEST_SECRET:
                        return {"type": "test_event"}
                    raise stripe.error.SignatureVerificationError("Invalid signature", sig_header=sig_header, http_body=payload)

                mock_construct.side_effect = side_effect

                event = _try_construct_event(payload, header)

                # If we get here, it means it accepted it
                pytest.fail("Vulnerability STILL PRESENT: _try_construct_event accepted TEST secret in PROD mode!")

        except HTTPException as e:
             # If it raises HTTPException(400), it means it rejected it (secure behavior)
             assert e.status_code == 400
             assert e.detail == "Invalid signature"
             print(f"\n[SUCCESS] _try_construct_event rejected TEST secret in PROD mode.")
        except Exception as e:
             pytest.fail(f"Unexpected error: {e}")

if __name__ == "__main__":
    # Manually run the test function if executed as script
    try:
        test_stripe_webhook_vuln_repro()
    except Exception as e:
        print(e)
