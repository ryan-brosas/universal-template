<!-- capsule-v2 -->
# Errexit fail-fast budget — how does a bootstrap script guarantee that ANY failed step aborts the whole run before later steps execute?

**Source:** railway-template-nexus3 EPL-1.0 `main@18e177a6563436ca1cd7e44bc2fa5648f6735c58`; Codebase Memory `railway-template-nexus3`. **Question:** How does a multi-step credential-rotation bootstrap ensure no step is skipped and no silent failure survives, and what POSIX corner lets an error slip through anyway?

## set -eu as the failure budget for every subsequent command
**Path/Symbol:** `entrypoint.sh:2` (`set -eu`), `entrypoint.sh:14` (curl under `if`, the deliberate exemption site), `entrypoint.sh:17` (timeout verdict), `entrypoint.sh:19-20` (bootstrap curls relying on the budget), `railway.toml:7-8` (`restartPolicyType="ON_FAILURE"`, `restartPolicyMaxRetries=10`).
**Signature:** `set -eu` on line 2 of a `/bin/sh` script. `-e`: any command failing (nonzero exit) aborts the shell. `-u`: expansion of unset variables is fatal. Every mutating curl uses `-fsS` so HTTP ≥400 (`-f`) or transport failure (`-sS` still prints errors) produces nonzero exit → instant abort.

### Decisive source
```sh
#!/bin/sh
set -eu
: "${NEXUS_ADMIN_PASSWORD:?NEXUS_ADMIN_PASSWORD is required}"
...
[ "$ready" = 1 ] || { echo 'Nexus bootstrap timed out' >&2; exit 1; }
initial=$(cat /nexus-data/admin.password)
curl -fsS -u "admin:$initial" -X PUT ... >/dev/null
curl -fsS -u "admin:$NEXUS_ADMIN_PASSWORD" -X PUT ... >/dev/null
touch /nexus-data/.railway-admin-configured
```

**Flow:** arm errexit FIRST → env gate (see env-gate-fail-closed) → poll loop where the probe curl runs under `if` → loud `exit 1` on timeout → rotation curl → anonymous-disable curl → marker touch. Under `-e`, each `-fsS` curl is a checkpoint: rotation failing means anonymous-disable never fires and the marker never lands, so the next boot re-runs the whole ladder.
**Invariant:** NO step after `set -eu` can be silently skipped, because every one of them either succeeds or kills the script. Two consequences a porter must not break: (1) the only tolerated non-zero command inside the flow is the readiness PROBE, which is deliberately placed under `if` — POSIX exempts commands tested by `if`/`while` from errexit, so transient probe failures during server warm-up cannot kill the bootstrap; (2) the same exemption is a TRAP elsewhere — a porter who wraps a MUTATING curl in `if curl ...; then` converts a hard failure into a taken-else branch that proceeds to touch the marker half-bootstrapped. Mutations must stay bare statements; only probes may sit under conditionals. The platform completes the contract: `exit 1` mid-bootstrap hands control to ON_FAILURE ×10 restarts (each with a fresh 900 s window), so fail-fast composes with the retry policy instead of fighting it.
**Probe:** EXECUTED this pass at pin: `env -u NEXUS_ADMIN_PASSWORD sh entrypoint.sh` → rc=1, stderr `NEXUS_ADMIN_PASSWORD is required`, `/nexus-data` never created (the `-u`+`:?` arm proves the budget arms before any side effect). Mechanical pins (executed): `grep -cF 'set -eu' entrypoint.sh` = 1 (line 2), `grep -c '127\.0\.0\.1' entrypoint.sh` = 3, `grep -c '^trap ' entrypoint.sh` = 1.

## Get live surrounding code
**Retrieve:** search_graph is BM25 over Function-class tokens and returns total:0 for shell keywords on this config-shaped graph (verified live: query "errexit set -e abort fail fast" → 0). Use the line-exact primitive:
```
codebase-memory-mcp cli search_code '{"project":"railway-template-nexus3","pattern":"set -eu","limit":4}'
```
→ resolves Module `entrypoint` lines `1-24`, match at `"2"` (verified rank-1 this pass).

## Verdict
Adopt: `set -eu` as the first statement of any mutating bootstrap; keep mutation commands bare (errexit-armed) and put ONLY liveness probes under `if`. Pair the resulting exits with the platform's ON_FAILURE retry policy. Adapt variable names/endpoints per product; omit nothing structural.
