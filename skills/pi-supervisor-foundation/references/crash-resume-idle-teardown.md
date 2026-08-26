<!-- capsule-v2 -->
# Crash-resume idle teardown — shared session-load handler that clears stale supervision when the agent is idle

**Source:** ext-pi-supervisor MIT `master@92c0d6df986dfd138f941001e3fcc57a3ee07247`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-supervisor`. **Question:** After a crash resume, session fork, or history navigation, when must restored-but-stale supervision be dropped instead of resumed?

## One handler, three registration points, one startup carve-out
**Path/Symbol:** `src/index.ts:132-150` (`onSessionLoad` + three `pi.on` registrations).
**Signature:** `const onSessionLoad = (ctx: ExtensionContext) => void`; registered on `session_start`, a SECOND `session_start` filtered by reason, and `session_tree`.
**Data Shape:** No payload; consults `state.isActive()` and `ctx.isIdle()`.

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

  pi.on('session_start', async (_event, ctx) => onSessionLoad(ctx));
  pi.on('session_start', async (event, ctx) => {
    if (event.reason === 'startup' || event.reason === 'reload') return;
    onSessionLoad(ctx);
  });
  pi.on('session_tree', async (_event, ctx) => onSessionLoad(ctx));
```

**Flow:** any load/restore/tree-navigation event → reload state from branch → active but agent idle ⇒ the persisted goal refers to work that already ended; stop + dispose + notify → always refresh UI.
**Invariant:** Idle-at-load is treated as "the supervised run is over" — resuming an active supervisor against an idle agent would immediately nudge it with a possibly stale goal. The double `session_start` registration is deliberate: the first runs unconditionally (covers startup), the second covers resume/fork reasons while skipping startup/reload to avoid duplicate handling. Working agent ⇒ keep supervising.
**Probe:** `grep -cF "onSessionLoad(ctx)" src/index.ts` → 3; `grep -c "event.reason === 'startup' || event.reason === 'reload'" src/index.ts` → 1. Direct tests: `tests/ephemeral-supervision.test.ts:122/:151/:209` "clears supervision when agent is idle" across crash-resume/resume/fork arms, each paired with a "keeps supervision when agent is working" twin at :138/:167/:225.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-supervisor", query: "loadSystemPrompt SUPERVISOR.md project global built-in", limit: 10 });
```
(Adjacent seam; for this handler use `name_pattern` `SupervisorStateManager` plus the test pins above — the handler itself lives in index.ts's default export.)

## Verdict
Adopt restore-then-adjudicate: persisted active state is a CLAIM that must be validated against live liveness (idle ⇒ drop). Adapt the event/reason vocabulary; keep the notify so users understand why supervision vanished. Omit the dual-registration trick if your host delivers load events exactly once with reason metadata.
