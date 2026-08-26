<!-- capsule-v2 -->
# Settled-event trigger — move compaction off mid-retry events onto the host's settled event and delete your own retry heuristic

**Source:** pi-observational-memory MIT `master@ce9fc982b3a219a7839f07c9f4a3e054e81a2b21`; Codebase Memory `pi-observational-memory`. **Question:** When the host ships a lifecycle event that fires only after retries/queued work finish, should you keep maintaining a hand-rolled "is this turn retryable" heuristic — or migrate and delete it?

## Path/Symbol
**Path:** `src/hooks/compaction-trigger.ts`
**Symbol:** `registerCompactionTrigger` **:6-77**; DELETED: `RETRYABLE_ERROR_RE` (was :5-7) and the last-assistant-message scan.

**Signature:** `pi.on("agent_settled", (_event, ctx) => ...)` — was `pi.on("agent_end", (event, ctx) => ...)` with an in-handler `RETRYABLE_ERROR_RE.test(lastAssistant.errorMessage)` suppression.

**Data Shape:** `agent_settled` carries no messages payload used here; threshold inputs unchanged (`ctx.sessionManager.getBranch()` entries, `resolveCompactAfterTokens(config, contextWindow)`).

### Decisive source
```ts
// Pi emits agent_settled only after retries, automatic compaction, and queued
// continuation have finished, so retry policy stays owned by Pi.
pi.on("agent_settled", (_event, ctx) => {
    runtime.ensureConfig(ctx.cwd);
    if (runtime.config.passive === true) return;
    if (runtime.compactInFlight) return;
    ...
```

**Flow:** agent_settled → passive/in-flight guards → raw-token progress ≥ threshold? → capture ctx fields SYNCHRONOUSLY (the setTimeout below may outlive ctx) → defer to macrotask (`setTimeout 0`) → re-check `ctx.isIdle()` AND re-check progress (another compaction may have run meanwhile) → `ctx.compact({onComplete,onError})` with `"Compaction cancelled"` error string-matched to suppress double-notification. The whole deferral/idle-recheck/cancel-suppression machinery is UNCHANGED from before the drift — only the subscription point and the deletion moved.

**Invariant:** The old design existed because `agent_end` fires BEFORE pi's own retry check, so the extension had to predict retryability with a ~30-alternative regex over `lastAssistant.errorMessage` — and any host-side pattern change silently broke it (false-positive = compacting mid-retry over turns about to replay; false-negative = never compacting). Subscribing to the SETTLED event deletes the entire class: the host has already decided retries are done when you run. Lesson generalizes: **when the host offers a post-lifecycle event, prefer it over maintaining a parallel heuristic of the host's internal policy.** The test file's registration assertion now reads `expect(name).toBe("agent_settled")`; the "skips retryable assistant errors" test was deleted outright.

**Probe (direct tests):**
```bash
cd /mnt/hdd/utopia/inspo/pi-observational-memory && \
grep -c "agent_settled" src/hooks/compaction-trigger.ts   # expect 2 && \
grep -c "agent_end\|RETRYABLE" src/hooks/compaction-trigger.ts   # expect 0 && \
npx vitest run tests/compaction-trigger.test.ts           # 24 passed
```

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-observational-memory", query: "registerCompactionTrigger agent_settled compactInFlight resolveCompactAfterTokens", limit: 5 });
```

**Verdict:** Adopt settled-event triggering with the retained synchronous-ctx-capture + deferred re-validation ladder. Adapt event name to your host's lifecycle vocabulary. Omit nothing — including the deletion: port the LESSON (prefer host lifecycle truth over parallel heuristics), not the regex.
