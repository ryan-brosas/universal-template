<!-- capsule-v2 -->
# Session event invalidation matrix — which host lifecycle events must reset which cached extension state, and in what order?

**Source:** pi-better-openai MIT `main@86814e9047996abba08e4c907e23286329196fe0`; Codebase Memory `pi-better-openai`. **Question:** What is the full event→action wiring a composition root must implement so caches, pets, footer, and background controllers stay coherent?

## Event → invalidation/action table
**Path/Symbol:** `index.ts` handler registrations :1222-1324 (`session_start`, `agent_start`, `tool_execution_start`, `tool_execution_end`, `agent_end`, `turn_end`, `session_compact`, `session_tree`, `model_select`, `session_shutdown`, `before_provider_request`, `message_start/update/end`).
**Signature:** `pi.on(<event>, (event, ctx) => void | payload)` — every handler ends in the same three primitives: invalidate memos → mutate controllers → `updateFooter(ctx)`.
**Data Shape:** Three state families with distinct triggers: usage memo + session-name memo (leaf/model-keyed), totals ledger (append-vs-rescan), pet controller (activity/animation FSM). Background poller: `usageController.start/refresh/shutdown`.

### Decisive source
```ts
// streaming deltas: content changed but leafId did NOT — key equality is not freshness
pi.on("message_start", invalidateContextUsage);
pi.on("message_update", invalidateContextUsage);
pi.on("message_end", invalidateContextUsage);

// identity switches: memo invalidation alone; totals survive
pi.on("model_select", (event, ctx) => {
  invalidateContextUsage();
  fastController.applyDesiredState(ctx, config(ctx));   // re-derive active for new model
  ... persist-if-changed ... updateFooter(ctx);
  void usageController.refresh(ctx, event.model.id, { force: true });
});

// teardown order: stop timers/pollers BEFORE dropping the context they capture
pi.on("session_shutdown", () => {
  invalidateContextUsage(); invalidateSessionName();
  usageController.shutdown();                           // interval poller first
  petController.shutdown();                             // animation timers second
});
```

**Flow:** per event — `session_start`: invalidate both memos, seed fast-mode from flag+config, reconcile-persist derived pair, install resize guard, rescan totals, updateFooter, start usage poller. `agent_start`/`agent_end`: pet activity transitions + updateFooter. `tool_execution_*`: pet tool-state (footer refresh skipped on tool ERROR at end :1256). `turn_end`/`compact`/`tree`: see dual-ledger capsule. `before_provider_request`: return `fastController.injectProviderPayload(...)` result directly.

**Invariant:** EVERY handler funnels through `updateFooter(ctx)` as its last synchronous act (except pure-invalidation message handlers and shutdown) so no state change can leave stale chrome; memo invalidation happens BEFORE any await/mutation so a re-entrant read never sees the pre-event world; teardown stops the poller before the animator because only the poller's callback can re-arm work after the animator's timers are gone. Porters forget the streaming trio (`message_*`) and serve frozen context percentages mid-turn.

**Probe:** `tests/footer.test.ts:369-392` "off mode clears the Better OpenAI footer only after Better OpenAI installed it" / "off mode does not clear a footer after Better OpenAI's footer was disposed" — re-emitting `session_start` after config flip to `off` calls `setFooter(undefined)` exactly when WE own the footer (latch discipline), and NOT after an external dispose. Handler sweep pinned by source :1222-1324; per-event unit coverage beyond these two is a recorded caveat.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-better-openai", query: "updateFooter installFooter clearFooter statusInstalled", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the matrix shape (event → {invalidate which family, mutate which controller, render}) for any long-lived UI-extension composition root. Adapt event names to your host's lifecycle. Omit pi-specific event payloads.
