<!-- capsule-v2 -->
# Fallback chain with content-received latch — when may the chain try the next model, and when must an error reach the caller?

**Source:** pi-model-router MIT `main@002b48f9bb03c068e0ef97eb230f49df57a24f93`; Codebase Memory `pi-model-router`. **Question:** How do I delegate a routed turn through primary + fallbacks such that partial answers are never duplicated and pre-content failures are retried transparently?

## Chain execution loop in streamSimple
**Path/Symbol:** `extensions/provider.ts:streamSimple` (lines 416–603); honesty gate :461–471 (`truncateContext` :106–138); thinking clamp :473–492; stale-context degradation :573–596.
**Signature:** builds `modelsToTry` then loops; per-attempt errors are caught into `lastError`; terminal failure rethrows.
**Data Shape:** Chain = deduped `[decision.targetLabel, ...profile[decision.tier].fallbacks]`. Events re-emitted verbatim to the caller's stream; cost accumulated from `done` events.

### Decisive source
```ts
let contentReceived = false;
for await (const event of delegatedStream) {
  if (event.type === 'done') {
    const cost = event.message.usage?.cost?.total ?? 0;
    state.accumulatedCost += cost;
  }
  if (event.type === 'error' && !contentReceived) {
    throw new Error(errorMessage || 'Model failed before sending content.');
  }
  const isContent = event.type === 'text_delta' || event.type === 'thinking_delta' ||
                    event.type === 'toolcall_delta' || event.type === 'toolcall_end';
  if (isContent) contentReceived = true;
  stream.push(event);
}
success = true;
if (i > 0) decision.isFallback = true;
break;
} catch (err) { lastError = err; }
```
```ts
// Honesty gate, per attempt:
const targetLimit = resolveContextWindow(decision.tier, profile, registry);
if (targetLimit < model.contextWindow!) effectiveContext = truncateContext(context, targetLimit);
```

**Flow per attempt:** skip refs whose provider is `'router'` (recursion guard) → registry miss or auth failure records `lastError` and CONTINUES → truncate context if the tier's resolved window is smaller than the reported router model window (never over-truncate; keeps latest message) → clamp requested reasoning to the tier's `resolvedThinkingLevels` only when the model supports reasoning → strip the host's own `reasoning` option from delegation options (the router owns thinking) → stream. **Latch semantics:** an error event BEFORE any content delta throws locally ⇒ next fallback; once ANY text/thinking/toolcall delta flowed, later error events propagate to the caller unchanged (no duplicate-answer risk). Success on index i>0 flags `decision.isFallback`. Exhausted chain rethrows `lastError`.
**Invariant:** At most one model may emit content per turn. Registry/auth problems and pre-content model errors are transparently absorbed; post-content failures are surfaced, never masked by a second attempt. A stale extension runtime (error message containing `'stale'`, e.g. subagent teardown) degrades to a graceful `done` event so the host's result promise resolves; `persistState` runs in `finally` best-effort.
**Probe:** `extensions/provider.test.ts` — fallback advance + `isFallback` :184–227; auto-truncation keeps latest message under resolved limit :359–410; registry-timeout error event :412–439; delayed-registry success :441–491; unknown-profile error :493–515; auth-fail fallback :517–556; model-not-found fallback :558–593; all-fail propagation :595–626; `waitForRegistry` immediate/delayed/timeout :629–657. Stale-context done-degradation (:573–596) is source-pinned without a dedicated test.

## Get live surrounding code
**Retrieve (executed live at pin):**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-model-router", query: "streamSimple fallback truncateContext delegation", limit: 5 });
// → truncateContext (provider.ts:106-138) #1 and streamSimple (provider.ts:249-607) #2.
```
Retrieval caveat: the naive form `"fallback contentReceived modelsToTry isFallback"` returns **total: 0** on this
graph generation; the latch lives inline in `streamSimple`, so reach it via the query above or any query naming
`truncateContext`/`streamSimple`.

## Verdict
Adopt the content-received latch, the continue-on-missing/auth-error posture, the per-attempt honesty truncation, reasoning-option stripping, and the stale-runtime graceful done as one unit — they jointly define "transparent retry before first byte". Adapt event-type names to your stream protocol and the truncation estimator to your tokenizer; omit the `'stale'` string sniff only for a host with typed teardown errors.
