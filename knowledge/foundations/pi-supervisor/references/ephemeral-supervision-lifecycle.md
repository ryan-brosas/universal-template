<!-- capsule-v2 -->
# Ephemeral supervision lifecycle — when does persisted supervision die, and why idle-on-load clears it?

**Source:** pi-supervisor MIT `master@92c0d6d`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-supervisor`. **Question:** A porter must know exactly which events clear supervision vs keep it — otherwise a crash-resumed session either supervises a dead conversation forever or kills live supervision mid-run.

## Lifecycle event wiring (`src/index.ts:130-185`)
**Path/Symbol:** `src/index.ts` default extension — `onSessionLoad` (:132-143), `pi.on('session_before_compact')` (:153-157), `pi.on('session_compact')` handler (:160-185).
**Signature:** `onSessionLoad(ctx: ExtensionContext): void`; compact handlers are `async (event, ctx)`.
**Data Shape:** `ctx.isIdle(): boolean` is the ONLY liveness oracle; compaction event carries `willRetry: boolean`.

### Decisive source
```ts
const onSessionLoad = (ctx: ExtensionContext) => {
  currentCtx = ctx;
  state.loadFromSession(ctx);
  if (state.isActive() && ctx.isIdle()) {
    state.stop();
    disposeSession();
    ctx.ui.notify('Supervision cleared: agent is idle', 'info');
  }
  updateUI(ctx, widgetState, state.getState());
};
// session_compact:
if (ctx.isIdle() && !event.willRetry) {   // overflow retry must survive teardown
  state.stop(); disposeSession(); ...
}
```

**Flow:** every load-shaped event (`session_start`, `session_start` with reason ≠ startup/reload, `session_tree`) → reload state from the newest `supervisor-state` custom entry → if active AND agent idle ⇒ stop + dispose supervisor LLM session (ephemeral death) → render. Compaction first PERSISTS pre-compact (:153), then reloads post-compact; idle+`!willRetry` tears down, working-agent or pending-retry keeps supervision attached.
**Invariant:** Supervision is EPHEMERAL across restarts: persisted state survives only while the agent is actually working. The `willRetry` carve-out exists because an aborted turn resumes after overflow-compaction and re-fires `agent_settled` — tearing down there would orphan the resumed run.
**Probe:** `tests/ephemeral-supervision.test.ts` — `clears supervision when agent is idle` (:122) / `keeps supervision when agent is working` (:138) per reason (resume :151, tree :179, fork :208); compaction pair :260/:273.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-supervisor", query: "session_compact willRetry supervision cleared idle", limit: 8 });
```

## Verdict
Adopt the idle-clears-everything rule + `willRetry` carve-out as one contract. Adapt event names to your host's lifecycle hooks. Omit pi's `session_tree`/fork semantics if your host has no history navigation.
