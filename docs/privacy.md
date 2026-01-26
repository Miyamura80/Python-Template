# Privacy and Data Handling

This repository is a template and does not include production data collection by default. If you add data handling to your implementation, follow these guidelines.

## Data Minimization

- Collect only what you need.
- Avoid storing sensitive data unless required.

## Secrets and Credentials

- Store secrets in `.env` (or a secrets manager), never in code.
- Do not log API keys, tokens, or user identifiers.

## Logging

- Treat logs as sensitive.
- Redact or hash identifiers before logging.

## Third-Party Services

- Document any external processors and what data they receive.
- Ensure their retention and deletion policies match your requirements.
