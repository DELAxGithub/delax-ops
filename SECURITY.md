# Security Policy

## Rules
- Never commit secrets or tokens.
- Use .env files locally and keep them out of git.
- Store production secrets in the deployment platform or GitHub Secrets.

## Rotation flow (summary)
1) Rotate keys at the provider.
2) Update deployments and local configs.
3) Remove leaked files from git history if needed.
4) Validate with Secret Scanning alerts.

## Local ignores
Add these to .gitignore in any repo:
- .env
- .env.*
- *.local.*
- settings.local.json
