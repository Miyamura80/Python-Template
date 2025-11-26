## High Priority

### Security Issues
- [ ] Fix session secret key in `src/server.py:13` - Currently hardcoded placeholder, should load from environment variable
- [x] Implement WorkOS JWT signature verification in `src/api/auth/workos_auth.py:77` - Currently disabled (`verify_signature: False`), security risk in production


### Infrastructure
- [ ] Move DB over to Convex
- [ ] Use RAILWAY_PRIVATE_DOMAIN to avoid egress fees

## Low Priority

### Features
- [ ] Implement API key authentication in `src/api/auth/unified_auth.py:53` - Structure exists but not implemented
- [ ] Add media handling support in DSPY LangFuse callback (`utils/llm/dspy_langfuse.py:71`) - Currently passes on image inputs
- [ ] Support tool use with streaming in agent endpoint (`src/api/routes/agent/agent.py:194`) - Currently disabled, complex to implement
- [ ] Restore RLS policies - Temporarily removed for WorkOS migration in:
  - `src/db/models/public/profiles.py:39`
  - `src/db/models/public/organizations.py:23`
  - `src/db/models/stripe/user_subscriptions.py:27`
  - Need to implement custom auth schema for WorkOS


### Configuration
- [ ] Fill in Stripe price IDs in `common/global_config.yaml:53` (`subscription.stripe.price_ids.test`)
- [ ] Set Stripe webhook URL in `common/global_config.yaml:60` (`stripe.webhook.url`)
