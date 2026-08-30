<!-- capsule-v2 -->
# Compaction-survival lifecycle — persist-before-compaction, reload-after, willRetry guard, idle teardown

**Source:** ext-pi-supervisor MIT `master@92c0d6df986dfd138f941001e3fcc57a3ee07247`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-supervisor`. **Question:** How does long-horizon supervision survive context compaction without being torn down by its own idle-check?

## Three-event choreography
**Path/Symbol:** `src/index.ts:153-185`: `session_before_compact` (:153-157), `session_compact` (:160-185).
**Signature:** before-compact handler calls `state.persist()` when active; after-compact handler reloads, then either continues watching or tears down.
**Data Shape:** Consumes `event.willRetry` (host flag: an aborted turn will be retried after compaction).

### Decisive source
```ts
  // ---- Compaction survival: persist state BEFORE compaction ----
  pi.on('session_before_compact', async (_event, ctx) => {
    if (state.isActive()) { state.persist(); }
  });

  pi.on('session_compact', async (event, ctx) => {
    currentCtx = ctx;
    state.loadFromSession(ctx);
    if (!state.isActive()) { updateUI(ctx, widgetState, null); return; }

    // Skip the clear-on-idle teardown when an overflow retry is pending
    // (event.willRetry). The aborted turn resumes after compaction, so
    // agent_settled will fire again with the full resumed run and the
    // supervision loop should stay attached.
    if (ctx.isIdle() && !event.willRetry) {
      state.stop(); disposeSession();
      ctx.ui.notify('Supervision cleared: compaction complete, agent idle', 'info');
      updateUI(ctx, widgetState, null);
      return;
    }
    updateUI(ctx, widgetState, state.getState(), { type: 'watching', ... });
  });
```

**Flow:** pre-compaction flush guarantees a current snapshot entry exists in the surviving branch → post-compaction reload from branch → inactive ⇒ UI clear → idle AND no pending retry ⇒ clean teardown → otherwise remain attached and wait for the resumed run's settle.
**Invariant:** The persist MUST happen before compaction because compaction may summarize old entries away (the summarized-away case degrades to inactive — see probe). `willRetry && idle` must NOT tear down: the aborted turn resumes and fires agent_settled again, which re-runs the whole decision path.
**Probe:** `grep -c "session_before_compact\|willRetry" src/index.ts` → 3. Direct tests: `tests/compaction.test.ts:263` "full lifecycle: start -> compact -> reload -> repersist", `tests/compaction.test.ts:314` "handles state loss when supervisor-state was summarized away", `tests/ephemeral-supervision.test.ts:260` "continues supervision when agent is working after compaction (long-horizon sessions)".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-supervisor", name_pattern: "SupervisorStateManager", query: "compaction survival", limit: 10 });
```

## Verdict
Adopt the three-beat pattern (flush-before-destructive-context-op → reload-after → conditional teardown with a retry-awareness guard). Adapt event names to your host's compaction hooks; any summarization step that can drop custom entries requires the flush beat. Omit pi-specific willRetry only if your host has no retry-after-overflow behavior.
