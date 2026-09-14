---
title: local-service-durability
summary: "Use when installing, updating, hardening, or recovering a long-lived local service such as a systemd --user unit, healthcheck timer, or supervised daemon; supplies supervisor ownership, crash-loop-safe recovery, and regeneration-safe local config."
kind: playbook
---

# Local Service Durability

## Core Principle

Exactly one thing must own the process lifecycle. Decide the owner once, keep the
installed artifact and local configuration separate, and verify the behavior that
changed. Use fault injection for recovery guarantees; reading the unit is not proof.

## When to Use / NOT

- A daemon must survive crashes, reboots, package updates, or a tool reinstall.
- Writing or repairing the healthcheck/autoheal path for a supervised service.
- A tool's own installer rewrites the unit file that runs it.
- Verifying an update of a service a supervisor already owns.

**NOT when:** the process is a one-shot CLI, or it runs in a container whose
orchestrator already owns restart and health (`shipping-and-launch`).

## Workflow

1. **Name the owner and its artifact** from observed state (`systemctl --user
   show`, process parentage, pidfile), not from documentation. Resolve the exact
   runtime, package root, and package-manager prefix from the effective unit and
   running process. The caller's `command -v` or package-manager prefix may select
   a different installation.
2. **Update the service-owned artifact.** When files can be replaced in place,
   stop the unit, invoke the exact runtime or package-manager prefix, then start
   the unit. A tool self-updater is safe only after confirming that it targets the
   same artifact and delegates restart to the supervisor. Otherwise it can update
   a dormant copy or spawn an untracked replacement.
3. **Keep local edits in drop-ins**, never in a file the installer generates
   (`<unit>.service.d/override.conf`). After any regeneration, re-check the
   effective properties with `systemctl show -p ExecStart -p ExecStartPre -p Restart`:
   regeneration can add startup preflight that delays or blocks boot.
4. **Harden the restart policy:** `Restart=always` (not `on-failure`), a short
   `RestartSec`, linger for user units that must survive logout, and deliberate
   start-limit bounds.
5. **Make recovery clear the limiter.** A unit in `start-limit-hit` refuses both
   `start` and `restart` ("start of the service was attempted too often") until
   its failed state is cleared. Health loops must run `reset-failed` *before*
   `restart`; `try-restart` alone neither starts an inactive unit nor clears the
   limit.
6. **Respect the cgroup.** The default `KillMode=control-group` kills children on
   restart, so in-memory sessions and PTYs are lost. Move state that must survive
   into its own scope or a terminal multiplexer instead of weakening the unit
   globally.
7. **Verify by fault injection,** not inspection: kill -9 and confirm a new pid
   inside the expected window; stop the unit and confirm the healthcheck revives
   it; drive a throwaway unit into `start-limit-hit` to prove the reset path.

## Installer Side Effects

Running an install or regeneration command "just to check" mutates external
state: network exposure (reverse proxy, tailnet, port mapping), extra daemons,
rc-file rewrites. Snapshot the observable state first, diff after, and revert
anything that was not requested.

## Red Flags

- A tool self-update used without confirming its artifact target and supervisor integration.
- A healthcheck whose only action is `try-restart`.
- Local tuning written into an installer-generated unit file.
- "Durable" claimed without a kill test or a real stop/revive cycle.
- An install path executed for verification with no before/after state diff.

## Verification

For an update, evidence is the version at the service-owned artifact, effective
`ExecStart`, a new supervised pid, a healthy readiness endpoint, a representative
operation, and confirmation that no extra instance remains. For recovery changes,
add fault-injection output and restart counters.

## References

- `references/systemd-user-services.md`: unit and drop-in recipes, the
  `reset-failed` recovery pattern, and a copy-paste verification command set.
