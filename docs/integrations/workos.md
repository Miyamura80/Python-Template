### WorkOS Dashboard AuthKit setup for local social login (no SSO)

#### Prereqs
- You have an AuthKit app in the correct environment (Staging/Production).
- You know your AuthKit Client ID (`VITE_WORKOS_CLIENT_ID`).

#### 1) Allowed Redirect URIs
- Go to `Authentication → Redirects`.
- Add `http://localhost:8080/callback`.
- Set it as **Default** while testing locally.
- Keep other redirect URIs for prod as needed.

#### 2) Allowed Origins (CORS)
- Go to `Authentication → Sessions`.
- Find **Cross-Origin Resource Sharing (CORS)** → **Manage**.
- Add `http://localhost:8080` (and optionally `http://127.0.0.1:8080`).
- Save.

#### 3) Providers (social)
- Go to `Authentication → Providers`.
- Open your provider (e.g., Google), toggle **Enable**.
- For quick testing choose **Demo credentials**; for real apps choose **Your app’s credentials** and supply keys.
- Save.

#### 4) Frontend env
- In `.env` set: `VITE_WORKOS_CLIENT_ID=<your AuthKit Client ID for this env>`.
- Restart `npm run dev` after editing `.env`.

#### 5) Verify flow
- Run locally, open `http://localhost:8080/editor`, click **Log in**, select provider.
- If you see CORS to `api.workos.com/user_management/authenticate`, re-check:
  - Allowed Origins (step 2)
  - Redirect URI present/default (step 1)

#### Notes
- You do **not** need SSO enabled for social login.
- Use localhost values in Staging; use production URLs in Production.
- If “Allowed Origins” isn’t visible, ask WorkOS support to enable it for your AuthKit app.