<!-- capsule-v2 -->
# Suppressions ledger — how do you let teams commit a baseline of known violations and prune it as code improves?

**Source:** ESLint MIT `main@dc1e7a8416937edefe04cf836ee202a6fc03bedd`; Codebase Memory project `eslint`. **Question:** How does the suppressions file admit, count-match, and retire per-file/per-rule violation baselines?

## SuppressionsService lifecycle
**Path/Symbol:** `lib/services/suppressions-service.js:SuppressionsService` (:33–301) — `suppress(results, rules)` (:57–75), `prune(results)` (:85–126), `applySuppressions(results, suppressions)` (:142–208), `load()` (:215–231), static `countViolationsByRule(messages)` (:251), `getRelativeFilePath(filePath)` (:267), static `suppressMessagesByRule(result, ruleId)` (:280–300).
**Signature:** `applySuppressions(results, suppressions) → {results, unused}`; file shape `Record<relativePath, Record<ruleId, {count}>>`.
**Data Shape:** keys are CWD-relative POSIX paths (`path.relative(cwd).split(path.sep).join(path.posix.sep)`) so Windows and Unix produce identical files; only `severity === 2 && ruleId` messages count (warnings never suppressible).

### Decisive source
```js
// admission is ALL-OR-NOTHING per (file, rule):
if (violationsCount <= suppressionsCount) {
  SuppressionsService.suppressMessagesByRule(result, ruleId);  // move ALL matching messages out
  wasSuppressed = true;
}
if (violationsCount < suppressionsCount) {          // strict < ⇒ credit the difference
  unused[rel][rule] = { count: suppressionsCount - violationsCount };
}
// results are structuredClone'd first; suppressed messages get stamped:
message.suppressions = [{ kind: "file", justification: "" }];
```

**Flow:** load (ENOENT ⇒ `{}`; parse failure ⇒ wrapped Error with cause) → per result count violations by rule → ≤ ⇒ move that rule's messages to `suppressedMessages` and recalc stats via `calculateStatsPerFile`; < ⇒ record surplus in `unused`; unmatched suppression entries are unused wholesale → prune deletes exact-count rules, decrements partials, drops empty files AND files whose absolute path no longer exists.
**Invariant:** a baseline holds only while violations don't EXCEED it — one new error re-surfaces every message for that rule (fail-loud baseline breakage, not partial suppression), which forces the team to fix or explicitly re-baseline. `unused` is the garbage collector: prune consumes it to shrink the ledger. Stats must be RECALCULATED after moving messages or counts lie. Save uses stable stringify with 2-space indent for reviewable diffs.
**Probe:** `tests/lib/services/suppressions-service.js` (29 its — :792 suppress-on-equal-count + stamp shape; :829 exceed-reports-all; :858+ unused-credit; :67/:178/:527 load/save/prune suites).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "SuppressionsService applySuppressions prune countViolationsByRule", limit: 10 });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.services.suppressions-service.SuppressionsService.applySuppressions" });
```

## Verdict
Adopt the all-or-nothing admission + surplus-credit ledger for any baseline/ratchet feature (lint, types, bundle size); adapt storage format; omit POSIX normalization only if single-platform.
