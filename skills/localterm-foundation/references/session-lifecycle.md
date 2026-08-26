<!-- capsule-v2 -->
# Session lifecycle policy — how do you reap dormant shells without ever killing a running command, and evict at the cap without stealing pinned sessions?

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853`; Codebase Memory `localterm`. **Question:** What is the pure decision policy that decides when a viewerless PTY dies, when it reschedules, and which session yields its slot at the concurrency cap?

## Grace timer + activity-state gate
**Path/Symbol:** `packages/server/src/session-lifecycle-policy.ts:SessionLifecyclePolicy` (whole file, 4–100): `startGrace` (27–57), `rearmGrace` (59–63), `cancelGrace` (65–71), `computeState` (77–80); state type `SessionActivityState = "running" | "alive-quiet" | "ready"` (`session-manager.ts:92`).
**Signature:** `constructor(getGraceMs: () => number | null, tearDown: (managed) => void, onSessionActivity: () => void)` — the policy owns NO timers table of its own; the timer lives on `managed.graceTimer`, and `getGraceMs` is a live resolver (`null` = never reap) so a config change applies on the NEXT arm without rewiring.
**Data Shape:** inputs on `ManagedSession`: `clients.size`, `pinned`, `graceTimer`, `parkedAt`, `lastOutputAt`, `hasForeground`, `session.isExited`. Constants: `SESSION_ACTIVITY_WINDOW_MS = 750` (constants.ts:435), default grace `SESSION_GRACE_MS = 30_000` (:416).

### Decisive source
```ts
// packages/server/src/session-lifecycle-policy.ts:39-55
    managed.graceTimer = setTimeout(() => {
      managed.graceTimer = null;
      managed.parkedAt = null;
      // Re-check on fire: reschedule while the shell is still doing something —
      // output still arriving (running), or a foreground program still alive
      // though quiet (alive-quiet) — so a closed tab never kills a running
      // command mid-stream, even after it's gone quiet. ...
      if (this.computeState(managed) !== "ready") {
        this.startGrace(managed);
        return;
      }
      this.tearDown(managed);
      this.onSessionActivity();
    }, graceMs);
```
**Flow:** last client detaches → hub calls `startGrace` → cancel-any-existing + stamp `parkedAt` → pinned sessions return immediately (park indefinitely, no timer) → `graceMs === null` parks with NO timer but keeps `parkedAt` for eviction ordering → on fire, re-check: `"running"` (output within 750ms) or `"alive-quiet"` (foreground program, quiet output) RESCHEDULES; only `"ready"` tears down. `computeState` is the same signal that colors the UI favicon, so reap decisions and what the user sees can never disagree.
**Invariant:** a shell is reaped only when (no clients) AND (no recent output) AND (no foreground program) — never mid-command; the fire-time re-check makes the armed duration an upper bound on latency, not a kill deadline; `rearmGrace` re-arms every viewerless live session after a config change (a finite value arms/resets, `null` cancels to park).
**Probe:** `tests/session-manager.test.ts::"keeps a dormant PTY alive while it's still producing output"` (:169 — 5 ticks of noteOutput across several grace windows), `::"keeps a dormant PTY alive while a foreground program runs quietly (alive-quiet)"` (:191), `::"never reaps a dormant shell while the grace window is Off, then reaps on rearm"` (:241 — null-park then flip to finite + rearmGrace), `::"reports the favicon-equivalent activity state on the session list"` (:320).

## Capacity + eviction ladder
**Path/Symbol:** `atCapacity` (11–20), `makeRoomForSession` (22–25), private `evictOldestDormant` (82–99).
**Signature:** `atCapacity(sessions: ReadonlyMap<string, ManagedSession>): boolean`; `makeRoomForSession(...): boolean` (mutates via eviction, then re-checks).
**Data Shape:** cap constant `MAX_CONCURRENT_SESSIONS = 64` (constants.ts:284). Eviction key: `managed.parkedAt ?? managed.createdAt`.
### Decisive source
```ts
// packages/server/src/session-lifecycle-policy.ts:14-18, 86-97
      // A dormant, non-pinned session can be evicted to make room. Pinned
      // sessions hold their slots (never silently reaped), so a full cap of
      // pinned sessions surfaces a real capacity error instead of a steal.
      if (managed.clients.size === 0 && !managed.pinned) return false;
...
      if (managed.clients.size > 0) continue;
      // Pinned sessions are never silently evicted — they're explicitly held.
      if (managed.pinned) continue;
      // Evict the parked session whose grace fires soonest (armed earliest); a
      // parked session with no timer is a fresh spawn nobody attached yet —
      // yield it only after all armed ones.
      const key = managed.parkedAt ?? managed.createdAt;
```
**Flow:** spawn → `makeRoomForSession` evicts ONE oldest dormant candidate if at cap → returns whether room now exists (`false` ⇒ caller refuses the spawn; WS path closes with a capacity code). Candidate filter: zero clients AND not pinned AND not exited-irrelevant (attached sessions are skipped entirely). Ordering: earliest `parkedAt` (armed-grace-fires-soonest first), fresh never-attached spawns (`parkedAt` set but no timer under "never reap", or brand-new) fall back to `createdAt` and yield last.
**Invariant:** pinned sessions are never reaped by time and never evicted at the cap — a full cap of pinned sessions is surfaced as a real capacity error, not a silent steal; exactly one victim per spawn attempt; eviction preference runs armed-dormant → parked-unattached.
**Probe:** eviction/pin behavior is exercised through the manager suite's detach/reap tests plus `spawnDetached` pinning in `tests/session-manager.test.ts::"runs recursive Git watchers only while a detached session has viewers"` (:93 — detached+pinned spawn stays live); the at-capacity refusal shape is pinned by the `spawnAndAttach ... Returns null only when the cap is full` contract (:522–525 source comment). Coverage caveat: no dedicated multi-session cap test exists upstream — port with your own cap-saturation test.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "localterm", query: "SessionLifecyclePolicy startGrace computeState evictOldestDormant", limit: 10, fields: ["signature", "name", "file"] });
await mcp.codebase_memory.trace_path({ project: "localterm", function_name: "startGrace", direction: "outbound", depth: 2 });
```

## Verdict
Adopt the three-state activity model (running / alive-quiet / ready) as THE reap gate, fire-time re-check + reschedule instead of trusted deadlines, the live grace resolver, and the pinned-exempt eviction ladder keyed on park-time; adapt thresholds (750ms window, 30s grace, 64 cap) and where `hasForeground` comes from (here: shell-hook OSC events) to your host; omit the favicon/UI surfacing and keep-awake integrations that consume the same signals. Direct tests exist upstream (integration, injectable `getGraceMs` avoids real waits). Coverage caveat: `tests/` was read on disk this session; the cap-eviction path itself has no dedicated upstream test (noted above).
