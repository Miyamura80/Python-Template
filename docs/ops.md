# Documentation Translation Operations

Automated translation of docs via the
[Jules Translation Sync](../.github/workflows/jules-sync-translations.yml)
GitHub Actions workflow.

## How it works

1. A push to `main` that changes English source docs (`docs/content/**/*.mdx`
   or `meta.json`, excluding `*.<lang>.mdx` and `meta.<lang>.json`) triggers the workflow.
2. The workflow detects the changed English files via `git diff`.
3. A single [Jules API](https://jules.google) session is created with a
   prompt that instructs Jules to update (or create) every `.<lang>.mdx`
   translation for each changed file.
4. Jules opens **one PR** containing all locale updates.

## Required secrets

Configure these in **Settings > Secrets and variables > Actions** in GitHub:

| Secret          | Description                                                  |
|-----------------|--------------------------------------------------------------|
| `JULES_API_KEY` | Google Jules API key. Generate at <https://jules.google> Settings. |

## Adding or removing a language

Edit the `SUPPORTED_LANGS` env var in
`.github/workflows/jules-sync-translations.yml`:

```yaml
env:
  SUPPORTED_LANGS: "es,ja,zh"
```

- **Add** a locale by appending its ISO 639-1 code (e.g. `"es,ja,zh,pt"`).
- **Remove** a locale by deleting it from the list.

That single line is the only change needed. The workflow, the change-detection
filter, and the Jules prompt all derive from this variable.

## Failure modes and how to retry

| Failure                         | Symptom                                       | Resolution                                                            |
|---------------------------------|-----------------------------------------------|-----------------------------------------------------------------------|
| **Jules API key invalid/expired** | Step "Create Jules translation session" fails with HTTP 401/403 | Rotate the key at <https://jules.google> and update the `JULES_API_KEY` secret. |
| **Jules source not found**      | HTTP 404 on session creation                  | Verify the Jules GitHub App is installed on the repo. Check the source name with `GET /v1alpha/sources`. |
| **Jules session fails**         | Poll step exits with `FAILED` state           | Check the Jules session UI (link in workflow logs) for details. Fix the underlying issue and re-run the workflow. |
| **Poll timeout**                | Workflow times out after ~30 min of polling    | The Jules session may still be running. Check the Jules UI. If it completed, the PR exists. If not, re-run the workflow. |
| **Transient 5xx errors**        | Warnings in logs, then success                | Built-in retry with exponential back-off handles these automatically. |

### Manual retry

1. Go to **Actions > Jules Translation Sync** in GitHub.
2. Find the failed run.
3. Click **Re-run failed jobs**.

If the English docs have since changed again, a new push to `main` will
trigger a fresh run automatically.

## Verifying the Jules source identifier

The workflow constructs the source as `sources/github/{owner}/{repo}` from
`github.repository`. To verify this matches your Jules configuration:

```bash
curl -H "x-goog-api-key: $JULES_API_KEY" \
  https://jules.googleapis.com/v1alpha/sources
```

If the format differs, update the `SOURCE` variable in the
"Create Jules translation session" step.
