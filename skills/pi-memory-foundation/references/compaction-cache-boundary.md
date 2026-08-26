<!-- capsule-v2 -->
# Compaction cache boundary — why must the pre-compaction hook refresh the snapshot even when it writes no handoff?

**Source:** pi-memory (MIT) `main@39e6b998a2279c8fad4a2c6c64e26828c1d6023e`; Codebase Memory `pi-memory` (full mode 380n/941e @2026-08-22T23:46:09Z). **Question:** When compaction drops tool history from the model's view, how do you keep an injected memory snapshot from serving stale state — even on turns where the handoff writer has nothing to say?

## Compaction cache boundary
**Path/Symbol:** `index.ts` default export → `pi.on("session_before_compact")` (:1587–1633); snapshot machinery `refreshMemorySnapshot` (:1400–1406).
**Signature:** `async (_event, ctx) => { parts = [openScratchpadItems, last15LinesOfTodayLog]; try { if (parts.length === 0) return; ...append HANDOFF... } finally { refreshMemorySnapshot("session_before_compact"); } }`.
**Data Shape:** HANDOFF block appended to `daily/YYYY-MM-DD.md`: `<!-- HANDOFF <ts> [<short-sid>] -->\n## Session Handoff\n**Open scratchpad items:**\n- [ ] …\n**Recent daily log context:**\n<last 15 lines>`.

### Decisive source
```ts
// index.ts:1613-1631 — the early-return sits INSIDE the try; the refresh is in finally
// Intentional cache boundary: compaction drops tool history, so the
// snapshot must catch up to disk on every compaction — even when no
// handoff is written. Otherwise stale pre-compaction state (e.g. a
// completed scratchpad item that no longer appears in the snapshot
// source files) would keep being injected.
try {
  if (parts.length === 0) return;
  const handoff = [`<!-- HANDOFF ${ts} [${sid}] -->`, "## Session Handoff", ...parts].join("\n");
  ...
  await ensureQmdAvailableForUpdate();
  scheduleQmdUpdate();
} finally {
  refreshMemorySnapshot("session_before_compact");
}
```

**Flow:** compaction begins → collect open scratchpad items + today's log tail → write HANDOFF when non-empty (then schedule qmd update) → REGARDLESS of write, refresh the byte-stable snapshot so the next turn's injection reflects post-compaction disk state.
**Invariant:** compaction is a cache invalidation point for any context snapshot derived from files whose change evidence lived in tool history. A "nothing to do" return must never skip the refresh — port it as `try { maybe-write } finally { refresh }`, not `if (empty) { return } write()`.
**Probe:** `test/unit.test.ts` — `"session_before_compact refreshes snapshot even when no handoff is written"` (:1875), `"session_before_compact refreshes snapshot so handoff is visible next turn"` (:1896); behavior proven live upstream by `test/e2e.ts:testHandoffSurvivesToNextSession` (:521–552). Unit tier EXECUTED pass 1 (`bun test` 182/182); e2e tier runner-blocked here (needs pi+qmd live).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-memory", query: "session_before_compact handoff snapshot refresh", limit: 6, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the invariant: treat compaction as a mandatory snapshot-refresh boundary decoupled from whether the side-effect artifact gets written. Adapt the artifact (HANDOFF block format, 15-line tail) to your host. Omit nothing — the finally-placement is the entire lesson.
---
