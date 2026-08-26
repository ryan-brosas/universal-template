<!-- capsule-v2 -->
# Crash-recovery pointer — mtime-TTL resume state with worktree fanout

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How do you make kill -9 recoverable for a long-lived session without embedding timestamps or racing concurrent bridges?

## Path/Symbol
**Path/Symbol:** `src/bridge/bridgePointer.ts` — TTL const (:40, 4h), `BridgePointerSchema` (:42-48: sessionId/environmentId/source enum), `getBridgePointerPath` (:52-54, per-cwd under projects dir), `writeBridgePointer` (:62-74), `readBridgePointer` (:83-113), `readBridgePointerAcrossWorktrees` (:129-184, MAX_WORKTREE_FANOUT=50 :19), `clearBridgePointer` (:190-202).
**Signature:** `writeBridgePointer(dir, pointer)` best-effort never-throws; `readBridgePointer(dir) → (pointer & {ageMs}) | null`; `clearBridgePointer(dir)` idempotent (ENOENT swallowed).
**Data Shape:** `{sessionId, environmentId, source: 'standalone'|'repl'}` + ageMs computed from file mtime.

### Decisive source
```ts
// Staleness is checked against the file's mtime (not an embedded timestamp)
// so that a periodic re-write with the same content serves as a refresh —
// matches the backend's rolling BRIDGE_LAST_POLL_TTL (4h) semantics. A
// bridge that's been polling for 5+ hours and then crashes still has a
// fresh pointer as long as the refresh ran within the window.
...
// stat for mtime (staleness anchor), then read. Two syscalls, but both
// are needed — mtime IS the data we return, not a TOCTOU guard.
```

**Flow:** write immediately after session create (crash at any later point leaves a trail); refresh hourly (`setInterval(...unref())`) AND opportunistically per work dispatch; read on startup → schema-validate → stale (>4h) or invalid pointers are DELETED so they don't re-prompt after the backend GC'd the env; clear on clean shutdown only. Resume flows: standalone `--continue` fans out across git worktree siblings (fast path = one stat in launch dir; parallel reads capped at 50; freshest-by-ageMs wins and RETURNS the found dir so failure clears the RIGHT file). replBridge perpetual mode reuses 'repl'-source pointers only and skips teardown-clear so continuity survives clean exits too.

**Invariant:** (1) mtime is the staleness clock — content-identical rewrites must bump it; embedding a timestamp instead breaks refresh semantics. (2) A crash-recovery file must NEVER itself crash the flow: every IO path catches and degrades to null. (3) Fanout readers must return WHICH dir held the pointer — clearing the wrong sibling's file on deterministic resume failure makes --continue loop forever on the same dead session. (4) Per-directory scoping keeps two concurrent bridges in different repos from clobbering each other.

**Probe:** coverage caveat — no upstream unit tests. Deterministic pins: `grep -n "mtime IS the data we return" src/bridge/bridgePointer.ts` (:91); `grep -n "MAX_WORKTREE_FANOUT = 50" src/bridge/bridgePointer.ts` (:19); `grep -n "must never" src/bridge/bridgePointer.ts` (:60); graph resolves `locoagent.src.bridge.bridgePointer.readBridgePointerAcrossWorktrees` :129-184 line-exact.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "writeBridgePointer readBridgePointerAcrossWorktrees clearBridgePointer BridgePointerSchema", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt whole as the canonical crash-recovery-pointer pattern (mtime-TTL + best-effort writes + scoped paths + worktree fanout). Adapt storage location and fanout source (`git worktree list` analogue) to your host.
