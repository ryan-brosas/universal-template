<!-- capsule-v2 -->
# Signal-relay dual-path PID 1 — how does one shell entrypoint stay a faithful signal relay in BOTH its bootstrap path and its steady-state path?

**Source:** railway-template-nexus3 EPL-1.0 `main@18e177a6563436ca1cd7e44bc2fa5648f6735c58`; Codebase Memory `railway-template-nexus3`. **Question:** When the container shell is PID 1, how do you avoid the classic "signals black-hole and the platform SIGKILLs after 30 s" bug across the two different ways this entrypoint starts the server?

## Exec-fast-path vs fork+trap bootstrap path
**Path/Symbol:** `entrypoint.sh:6-11` (both start paths), `Dockerfile:7` (exec-form ENTRYPOINT), `entrypoint.sh:23` (final foreground wait).
**Signature:** `/bin/sh` under `set -eu`; `ENTRYPOINT ["/usr/local/bin/nexus-railway-entrypoint"]` — JSON-array form so no `sh -c` wrapper interposes between the platform signal and this script.
**Data Shape:** Branch predicate is volume-marker existence (`[ -f .railway-admin-configured ]`). Fast path: `exec` replaces the shell with the JVM → shell ceases to exist. Bootstrap path: server backgrounded (`&`), `$!` captured into `pid`, `trap` installed BEFORE any long-running work, final `wait "$pid"` parks the shell in foreground.

### Decisive source
```sh
if [ -f /nexus-data/.railway-admin-configured ]; then
  exec su-exec nexus /opt/sonatype/nexus/bin/nexus run
fi
su-exec nexus /opt/sonatype/nexus/bin/nexus run &
pid=$!
trap 'kill -TERM "$pid" 2>/dev/null || true; wait "$pid"' TERM INT
...
wait "$pid"
```

**Flow:** steady state (marker exists) ⇒ `exec` — the JVM *becomes* PID 1's replacement image, so TERM lands on the JVM directly; there is no shell left to relay and none is needed. First boot ⇒ fork server, capture pid, install TERM+INT trap, do the bootstrap work, then `wait "$pid"` forever; on TERM the trap forwards TERM to the child (swallowing kill-failure with `|| true` so a already-dead child cannot kill the trapper under `set -eu`), reaps it, and the post-trap `wait` returns the child's exit status — which becomes the script's own exit code.
**Invariant:** exactly ONE termination discipline is live at any moment, chosen by the marker. Breaking either half causes the same visible symptom (platform kill-timer fires): using `&`+`wait` in the fast path leaves a useless shell as PID 1 that must translate signals manually; forgetting the trap in the bootstrap path leaves TERM arriving at a shell blocked in `wait`, which POSIX delivers only after `wait` returns — i.e. never within the grace period. The `|| true` inside the trap is load-bearing under `set -eu`; removing it turns a benign double-signal race into a premature shell death that orphans the JVM.
**Probe:** no runtime harness exists upstream (recorded caveat). Behavioral probe executed by this pass (gate 5): `env -u NEXUS_ADMIN_PASSWORD sh entrypoint.sh` exits nonzero at the `:?` gate BEFORE reaching any branch — proving the gate precedes path selection. Mechanical pins: `grep -c 'exec su-exec' entrypoint.sh` ≥ 1, `grep -c "^trap " entrypoint.sh` = 1, `grep -c '^wait "\$pid"$' entrypoint.sh` = 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "railway-template-nexus3", query: "railway deploy restart policy", limit: 10 });
```
(Graph is config-shaped: resolves the `railway.deploy` Class over `railway.toml:4-9` — the restart policy that consumes these exit codes; the shell flow itself is confirmed by direct whole-file read.)

## Verdict
Adopt the dual-path discipline: exec-replace when no bootstrap work remains, fork+trap+final-wait exactly when it does; install traps before any blocking call and end the script in a bare `wait`. Adapt the child command and marker path. Omit nothing here — this pattern ports whole. Coverage caveat: upstream ships no signal-path test; behavior verified by reading + the gate-order probe, not by sending live signals to a booted container.
