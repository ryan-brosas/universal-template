<!-- capsule-v2 -->
# Stale-extension-ctx deferral — a session replaced mid-task turns "ctx is stale" throws into deferred-not-failed outcomes

**Source:** pi-hermes-memory (MIT, `main@71beae8a`); Codebase Memory `pi-hermes-memory`. **Question:** A long consolidation run holds the lock while the user starts a new session — the captured ctx now throws "extension ctx is stale" — is that a failure the user should see?

## triggerConsolidation stale-ctx branch
**Path/Symbol:** `src/handlers/auto-consolidate.ts:triggerConsolidation` catch block (:277–291); sibling handling in `tests` :697 ("does not throw if the command ctx becomes stale before the final summary notify"). Warning gate: `src/auto-consolidation-warning.ts:shouldWarnAutoConsolidationFailure(warnOnFailure, consolidated)` (6–8) + config `autoConsolidationWarnOnFailure` (`src/types.ts`, default true; `src/index.ts` :249–269 logs deferred via `console.info` and warns only when the gate passes).
**Signature:** catch of `String(err)` → `message.includes("extension ctx is stale")` ⇒ `{ consolidated: false, deferred: true, error: "session replaced or reload… will consolidate on next write" }`.
**Data Shape:** `ConsolidationOutcome` gains nothing new — reuses the existing `deferred: true` channel that lock contention already uses.

### Decisive source
```ts
} catch (err) {
  const message = String(err);
  if (message.includes("extension ctx is stale")) {
    // Session replaced/reloaded while consolidation was running. The new
    // session re-initializes the store and will consolidate on its own next
    // write, so this is a skip, not a failure — report it as deferred so the
    // caller asks for a retry instead of surfacing a stale-ctx error.
    return { consolidated: false, deferred: true,
      error: "session replaced or reloaded during consolidation — will consolidate on next write" };
  }
  return { consolidated: false,
    error: `Consolidation failed: ${message.slice(0, 200)}` };
}
```

**Flow:** consolidation in flight → host replaces/reloads the session → any ctx-touching call throws the stale error → string-match classifies it as lifecycle, not fault → outcome `deferred` → `add()`'s caller renders retry-instead-of-failure (existing contract from `consolidation-lock-ladder.md`) and the new session consolidates on its own next write.
**Invariant:** environment-invalidated work is a SKIP when the successor repeats it: the invariant that makes deferral safe is self-healing recurrence (consolidation runs on every write), so the ONLY correct response is to hand off, never to report an error the user cannot act on. Non-stale errors keep the old `Consolidation failed: …` shape truncated to 200 chars. The console warning for genuine failures is separately configurable (`autoConsolidationWarnOnFailure`) because users monitoring tool results do not need duplicate logging (#135).
**Probe:** `npx tsx --test tests/handlers/auto-consolidate.test.ts` — "defers instead of failing when pi.exec throws a stale extension ctx error" (:377, mock exec throws the verbatim stale message; asserts `result.deferred === true`). GREEN under `npx tsx --test`. Coverage caveat: `shouldWarnAutoConsolidationFailure` itself is a two-line gate exercised indirectly via index wiring; no dedicated unit test upstream.
**Retrieve:** `search_graph({ project: "pi-hermes-memory", query: "triggerConsolidation shouldWarnAutoConsolidationFailure deferred", limit: 5 })`

## Verdict
Adopt lifecycle-error classification into existing deferred channels wherever background work recurs naturally. Adapt the match string to your host's staleness message. Pair with `consolidation-lock-ladder.md` (contention deferral — same channel, different cause).
