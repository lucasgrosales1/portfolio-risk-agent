# Terminal cheat sheet

The video's best practical tip: keep the commands you run over and over in one place.
Windows / PowerShell versions, since that's what this machine runs.

## Getting back into the project

```powershell
cd "C:\Users\buyer\claude python agent"
```

Run this first in any fresh terminal. If the prompt doesn't show the project folder,
you're not in it, and nothing else here will work right.

## The commit loop — the one you'll use daily

```powershell
git status          # what changed?
git add .           # stage everything
git commit -m "describe what actually changed"
git push origin main
```

`git status` before `git add .` is the habit worth building — it's how you catch yourself
about to commit a `.env` file.

## Seeing where you are

```powershell
git branch          # which branch am I on?
git log --oneline   # commit history, one line each
git diff            # what changed but isn't staged yet
```

## Branches (for trying something risky)

```powershell
git checkout -b phase-2-ips    # create and switch to a new branch
git checkout main              # switch back
git merge phase-2-ips          # bring the work into main once it's good
```

## Python environment

```powershell
python -m venv .venv                    # create the virtual environment (once)
.\.venv\Scripts\Activate.ps1            # activate it (every session)
pip install -r requirements.txt         # install dependencies
deactivate                              # leave the venv
```

If activation is blocked by execution policy, run this once as your user:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

## Running the project

```powershell
python -m advisor.report --portfolio data/sample_portfolio.csv
```

(Exact command will firm up as we build — this line gets updated then.)

## Undo buttons

```powershell
git restore <file>              # discard uncommitted changes to a file
git reset --soft HEAD~1         # undo last commit, keep the changes staged
git revert <commit-hash>        # safely undo a commit that's already pushed
```

`git revert` is the safe one for anything already on GitHub. Avoid `reset --hard` unless
you're certain — it deletes work with no recovery.
