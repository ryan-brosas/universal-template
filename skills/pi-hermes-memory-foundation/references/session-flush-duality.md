<!-- capsule-v2 -->
# Session flush — one last LLM memory-save, awaited at BOTH compaction and shutdown (shutdown contract corrected @71beae8a)

**Source:** pi-hermes-memory (MIT, `main@71beae8a`); Codebase Memory `pi-hermes-memory`. **Question:** How do you give the agent one turn to persist memories before context is lost — before compaction and before session shutdown — and what does each hook site owe the host?

## setupSessionFlush
**Path/Symbol:** `src/handlers/session-flush.ts:setupSessionFlush` (:51–150); prompt builder `buildDirectFlushUserPrompt` (:21–49); imports `DIRECT_FLUSH_SYSTEM_PROMPT`/`FLUSH_PROMPT`/`ENTRY_DELIMITER`/`buildMemoryTargetRoutingGuidance` from `src/constants.ts`.
**Signature:** `setupSessionFlush(pi, store, projectStore: ProjectStoreRef, config, dbManager?, projectName?: ProjectNameRef, deps?)`; internal `flush(ctx: Pick<ExtensionContext, "sessionManager" | "model" | "modelRegistry" | "cwd">, signal?, timeoutMs = 30000)`; hooks `session_before_compact` (awaited, 30 s), `session_shutdown` (awaited, 10 s).
**Data Shape:** conversation snapshot = current memory entries + user profile + optional project memory joined with `ENTRY_DELIMITER`, then the collected `[USER]`/`[ASSISTANT]` message parts; direct transport emits operations through the shared review pipeline (`runDirectMemoryCompletion`). The subprocess call now carries `{ cwd: ctx.cwd, model: resolveChildPiModel(ctx.model), signal, timeoutMs }`.

### Decisive source
```ts
// :138-149 — BOTH trigger sites await; the old fire-and-forget comment is GONE:
pi.on("session_before_compact", async (event, ctx) => {
  if (!config.flushOnCompact) return;
  await flush(ctx, event.signal, 30000);   // compaction can afford to wait
});

// Flush before session shutdown. Pi awaits async session_shutdown handlers
// before invalidating the session, so await the bounded flush here.
pi.on("session_shutdown", async (_event, ctx) => {
  if (!config.flushOnShutdown) return;
  await flush(ctx, undefined, 10000);      // bounded at 10 s, then Pi proceeds
});
```

**Flow:** (1) a `message_end` listener counts user turns; (2) on compaction or shutdown the shared `flush` gates on `flushMinTurns`, snapshots the branch, collects message parts; (3) direct in-process completion is attempted first (`usesDirectTransport(config)`); (4) only on failure does it spawn the `pi -p` subprocess fallback with the inherited cwd/model; (5) every failure path inside `flush` degrades silently (`catch { /* Best-effort flush — never block compaction or shutdown. */ }`).
**Invariant:** awaiting is now the contract at BOTH sites because the host (Pi) awaits async `session_shutdown` handlers anyway — detaching would just orphan an in-flight child process while the session dies. The bound moves the cost question from "block or not" to "how long": 30 s where waiting is cheap, 10 s where teardown latency matters. ERRATUM vs pass-1/2/3 state: this capsule previously documented fire-and-forget at shutdown ("intentionally do NOT await"); upstream commit 1fd27bc/#179-era rework made Pi's await-semantics explicit and the handler was changed to `await` — source wins.
**Probe:** `npx tsx --test tests/handlers/session-flush.test.ts` — "awaits the bounded flush before session_shutdown resolves" (:214, uses `Promise.withResolvers` + a deferred mock exec to assert the shutdown promise has NOT settled while exec is in flight, then resolves it), "session_shutdown triggers flush when flushOnShutdown is true" (:203), "session_shutdown does NOT trigger when flushOnShutdown is false" (:246). File passes GREEN under `npx tsx --test` (node:test runner; bun mis-runs this suite).
**Retrieve:** `search_graph({ project: "pi-hermes-memory", query: "setupSessionFlush buildDirectFlushUserPrompt FLUSH_PROMPT", limit: 5 })`

## Verdict
Adopt the dual-trigger flush with bounded-await at both sites and per-site budgets (30 s compaction / 10 s shutdown). Adapt prompts/constants and budget values. Omit the Pi event names themselves. Pair with `background-review-loop.md` (same transport ladder, different trigger policy) and `target-routing-guidance.md` (the routing block injected into every flush prompt).
