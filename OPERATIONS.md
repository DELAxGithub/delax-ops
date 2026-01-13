# Operations Rules

## 1) Reference-first policy
- New work starts by referencing existing repos and modules.
- If a module exists, reuse it before creating a new one.
- Shared assets live in their original repo; link here until a migration is agreed.

## 2) Extraction policy (history-preserving)
- Default: git filter-repo with path-only extraction.
- Use a clean clone under `/Users/delaxstudio/src/_extract/`.
- Merge into delax-ops with `--allow-unrelated-histories` and a clear merge message.
- Do not use `cp -R` unless explicitly choosing to discard history.

## 3) Secrets and safety
- Never commit secrets or tokens.
- If a secret is detected:
  1) Rotate at provider
  2) Update deployments
  3) Remove from git history
  4) Confirm GitHub Secret Scanning
- Add these to .gitignore in every repo:
  - .env
  - .env.*
  - *.local.*
  - settings.local.json

## 4) Archive and delete policy
- Archive first; delete only after 30+ days with no dependency.
- Empty repos are archived; delete only with explicit confirmation.

## 5) Tag before destructive actions
- Before history rewrites or force pushes, tag:
  - pre-sanitize-YYYYMMDD
- Record actions in the repo README or a change log.
