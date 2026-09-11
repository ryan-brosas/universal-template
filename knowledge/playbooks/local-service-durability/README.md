---
title: local-service-durability
summary: "Use when installing, updating, hardening, or recovering a long-lived local service such as a systemd --user unit, healthcheck timer, or supervised daemon; supplies supervisor ownership, crash-loop-safe recovery, and regeneration-safe local config."
kind: playbook
---

# Local Service Durability

## Core Principle

Exactly one thing must own the process lifecycle. Decide the owner once, keep the
installed artifact and the local configuration in different places, and prove
recovery by killing the process, never by reading the unit.

## When to Use / NOT

- A daemon must survive crashes, reboots, package updates, or a tool reinstall.
- Writing or repairing the healthcheck/autoheal path for a supervised service.
- A tool's own installer rewrites the unit file that runs it.
- Verifying an update of a service a supervisor already owns.

**NOT when:** the process is a one-shot CLI, or it runs in a container whose
orchestrator already owns restart and health (`shipping-and-launch`).

## Workflow

1. **Name the owner** from observed state (`systemctl --user show`, process
   parentage, pidfile), not from documentation.
2. **Update under the supervisor.** Change the installed artifact with its
   package manager and restart the unit. Never use the tool's self-update or
   install path while a supervisor owns the daemon: it stops the tracked pid and
   spawns a detached replacement that races the restart policy, leaving two
   instances and a stale pidfile.
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

- The tool's own update command used while a supervisor owns the daemon.
- A healthcheck whose only action is `try-restart`.
- Local tuning written into an installer-generated unit file.
- "Durable" claimed without a kill test or a real stop/revive cycle.
- An install path executed for verification with no before/after state diff.

## Verification

Evidence is fault-injection output (pid change window, restart counters), the
effective `systemctl show` values, a healthy readiness endpoint, and confirmation
that nothing extra was exposed or left running.

## References

- `references/systemd-user-services.md`: unit and drop-in recipes, the
  `reset-failed` recovery pattern, and a copy-paste verification command set.
