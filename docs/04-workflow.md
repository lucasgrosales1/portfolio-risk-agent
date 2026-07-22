# How this actually works — save, run, ship

End-to-end process, from "files on your laptop" to "link on your resume." Written for
Windows / PowerShell, which is what this machine runs.

---

## Where everything lives

```
C:\Users\buyer\claude python agent\      ← workspace (transcripts stay here, never public)
└── portfolio-risk-agent\                ← THE REPO. This folder is the project.
    ├── .git\                            ← version history (hidden)
    ├── .venv\                           ← Python dependencies (not committed)
    ├── .env                             ← your API key (NEVER committed)
    ├── src\pra\                         ← the code
    ├── data\                            ← sample portfolios
    ├── reports\                         ← generated HTML reports
    └── docs\                            ← the planning docs
```

That one folder syncs to `github.com/lucasgrosales1/portfolio-risk-agent`.

---

## Saving happens at three levels

People new to git usually conflate these. They're separate, and understanding the
difference is most of what git anxiety is.

**Level 1 — the file on disk.** When I write a file or you save in Cursor, it's on your
hard drive immediately. Nothing else required. If your laptop is fine, your work is fine.

**Level 2 — the commit.** A labeled snapshot of every file at a moment in time. Commits
are what let you say "this worked yesterday, put it back." Nothing is committed until you
run the commit command — editing a file does *not* create one.

```powershell
git add .
git commit -m "add risk metrics module"
```

**Level 3 — the push.** Uploads your commits to GitHub. This is the backup, and it's what
makes the repo visible to anyone you send the link to.

```powershell
git push origin main
```

Rule of thumb: **commit whenever something works**, push at the end of a session. A commit
is free and takes three seconds. There is no such thing as committing too often.

---

## Running it

Open the project in Cursor, then open a terminal inside it (Ctrl+`). Every session starts
the same way:

```powershell
cd "C:\Users\buyer\claude python agent\portfolio-risk-agent"
.\.venv\Scripts\Activate.ps1
```

You'll know the venv is active because your prompt gets a `(.venv)` prefix. That prefix
means Python is using this project's isolated dependencies instead of your system Python.

Then run a report:

```powershell
python -m pra.cli --portfolio data/sample_concentrated.csv --model balanced_growth
```

It writes `reports/concentrated.html` and opens it in your browser. Ten to twenty seconds,
most of it fetching prices. Second run is faster — prices are cached to disk.

To get a PDF: open the HTML, `Ctrl+P`, Save as PDF. The print stylesheet is built for
this, so it comes out as a clean one-pager rather than a mangled web page.

---

## The one-time setup you do yourself

Everything else I can do, but these need you:

1. **Connect the repo to GitHub.** I'll run `git init` and make the first commit locally.
   You create the empty repo at github.com/new named `portfolio-risk-agent`, set it to
   **Public**, and don't check any of the "initialize with" boxes.
2. **First push authenticates you.** Git Credential Manager opens a browser window, you
   sign into GitHub, done. No token to generate or store. This happens once.
3. **The API key, when we get there.** You create it at console.anthropic.com and paste it
   into the `.env` file yourself. Don't paste it into chat — I don't need to see it, and
   anything in chat is harder to keep track of than a single gitignored file.

---

## Getting it onto your resume

Five steps, roughly in order:

**1. Make the repo public and readable.** The README is the thing recruiters actually
read — most never open the source. It needs: one sentence on what the tool does, a
screenshot of a generated report, the "the LLM never produces a number" design note, and
run instructions someone can follow in two minutes.

**2. Publish the sample report to GitHub Pages.** Repo Settings → Pages → deploy from
`main` branch. Gives you a real URL like
`lucasgrosales1.github.io/portfolio-risk-agent/sample-report.html` — a live page showing
actual output, no cloning required. This is the equivalent of the Firebase live link from
the Cursor video, minus Firebase.

**3. Write the resume line.** Something in this shape:

> **Portfolio Risk Agent** — Python tool generating client-ready portfolio risk reports:
> concentration analysis, volatility, max drawdown, Sharpe, beta, and tax-aware
> rebalancing with long/short-term gain treatment. AI-generated commentary is constrained
> to computed figures and passes an automated compliance-language review.
> `github.com/lucasgrosales1/portfolio-risk-agent`

The tax-aware and compliance-review clauses are the parts that separate this from a
dashboard. Keep them.

**4. Be able to talk about it.** Expect: *"walk me through how you calculate max
drawdown"* and *"how do you keep the AI from making things up?"* The second is the better
question and you have a real answer — the model receives computed metrics and is
explicitly checked against them. That's why we build it that way.

**5. Phase 2 gives you a live app.** The Streamlit IPS questionnaire deploys to Streamlit
Community Cloud from the public repo — a URL an interviewer can click and *use*, not just
read. That's the strongest version of this.

---

## What a working session looks like

1. Open Cursor, `cd` into the repo, activate the venv
2. We build a piece; I explain what it does and why
3. Run it, look at real output
4. `git add .` → `git commit -m "..."` → `git push origin main`
5. Repeat

The commit history becomes part of the artifact. A repo with one giant "initial commit"
reads as a code dump. A repo with twenty readable commits reads as someone who works like
an engineer — and costs nothing extra to produce.
