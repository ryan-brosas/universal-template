<!-- capsule-v2 -->
# OpenCode auto-dream gate FSM — how do you schedule agent-driven memory consolidation so it fires rarely, never concurrently, and only resets when consolidation actually happened?

**Source:** mem0 Apache-2.0 `main@7e096155714c`; Codebase Memory `mem0`. **Question:** when a memory plugin wants the AGENT itself to periodically consolidate its memory store (merge duplicates, drop stale/sensitive entries), what gate stack, lock, and completion semantics make that safe across concurrent sessions and crashes?

## dream.ts — three-tier gates + 1h-stale exclusive lock + write-evidenced completion
**Path/Symbol:** `integrations/mem0-plugin/.opencode-plugin/dream.ts` — `DREAM_DEFAULTS` (40–46), `loadDreamConfig` (81–111), `incrementSessionCount` (114–121), `checkCheapGates` (124–140), `checkMemoryGate` (143–152), `acquireDreamLock` (155–180), `releaseDreamLock` (182–188), `recordDreamCompletion` (191–197), `DREAM_PROTOCOL` (204–225); trigger site in `opencode-mem0.ts` chatMessageHook init block (731–751) and finalization in `emitSessionStop` (301–320).
**Signature:** `checkCheapGates(stateDir, config: Partial<DreamConfig>): {proceed: boolean; reason?: string}`; `checkMemoryGate(memoryCount: number, config): {pass: boolean; reason?: string}`; `acquireDreamLock(stateDir): boolean`; `recordDreamCompletion(stateDir): void`.
**Data Shape:** state file `~/.mem0/mem0-dream-state.json` `{lastConsolidatedAt: epoch-ms, sessionsSince: int, lastSessionId: string|null}`; lock file `~/.mem0/mem0-dream.lock` `{pid, startedAt}`. Defaults: enabled, auto, minHours 24, minSessions 5, minMemories 20. Config precedence: defaults < settings.json `dream` block (per-field type-checked: booleans stay booleans, numbers stay numbers) < `MEM0_DREAM` env force-disable (`false/0/no/off`).

### Decisive source
```ts
export function acquireDreamLock(stateDir: string): boolean {
  ensureDir(stateDir);
  const lp = lockPath(stateDir);
  try {
    const lock = JSON.parse(readFileSync(lp, "utf-8")) as DreamLock;
    if (Date.now() - lock.startedAt < LOCK_STALE_MS) {   // 60 * 60 * 1000
      return false;
    }
    try { unlinkSync(lp); } catch { /* race ok */ }
  } catch { /* no lock file */ }
  const lock: DreamLock = { pid: process.pid, startedAt: Date.now() };
  try {
    writeFileSync(lp, JSON.stringify(lock), { flag: "wx" });  // exclusive create is the real claim
    return true;
  } catch {
    return false;
  }
}
```
Completion is write-evidenced, not time-based: at `beforeExit`, `recordDreamCompletion` runs ONLY if `dreamWriteSeen` (an add/delete/delete_all tool call happened while the dream protocol was active); the lock is released unconditionally either way.

**Flow:** first message of a session → incrementSessionCount (counts DISTINCT session ids only — repeated calls with the same id are no-ops) → on session init, if enabled+auto+not-yet-triggered: cheap gates (hoursSince ≥ minHours AND sessionsSince ≥ minSessions) → memory-count gate (count fetched once at init via getAll pageSize=1, three-shape unwrap count/array/results) → acquireDreamLock → all pass: set dreamTriggered, push DREAM_PROTOCOL into systemContext, emit `dream_triggered`; any fail: log the joined reasons ("auto-dream waiting — …") so "why didn't it run?" is answerable from logs. At process exit: record completion iff a dream write was seen (+ `dream_completed` event), always release the lock.
**Invariant:** gates are ordered cheap-first (no API call before the filesystem gates); the lock's exclusive-create flag — not the read-then-unlink — is the actual mutual-exclusion primitive (the stale-steal unlink is best-effort and race-tolerant); completion must NOT reset the time/session gates unless consolidation actually wrote something, or a crashed/ignored dream would permanently suppress future dreams; DREAM_PROTOCOL instructs the agent to use the plugin's NATIVE tools (get_memories/add_memory/delete_memory) and to skip `[PINNED]` entries.
**Probe:** `.opencode-plugin/dream.test.ts` (9 tests, bun green) — pins the memory-gate boundary (≥ vs <), fresh-state blocks-on-sessions then passes after minSessions distinct ids, distinct-session counting (3× same id → "sessions: 1"), completion-reset re-blocks on the time gate, lock exclusivity + reclaim-after-release, config defaults / MEM0_DREAM=false / settings-block override, and that DREAM_PROTOCOL names native tools and NOT the MCP tool.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mem0", query: "acquireDreamLock", limit: 10, fields: ["signature", "name", "file"] });
```
(MCP not connected this session — direct whole-file reads of dream.ts + dream.test.ts + trigger/finalization sites executed instead; record in verification.md pass 10.)

## Verdict
Adopt the whole gate stack: cheap-fs-gates-before-api-call ordering, distinct-session counting, stale-age lock steal with exclusive-create as the real claim, write-evidenced completion, and log-the-reasons on every skip. Adapt thresholds (24h/5 sessions/20 memories) and the protocol text to your host's tool names; keep `[PINNED]`-style user-protected markers if your store supports them. Omit the PostHog events but keep their trigger points as your own observability hooks. This seam has no Python-hook-suite counterpart — it is the pi-agent lineage contribution to the family (contrast: the Python suite's closest analogue is the cadence counters in plugin-prompt-context-compiler.md, which nudge rather than consolidate). Coverage: fully indexed plane, whole 225L file + 100L test read.
