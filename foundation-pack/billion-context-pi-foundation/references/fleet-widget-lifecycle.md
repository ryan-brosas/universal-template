<!-- capsule-v2 -->
# Fleet status widget — how does a live TUI widget render running background work without ticking forever or leaking teardown errors?

**Source:** billion-context-pi (MIT) `master@558a83a9db69`; Codebase Memory project `billion-context-pi`. **Question:** What lifecycle contract keeps a periodic UI widget cheap, correct on empty, and safe across session teardown?

## Render-key debounce + idle self-stop + direct mode guard + double best-effort teardown
**Path/Symbol:** `src/fleet-widget.ts` (125L whole): `renderKeyFor`, interval wiring, `poke()`, mode guard (:70-77), dispose.
**Signature:** `delegateStatusWidget.setContext(ctx, snapshotGetter)` / `.refresh()` / `.dispose()`; row = `● agent (12s) — task`; key = agent + elapsed-SECONDS + truncated task per run.
**Data Shape:** snapshot pulled FRESH each tick from the in-memory runs Map via `runningRunsSnapshot` — never cached between ticks.

### Decisive source
```ts
// :62-67 — the idle doctrine:
// "empty list clears the widget AND stops its timer ... a spawn can arrive
//  after idle shutdown" → poke() restarts it. A background poller that
//  outlives its content is a bug dressed as a feature.
// :73-76 — capability vs mode:
// RPC reports hasUI=true but setWidget there emits useless extension_ui_request
// notifications (~1Hz chatter); guard on ctx.mode === "tui" DIRECTLY.
```

**Flow:** setContext binds ui + getter and starts the (unref'd) 500ms interval → each tick pulls a fresh snapshot and re-renders only when the composite render key changed (elapsed rounds to seconds so motion updates ~1Hz regardless of tick rate) → last run settles → clear widget + stop interval → next spawn pokes it back to life.
**Invariant:** (1) debounce on derived state (rounded time), not raw ticks. (2) An empty workload must STOP the timer; restart-on-event beats never-idle polling. (3) Guard on the actual MODE, not hasUI — capability flags lie about widget support. (4) Teardown is best-effort twice over: setWidget throws during session teardown are swallowed AND an unexpected throw clears the ui binding so the next setContext rebinds; real cleanup belongs to dispose(). Sort rows by startedAt (launch order = mental model); truncate task text inside the row budget with the ellipsis counted.
**Probe:** widget poke on spawn/done is asserted within the delegate lifecycle tests (`tests/delegate-tool.test.ts:522-524`, `:600-606` — widget stays live until the last run settles). No dedicated widget suite; recorded caveat.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "billion-context-pi", query: "delegateStatusWidget setContext refresh dispose", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt all five rules for any periodic UI surface. Adapt placement/rendering to your TUI kit. Omit pi-specific widget APIs.
