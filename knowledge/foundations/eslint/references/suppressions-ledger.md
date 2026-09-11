<!-- capsule-v2 -->
# Suppressions ledger — how do you let teams commit a baseline of known violations and prune it as code improves?

**Source:** ESLint MIT `main@c27bc926e496985eb7911c09eb60914b2e4b5d0f` (pin rebased from dc1e7a84, pass 13); Codebase Memory project `eslint`. **Question:** How does the suppressions file admit, count-match, and retire per-file/per-rule violation baselines — and who calls it?

## SuppressionsService lifecycle
**Path/Symbol:** `lib/services/suppressions-service.js:SuppressionsService` (:33–303 at the current pin) — `suppress(results, rules)` (:57–77), `prune(results)` (:85–127), `applySuppressions(results, suppressions)` (:142–208), `load()` (:215–231), `save(suppressions)` (:239), static `countViolationsByRule(messages)` (:251), `getRelativeFilePath(filePath)` (:267), static `suppressMessagesByRule(result, ruleId)` (:280–300). Call sites: `lib/eslint/eslint.js` constructor wiring (:740–751, "suppressions_" cache-file prefix) + lintFiles tail (:1083–1092) + lintText gate (:1206–1216, `!filePath || !applySuppressions`); `lib/cli.js` (:397–444 file-location resolution, suppress/prune/apply sequencing; :497–509 unused-suppressions exit-2 with `--pass-on-unpruned-suppressions` bypass).
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
**Probe:** `tests/lib/services/suppressions-service.js` (29 passing at the current pin — :792 suppress-on-equal-count + stamp shape; :829 exceed-reports-all; :858+ unused-credit; :67/:178/:527 load/save/prune suites). Live probe (pass 13, node -e at the pin): all four admission arms — violations==count ⇒ suppressed + empty unused; violations<count ⇒ suppressed + unused credit; violations>count ⇒ NOTHING suppressed (fail-loud); unmatched entry ⇒ unused wholesale; stamp `[{kind:"file",justification:""}]`; `getRelativeFilePath("/tmp/sub/dir/x.js")` ⇒ `sub/dir/x.js`; warnings never counted. End-to-end: `suppress()` writes the baseline with POSIX keys + 2-space stringify; an ESLint-class run with `applySuppressions: true` + `suppressionsLocation` moves the violation to `suppressedMessages` with the file-kind stamp. NOTE: `suppressAllErrors` is NOT an ESLint-class option at this pin (throws ESLintInvalidOptionsError "Unknown options"); the correct surface is `applySuppressions` + `suppressionsLocation`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "SuppressionsService applySuppressions prune countViolationsByRule", limit: 10 });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.services.suppressions-service.SuppressionsService.applySuppressions" });
```

## Verdict
Adopt the all-or-nothing admission + surplus-credit ledger for any baseline/ratchet feature (lint, types, bundle size); adapt storage format; omit POSIX normalization only if single-platform. Pass-13 re-verification: every claim re-checked at the current pin (line anchors updated; behavior unchanged); the ESLint-class and CLI call-site planes folded into Flow/Path prose — no separate call-site capsule needed. Caveat: Codebase Memory MCP was not connected in the mining session; anchors verified by direct byte-matched source reads at the git-clean pin.
