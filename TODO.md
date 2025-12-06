## 🟢 High Priority

### Core Features

- Look at letstellit for inspiration around tests & core features

### Infrastructure
- [ ] Move DB over to Convex
- [ ] Use RAILWAY_PRIVATE_DOMAIN to avoid egress fees

## 🟡 Low Priority

### Features
- [ ] Implement API key authentication in `src/api/auth/unified_auth.py:53` - Structure exists but not implemented
- [ ] Add media handling support in DSPY LangFuse callback (`utils/llm/dspy_langfuse.py:71`) - Currently passes on image inputs
- [ ] Support tool use with streaming in agent endpoint (`src/api/routes/agent/agent.py:194`) - Currently disabled, complex to implement
- [ ] Restore RLS policies - Temporarily removed for WorkOS migration in:
  - `src/db/models/public/profiles.py:39`
  - `src/db/models/public/organizations.py:23`
  - `src/db/models/stripe/user_subscriptions.py:27`
  - Need to implement custom auth schema for WorkOS

