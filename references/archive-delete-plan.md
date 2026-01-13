# Archive → Delete Plan (PM repos)

Policy: archive first, delete after 30+ days with no dependency.

## Archived (current)
- delax-unified-pm
- PMliberary
- PMplatto
- DELAxPM

## Delete candidates (after 30+ days)
- delax-unified-pm (DB design extracted to delax-ops)
- PMliberary (DB design extracted to delax-ops)
- PMplatto (automation extracted to delax-ops)
- DELAxPM (DB schema extracted to delax-ops)

## Preconditions
- Secrets rotated and confirmed
- delax-ops contains the needed schema/automation
- No runtime dependency from active apps
