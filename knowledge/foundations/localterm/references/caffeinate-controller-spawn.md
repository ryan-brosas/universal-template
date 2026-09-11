<!-- capsule-v2 -->
# Caffeinate controller + platform spawn — how do I own exactly one keep-awake process across macOS and Linux?

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853f4bed28f7a0cca14dd1c02f54b86d6fa`; Codebase Memory `localterm`. **Question:** How do I spawn/kill a single power-assertion process safely, including Linux's forked child and unexpected death?

## Single-handle lifecycle with identity-checked exit
**Path/Symbol:** `packages/server/src/caffeinate-controller.ts:CaffeinateController.start` (55–67) / `.stop` (69–75); `packages/server/src/caffeinate-platform.ts:spawnKeepAwakeProcess` (51–89) + `keepAwakeSpawnTarget` (24–34) + `detectCaffeinateSupported` (42–49).
**Signature:** `setActive(enabled: boolean): void`; `handle: CaffeinateProcessHandle { kill(): void; onExit(cb): void }`; `keepAwakeSpawnTarget(platform?): KeepAwakeSpawnTarget | null`.
**Data Shape:** `active === (this.handle !== null)` — no separate flag; target `{binary, args, detached}` = darwin `caffeine -dims detached:false` vs linux `systemd-inhibit … tail -f /dev/null detached:true` vs null elsewhere.

### Decisive source
```ts
// controller :59-65 — only an UNEXPECTED death of the CURRENT handle flips state
handle.onExit(() => {
  if (this.handle !== handle) return;   // replaced or intentionally stopped
  this.handle = null;
  this.emit("change");
});
```
```ts
// platform :69-80 — group kill for the Linux fork
kill: () => {
  if (target.detached && child.pid !== undefined) {
    try { process.kill(-child.pid, "SIGTERM"); return; }
    catch { /* group already gone; fall through to direct kill */ }
  }
  child.kill();
}
```

**Flow:** setActive(true) → start (idempotent: existing handle ⇒ return) → spawn per platform target → onExit listener registered immediately. setActive(false) → stop: capture handle, NULL THE FIELD FIRST, then kill (the identity check makes the intentional-stop exit a no-op). Unsupported platform ⇒ setActive returns without spawning AND the null-target fallback handle fires `onExit` via `process.nextTick` so a spawn on a wedged host records never-held instead of hanging. `onExit` registers BOTH `exit` and `error` child events — `error` covers failed spawn (binary missing, e.g. non-systemd host masquerading as supported). Detection is capability-only (macOS always; Linux iff `systemd-inhibit` on PATH at CALL time — detection boolean ≠ resolved path; spawn re-resolves PATH).
**Invariant:** at most ONE live keep-awake process; the identity check (`this.handle !== handle`) is what separates "process died unexpectedly" (flip state + rebroadcast) from "we replaced/killed it" (ignore); Linux MUST be spawned detached + group-killed or systemd-inhibit's `tail -f /dev/null` child orphans to init.
**Probe:** `packages/server/tests/caffeinate-controller.test.ts::"is idempotent — enabling twice spawns only one process"` (:53), `"flips inactive and emits change when the process dies unexpectedly"` (:91), `"ignores the exit of a process it already stopped"` (:103); `caffeinate-platform.test.ts::"targets systemd-inhibit on Linux detached (group kill reaps the child)"` (:22), `"is supported on Linux only when systemd-inhibit is on PATH"` (:57).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "localterm", query: "keepAwakeSpawnTarget", limit: 5 });
// → keepAwakeSpawnTarget @ caffeinate-platform.ts:24-34 (exact)
await mcp.codebase_memory.trace_path({ project: "localterm", function_name: "localterm.packages.server.src.caffeinate-controller.CaffeinateController.setActive", direction: "inbound", depth: 1 });
```

## Verdict
Adopt handle-identity exit filtering and detached+group-kill semantics verbatim; adapt binary/args tables per host; omit the caffeinate/systemd-inhibit specifics where the platform has a native power-assertion API (inject a spawnProcess). Direct tests pin idempotency, both exit paths, and per-platform targets.
