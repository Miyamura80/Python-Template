# Security Audit Findings

## Critical Issues

### 1. Stripe Webhook Signature Bypass (FIXED)

**Severity:** Critical
**Description:** The Stripe webhook handler `_try_construct_event` was configured to accept payloads signed with the Test Secret even when the application was running in Production mode. This would allow an attacker knowing the Test Secret to forge events (e.g., subscription creation) against the Production environment.
**Fix:** The logic in `src/api/routes/payments/webhooks.py` was updated to strictly enforce secret usage based on the environment (`DEV_ENV`). Production only uses `STRIPE_WEBHOOK_SECRET`, and non-production environments use `STRIPE_TEST_WEBHOOK_SECRET`.

## Low/Medium Issues

### 1. `alert_admin` DB Session Handling
**Severity:** Low
**Description:** The `alert_admin` tool manually manages a database session obtained from `get_db_session` generator. While it correctly closes it, the generator remains suspended until garbage collection.
**Recommendation:** Ensure `get_db_session` is used as a context manager if possible, or refactor tool to use `scoped_session` similar to `agent_stream_endpoint`.

### 2. Missing Rate Limiting on Webhooks
**Severity:** Low
**Description:** While signature verification prevents unauthorized payloads, the webhook endpoint is still exposed to DoS attacks.
**Recommendation:** Implement rate limiting (e.g., via Nginx or application middleware) for the webhook endpoint.

### 3. Usage Reset Logic
**Severity:** Low
**Description:** The `handle_usage_reset_webhook` trusts `invoice.payment_succeeded` events to reset usage. Ensure idempotency keys are handled to prevent double-processing if Stripe retries webhooks (though resetting to 0 is idempotent-ish).
