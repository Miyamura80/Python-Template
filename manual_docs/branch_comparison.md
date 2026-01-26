# Branch Feature Comparison

This document provides a detailed comparison of features available in the `main` and `saas` branches.

## Overview

- **`main`**: Lightweight Python template with core tooling, LLM inference, and CI/CD
- **`saas`**: Full-featured SaaS application template extending `main` with web framework, auth, payments, and database

## Detailed Comparison

### Core Infrastructure

| Feature | `main` | `saas` | Notes |
|---------|:------:|:------:|-------|
| UV dependency management | ✅ | ✅ | Fast Python package manager |
| Pydantic-settings configuration | ✅ | ✅ | Type-safe config with validation |
| Global config (YAML) | ✅ | ✅ | Centralized hyperparameters |
| Environment variables (.env) | ✅ | ✅ | Secrets management |
| Loguru logging | ✅ | ✅ | Structured logging |
| Production config | ❌ | ✅ | Separate production settings |

### Code Quality & CI

| Feature | `main` | `saas` | Notes |
|---------|:------:|:------:|-------|
| Ruff linter | ✅ | ✅ | Fast Python linter |
| Ruff formatter | ✅ | ✅ | Opinionated code formatting |
| Vulture dead code detection | ✅ | ✅ | Find unused code |
| ty type checker | ✅ | ✅ | Type checking |
| GitHub Actions CI | ✅ | ✅ | Automated testing & linting |
| Auto-delete branch workflow | ✅ | ✅ | Clean up merged branches |

### LLM & AI

| Feature | `main` | `saas` | Notes |
|---------|:------:|:------:|-------|
| DSPY inference | ✅ | ✅ | Structured LLM programming |
| LangFuse observability | ✅ | ✅ | LLM tracing & analytics |
| LiteLLM integration | ✅ | ✅ | Multi-provider LLM support |

### Testing

| Feature | `main` | `saas` | Notes |
|---------|:------:|:------:|-------|
| pytest framework | ✅ | ✅ | Python testing |
| TestTemplate base class | ✅ | ✅ | Shared test utilities |
| pytest-asyncio | ✅ | ✅ | Async test support |
| E2E test structure | ❌ | ✅ | End-to-end testing patterns |

### Web Framework

| Feature | `main` | `saas` | Notes |
|---------|:------:|:------:|-------|
| FastAPI | ❌ | ✅ | Modern async web framework |
| Uvicorn server | ❌ | ✅ | ASGI server |
| API routes structure | ❌ | ✅ | Organized route modules |
| Rate limiting | ❌ | ✅ | Request throttling |
| HTTPX client | ❌ | ✅ | Async HTTP client |

### Database

| Feature | `main` | `saas` | Notes |
|---------|:------:|:------:|-------|
| SQLAlchemy ORM | ❌ | ✅ | Async ORM with 2.0 style |
| Alembic migrations | ❌ | ✅ | Database schema versioning |
| Row-Level Security (RLS) | ❌ | ✅ | Postgres RLS policies |
| Model discovery | ❌ | ✅ | Automatic model registration |
| psycopg2 driver | ❌ | ✅ | PostgreSQL adapter |

### Authentication

| Feature | `main` | `saas` | Notes |
|---------|:------:|:------:|-------|
| WorkOS integration | ❌ | ✅ | Enterprise SSO & user management |
| API key authentication | ❌ | ✅ | Programmatic access |
| Unified auth middleware | ❌ | ✅ | Combined auth strategies |
| JWT support | ❌ | ✅ | Token-based auth |
| User model | ❌ | ✅ | User data persistence |

### Payments & Billing

| Feature | `main` | `saas` | Notes |
|---------|:------:|:------:|-------|
| Stripe integration | ❌ | ✅ | Payment processing |
| Checkout sessions | ❌ | ✅ | Payment collection |
| Subscription management | ❌ | ✅ | Recurring billing |
| Usage metering | ❌ | ✅ | Usage-based billing |
| Webhook handlers | ❌ | ✅ | Stripe event processing |
| Subscription config | ❌ | ✅ | Plan definitions |

### Additional Features

| Feature | `main` | `saas` | Notes |
|---------|:------:|:------:|-------|
| Referral system | ❌ | ✅ | User referral tracking |
| Agent system | ❌ | ✅ | AI agent with tools |
| Agent conversation history | ❌ | ✅ | Persistent chat history |
| Railway deployment | ❌ | ✅ | Procfile & deploy scripts |

## When to Use Each Branch

### Use `main` when:
- Building CLI tools or scripts
- Creating data processing pipelines
- Prototyping LLM applications
- Projects that don't need a web server or user auth

### Use `saas` when:
- Building a web application with user accounts
- Need payment processing and subscriptions
- Require database persistence
- Building a production SaaS product
