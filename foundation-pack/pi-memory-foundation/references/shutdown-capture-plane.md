<!-- capsule-v2 -->
# Shutdown capture plane — how "was this a real exit?" is detected before the summary gate

**Source:** pi-memory (MIT) `main@39e6b998a2279c8fad4a2c6c64e26828c1d6023e`; Codebase Memory `pi-memory`. **Question:** How does an extension learn the *user-intent reason* a session is ending (Ctrl+D vs `/quit` vs lifecycle transition) so its goodbye hook can decide whether to summarize at all?

## Shutdown capture plane
**Path/Symbol:** `index.ts:export default(pi)` — module state `exitSummaryReason` reset at `session_start` (:1429); Ctrl+D subscription (:1433–1442); `/quit` input listener (:1531–1537); consumption in `session_shutdown` (:1470–1490); display mapping `formatExitSummaryReason` (:306–310).
**Signature:** `ctx.ui.onTerminalInput((data) => string | undefined)`; `pi.on("input", async (event) => ({ action: "continue" }))`.
**Data Shape:** `exitSummaryReason: "ctrl+d" | "slash-quit" | null` (module-level, one per process). Default fallback when nothing captured: `"session-end"`.

### Decisive source
```ts
// session_start (1435-1440): three-clause Ctrl+D detector — byte, idle, empty editor
terminalInputUnsubscribe = ctx.ui.onTerminalInput((data) => {
  if (!data.includes("\u0004")) return undefined;   // 0x04 = EOF key
  if (!ctx.isIdle()) return undefined;               // agent still running → not an exit intent
  if (ctx.ui.getEditorText().trim()) return undefined; // user typed something → not an EOF
  exitSummaryReason = "ctrl+d";
  return undefined;
});

// input hook (1533-1534): only USER-typed /quit counts
if (event.source !== "extension" && event.text.trim() === "/quit") {
  exitSummaryReason = "slash-quit";
}

// shutdown consumption (1487-1488): captured reason or generic default, then cleared
const reason = exitSummaryReason ?? "session-end";
exitSummaryReason = null;
```

**Flow:** `session_start` clears any stale reason, subscribes a terminal-input watcher (only when `ctx.hasUI`) that flags `ctrl+d` on raw 0x04 **while idle with an empty editor**, and returns `undefined` from every branch (it observes; it never swallows input). A separate `input` hook flags `slash-quit` for user-typed `/quit` only (`source !== "extension"` blocks programmatic sends). `session_shutdown` reads the flag once, falls back to `"session-end"`, and nulls it before any async work so a late event can't double-consume.

**Invariant:** the capture side never throws, never blocks input, and stores ONLY user-exit intents — every other path leaves the flag null so shutdown treats it as an ordinary end; the flag is consumed exactly once (reset at start AND after read).

**Probe:** `test/unit.test.ts` pins the consumption side (capture is UI-adapter surface, unit-covered only via skip/fallback): `session_shutdown with reason=reload skips exit summary entirely` (:1465), `session_shutdown skips trivial sessions without attempting a summary` (:1488), `session_shutdown with reason=quit still attempts the exit summary` (:1521), `session_shutdown writes nothing when summary generation is unavailable` (:1417). Coverage caveat: no direct upstream test drives `onTerminalInput`/the `input` hook — the three-clause gate is source-pinned only.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-memory", query: "onTerminalInput exitSummaryReason slash-quit", limit: 6, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the split: observe-only input watchers that record a typed exit-reason enum, consumed once by the shutdown hook with a neutral default. Adapt the trigger bytes (`\u0004`), the slash command, and the idle/editor gates to your host's terminal API. Omit the Pi `ctx.ui` specifics unless your host exposes the same shape.
