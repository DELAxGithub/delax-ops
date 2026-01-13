# delax-ops

Operational nucleus for DELAx. This repo holds shared ops docs, DB schemas, and automation that power other repos.

## Scope
- ops/db-schema: database design and migrations (no secrets)
- ops/automation: scheduled jobs and automation scripts (secrets via env/GitHub)
- ops/media: shared media pipeline utilities

## References
See references/repos.md for the current repo map and labels.

## Dependencies
This repo does not vendor shared packages. Reference them instead:
- delax-shared-packages: https://github.com/DELAxGithub/delax-shared-packages
