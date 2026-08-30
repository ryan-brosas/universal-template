# Security and dependency surfaces - verified mechanics

All commands verified against gh 2.98.0 (2026-08-30). Read state before every
mutation; write only what the project earns; report plan-unavailable surfaces
as unavailable.

## Read state

| Surface | Read | Enabled signal |
|---|---|---|
| Dependabot alerts | `gh api repos/O/R/vulnerability-alerts` | HTTP 200 (404 = disabled/unavailable) |
| Security updates | `gh api repos/O/R/automated-security-fixes` | 200 on, 404 off |
| Private vulnerability reporting | `gh api repos/O/R/private-vulnerability-reporting` | `{"enabled": true}` |
| CodeQL default setup | `gh api repos/O/R/code-scanning/default-setup` | `state: configured` |
| Repo security block | `gh api repos/O/R --jq .security_and_analysis` | per-feature `status: enabled` |

`security_and_analysis` covers: `secret_scanning`,
`secret_scanning_push_protection`, `secret_scanning_non_provider_patterns`,
`dependabot_security_updates`, `vulnerability_alerts`. Public repos get secret
scanning free; other features depend on plan.

## Enable (PATCH/PUT; owner token required)

```bash
# one JSON body per call, then read back the same field
gh api -X PATCH repos/O/R --input - <<<'{"security_and_analysis":{"secret_scanning":{"status":"enabled"},"secret_scanning_push_protection":{"status":"enabled"},"secret_scanning_non_provider_patterns":{"status":"enabled"},"dependabot_security_updates":{"status":"enabled"},"vulnerability_alerts":{"status":"enabled"}}}'
gh api -X PUT repos/O/R/private-vulnerability-reporting --input - <<<'{"enabled": true}'
```

Private vulnerability reporting needs `SECURITY.md` pointing at it (never an
invented email). CodeQL default setup (prefer over a custom workflow):

```bash
gh api -X POST repos/O/R/code-scanning/default-setup \
  --input - <<<'{"state":"configured","languages":["python","actions"],"query_suite":"default"}'
# 202 = provisioning; poll the GET until state becomes "configured"
```

Available languages are listed in the GET response; request only languages the
repository actually contains.

## Dependabot

`.github/dependabot.yml` per ecosystem actually present. For SHA-pinned
Actions: `package-ecosystem: github-actions`, weekly schedule, group
minor+patch (majors stay separate), conventional commit prefix so the title
automation classifies the PR. Order matters: labels referenced by the config
must already exist.

## Boundaries

- Never weaken an enabled protection to make automation easier.
- Never claim a feature is enabled without reading its state back.
- Path-filtered scanners (e.g. a workflows-only zizmor audit) stay OPTIONAL
  required checks - a skipped workflow leaves a required check pending.
