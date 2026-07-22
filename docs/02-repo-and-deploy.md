# Repo + deploy plan (adapted from the Cursor video)

The Cursor walkthrough ([source-transcript-cursor-github.md](source-transcript-cursor-github.md))
is a **React app on macOS deployed to Firebase**. We're building a **Python agent on
Windows**. This doc records what carries over, what doesn't, and where I'm deliberately
deviating from the video's advice.

## What carries over — all of it useful

| Video step | Our version |
|---|---|
| Project directory + `cd` | Already done — `C:\Users\buyer\claude python agent` |
| Terminal cheat sheet | Good idea, kept in [cheatsheet.md](cheatsheet.md) |
| `git init` → first commit → remote → push | **Applies exactly.** This is the core. |
| The commit loop (`add` / `commit -m` / `push`) | **Applies exactly.** Daily habit. |
| Branches for experiments, roll back if broken | Applies — we'll branch per phase |
| Run locally before deploying | Applies (a CLI command instead of `localhost:3000`) |

## What does not carry over

**Node.js, Homebrew, `npx create-react-app`, Firebase.** All React/macOS-specific.

- **Homebrew doesn't exist on Windows.** Skip Step 2 entirely — git 2.55 and Python 3.14
  are already installed on this machine. Nothing to install.
- **We're not building a React front end.** No Node, no npm, no `npm start`, no
  `npm run build`.
- **Firebase Hosting only serves static files.** It cannot run Python. Deploying our
  agent there is not a thing that works.
- Side note: `create-react-app` has been deprecated since 2023 and the React team no
  longer recommends it — so that step is stale even for React projects. Not our problem,
  but worth knowing if you follow that video for something else later.

## Three places I'm deviating from the video's advice

### 1. The repo must be PUBLIC, not private

The video says private "so people can't steal your code." That's the wrong call here and
it's not close. **The entire point of this project is that a hiring manager can look at
it.** A private repo is an invisible repo — you'd be building a resume piece nobody can
open. Nobody is going to steal a portfolio analyzer.

This is exactly why the aim doc committed to synthetic sample data and no real client
information. Public repo, nothing sensitive in it, by design.

### 2. Don't grant the token read+write on everything

The video says max out every permission "so that we never run into errors." That's a key
to your whole GitHub account sitting in a text file. Fine-grained tokens exist precisely
so you don't do this.

**We're skipping the token entirely.** On Windows, Git Credential Manager ships with Git
and handles auth through a browser sign-in — no token to generate, copy, lose, or leak.
Just `git push` and approve in the browser once.

If you ever *do* need a token, the minimum is **Contents: read and write** on the single
repo. Nothing else.

### 3. Never put a token in the remote URL

The video's `https://<username>:<token>@github.com/...` writes your token into
`.git/config` in plain text, and it leaks into terminal history. Use the clean URL and
let the credential manager hold the secret.

## Secrets — non-negotiable for this project

Our project has an `ANTHROPIC_API_KEY`. A public repo makes leaking it costly and
permanent (GitHub history keeps deleted files; scrapers find keys within minutes).

- `.env` for the key, `.env.gitignore`d before the first commit
- `.env.example` committed with a blank placeholder, so the repo is still runnable
- The key is read from the environment at runtime, never hardcoded, never in a docstring

I'll set this up before we make the first commit, not after.

## Getting a live link anyway

The video's payoff is a shareable URL, and that instinct is right — a link is worth more
on a resume than a repo alone. Our path there:

| Phase | Deliverable | Live link |
|---|---|---|
| Phase 1 | Python CLI producing an HTML report | The sample report can be served on **GitHub Pages** straight from the repo — free, no signup, one setting |
| Phase 2 | Streamlit questionnaire + IPS generator | **Streamlit Community Cloud** — free, connects directly to a public GitHub repo, redeploys on every push |

Streamlit Community Cloud is the real equivalent of what Firebase did in that video:
point it at the repo, get a public URL, and every `git push` updates the live app. It runs
Python, which Firebase Hosting cannot.

## Order of operations

1. `git init`, `.gitignore`, `.env.example`, README skeleton → **first commit**
2. Create the public GitHub repo, connect the remote, push
3. Build Phase 1 analytics core → commit as we go
4. Add the two agents → commit
5. GitHub Pages for the sample report
6. Phase 2 Streamlit app → Streamlit Community Cloud

Commits happen continuously, not at the end. A resume repo with one giant "initial
commit" reads as a dump; a repo with a readable commit history reads as someone who works
like an engineer.
