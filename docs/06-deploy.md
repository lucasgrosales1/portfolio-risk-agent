# Deploying to Streamlit Community Cloud

Free hosting that runs the Python app directly from the public GitHub repo and
redeploys on every push. The result is a public URL you can put on a resume.

## Prerequisites (already done)

- Repo is **public**: github.com/lucasgrosales1/portfolio-risk-agent ✓
- `streamlit_app.py` at the repo root (the entry point) ✓
- `requirements.txt` at the root (Community Cloud installs from this) ✓
- `src/` added to the path in `streamlit_app.py` so `pra` imports without a
  local install ✓

## Steps

1. Go to **https://share.streamlit.io** and click **Sign in with GitHub**.
   Authorize Streamlit to read your repositories (read-only).

2. Click **Create app** → **Deploy a public app from GitHub**.

3. Fill in:
   - **Repository:** `lucasgrosales1/portfolio-risk-agent`
   - **Branch:** `main`
   - **Main file path:** `streamlit_app.py`
   - **App URL:** pick a custom slug if you like (e.g. `advisor-workbench`).

4. *(Optional)* **Advanced settings**:
   - **Python version:** 3.12 or 3.13 (either works).
   - **Secrets:** only if you want AI-written commentary instead of the
     rule-based default. Paste, in TOML form:
     ```toml
     ANTHROPIC_API_KEY = "sk-ant-..."
     ```
     Without this, the app runs fine — every number is identical, only the
     prose differs. **Don't paste a key anywhere public.**

5. Click **Deploy**. First build takes a few minutes (installing pandas,
   yfinance, streamlit). Watch the log; when it finishes you get the URL.

## After it's live

- The first portfolio load fetches market data, so it's slow the first time,
  then cached.
- **Every `git push` to `main` auto-redeploys.** No separate deploy step.
- If a build fails, the log names the cause — usually a dependency version.
  Check `requirements.txt` floors against the chosen Python version.

## Put it on the resume

- Add the live URL to the README (top) and to the resume line.
- The repo README + the live app together are the portfolio piece: one shows
  how it's built, the other lets a recruiter use it without cloning anything.
