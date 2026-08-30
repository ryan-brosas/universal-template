<!-- capsule-v2 -->
# Snapshot — KV-cache-stable memory context that keeps the system prompt byte-stable across turns

**Source:** pi-memory (MIT, `main@39e6b998a2279c8fad4a2c6c64e26828c1d6023e`); Codebase Memory `pi-memory`. **Question:** How does an agent keep the injected memory context byte-stable across turns so local prefix caches (llama.cpp, vLLM, MLX) don't invalidate the whole conversation tail on each turn?

## Snapshot
**Path/Symbol:** `index.ts:refreshMemorySnapshot` (1400–1406), `getSnapshotMode` (1408–1411), `_resetMemorySnapshot` (1414–1420).
**Signature:** `refreshMemorySnapshot(reason: string): void`; `getSnapshotMode(): "stable" | "per-turn"`.
**Data Shape:** module state `memorySnapshot: string | null`, `snapshotTakenAt`, `snapshotTakenOnDate`, `snapshotReason`, `snapshotDirty: boolean`. Mode from `PI_MEMORY_SNAPSHOT` ∈ {stable (default), per-turn}. Refresh triggers: `session_start`, `session_before_compact`, long-term writes (set `snapshotDirty`), day rollover.

### Decisive source
```ts
// refreshMemorySnapshot (1400-1406): rebuild the context and clear the dirty flag
memorySnapshot = buildMemoryContext("");
snapshotTakenAt = nowTimestamp();
snapshotTakenOnDate = todayStr();
snapshotReason = reason;
snapshotDirty = false;

// before_agent_start stable branch (1550-1558): refresh only when stale
const today = todayStr();
const needsRefresh = memorySnapshot === null || snapshotDirty || snapshotTakenOnDate !== today;
if (needsRefresh) {
  const reason = memorySnapshot === null ? "before_agent_start" : snapshotDirty ? "long_term_write" : "day_rollover";
  refreshMemorySnapshot(reason);
}
memoryContext = memorySnapshot ?? "";
```

**Flow:** (1) In `stable` mode, `before_agent_start` reuses the cached snapshot, refreshing only when null, dirty, or on a different day. (2) `memory_write target=long_term` and `memory_forget`/`memory_restore` set `snapshotDirty = true` so the next turn refreshes; daily writes are intentionally NOT dirty (high-frequency, already echoed via tool args). (3) `session_before_compact` always refreshes in its `finally` (compaction drops tool history, so the snapshot must catch up to disk). (4) `per-turn` mode rebuilds every turn and optionally runs a live search.

**Invariant:** in stable mode the injected memory block is byte-identical across turns between checkpoints, preserving KV-cache prefix reuse; a long-term write or forget marks the snapshot dirty so the change is visible next turn; daily writes keep the cache warm.

**Probe:** `test/unit.test.ts` — `KV cache stability: memory snapshot` describe (:1815): `byte-stable systemPrompt across turns despite mid-session file mutations` (:1844), `session_before_compact refreshes snapshot even when no handoff is written` (:1875), `session_before_compact refreshes snapshot so handoff is visible next turn` (:1896), `memory_write target=long_term marks snapshot dirty so next turn refreshes` (:1915), `memory_write target=daily does NOT mark snapshot dirty (cache stays warm)` (:1935), `PI_MEMORY_SNAPSHOT=per-turn restores per-turn rebuild behavior` (:1954), `session_start refreshes snapshot (resets module state across sessions)` (:1968), `snapshot caveat is included in stable mode header` (:1995). Coverage caveat: `test/` is excluded from the index by design, so probes are source-grounded from the on-disk test files.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-memory", query: "refreshMemorySnapshot getSnapshotMode _resetMemorySnapshot", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the stable/per-turn snapshot split, the checkpoint-triggered refresh, the long-term-write dirty flag, and the always-refresh-on-compact rule. Adapt the env-var name, checkpoint triggers, and caveat wording to the host. Omit nothing here — this is the portable KV-cache snapshot core.
