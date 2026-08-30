<!-- capsule-v2 -->
# Severity normalization + message counting — how do you keep error/warning/fixable tallies honest across three severity spellings?

**Source:** ESLint MIT `main@dc1e7a8416937edefe04cf836ee202a6fc03bedd`; Codebase Memory project `eslint`. **Question:** What is the canonical mapping between 0/1/2, "off"/"warn"/"error", and the per-file stat block?

## severity.js + message-counts.js
**Path/Symbol:** `lib/shared/severity.js:normalizeSeverityToString / normalizeSeverityToNumber` (:14–41 / :33–44) + `lib/shared/message-counts.js:calculateStatsPerFile(messages)` (:14–44).
**Signature:** both normalizers accept `0|"0"|"off"`, `1|"1"|"warn"`, `2|"2"|"error"` and THROW on anything else; `calculateStatsPerFile(messages) → {errorCount, fatalErrorCount, warningCount, fixableErrorCount, fixableWarningCount}`.
**Data Shape:** membership arrays (`[2,"2","error"]`) make numeric-string duality explicit; stats classify by `message.fatal || message.severity === 2`.

### Decisive source
```js
for (let i = 0; i < messages.length; i++) {
  const message = messages[i];
  if (message.fatal || message.severity === 2) {
    stat.errorCount++;
    if (message.fatal) stat.fatalErrorCount++;
    if (message.fix) stat.fixableErrorCount++;
  } else {
    stat.warningCount++;
    if (message.fix) stat.fixableWarningCount++;
  }
}
```

**Flow:** normalize at config edges (rule settings, inline comments, CLI flags) → store canonical form → count once at result assembly.
**Invariant:** FATAL parsing errors count as errors EVEN IF their stored severity is somehow not 2 (`message.fatal ||` guard first) — a parse failure must never masquerade as a warning. Fixable counts are computed per-severity-bucket from the presence of `.fix`, so "N problems (M fixable)" stays consistent after suppressions only if stats are RECALCULATED post-filter (suppressions ledger does exactly this). The throw-on-unknown contract means callers can rely on exhaustiveness instead of defaulting silently to "error".
**Probe:** `tests/lib/shared/severity.js` (:23–46 full 9-entry table + invalid-value throw); `tests/lib/shared/message-counts.js` (:21 zero-counts; :31 mixed counts; :50 fatal-as-error-even-at-warning-severity).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "normalizeSeverityToNumber calculateStatsPerFile", limit: 10 });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.shared.message_counts.calculateStatsPerFile" });
```

## Verdict
Adopt the dual-spelling normalizer with loud failure for any severity/log-level system; adopt fatal-first classification for diagnostic tallying; adapt field names.
