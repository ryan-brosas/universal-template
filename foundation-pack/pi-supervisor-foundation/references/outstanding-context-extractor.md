<!-- capsule-v2 -->
# Outstanding-context extractor — six prioritized blocker detectors with tsc-resolution tagging and an 8-item cap

**Source:** ext-pi-supervisor MIT `master@92c0d6df986dfd138f941001e3fcc57a3ee07247`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-supervisor`. **Question:** How do you distill "what is currently broken" out of a noisy tail so an LLM judge sees unresolved problems first?

## Six detectors over the last 25 blocks
**Path/Symbol:** `src/compaction/build-sections.ts:97-250` (`extractOutstandingContext`), priority tagging :65-74, resolution detection :229-249.
**Signature:** `extractOutstandingContext(blocks: NormalizedBlock[]): string[]` — items capped at **8**, scanned window = last 25 blocks.
**Data Shape:** Tagged strings `[ERROR]/[WARN]/[INFO]` (+ `[RESOLVED]` override); bash-output scan head-capped at `BASH_OUTPUT_SCAN_LIMIT = 8_000`.

### Decisive source
```ts
    // 1. Bash non-zero exit codes ...
    if (b.kind === 'bash' && b.exitCode !== undefined && b.exitCode !== 0) {...}
    // 2. TypeScript compiler errors in bash output (first BASH_OUTPUT_SCAN_LIMIT chars)
    ...if (TSC_ERROR_RE.test(outputHead)) {...}
    // 3. Test failures in bash output
    // 4. Empty grep/search results ("searched for something that wasn't found = signal")
    // 5. Tool errors — classify tsc/test failures before generic catch
    // 6. BLOCKER_RE text matching (user/assistant mentions of problems)
```
Resolution tagging (:229-249): edit positions collected FIRST, then any `[tsc]` item whose error-file was edited at a LATER tail position gets its tag rewritten:
```ts
  return items.slice(0, 8).map((item, idx) => {
    const resolved = tailIdx >= 0 && file !== null && isTscResolved(file, tailIdx, editPositions);
    if (!resolved) return priorityTag(item);
    const tagged = priorityTag(item);
    return tagged.replace(/^\[(ERROR|WARN)\]/, '[RESOLVED]');
  });
```
BLOCKER prose guard (:212-224): line ≥15 chars, not a bullet/quote continuation, must start capitalized — kills false positives on pasted fragments.

**Flow:** walk tail → collect deduped items with their tail indices → build edit-position map → tag priorities → rewrite tsc errors fixed by later edits to [RESOLVED].
**Invariant:** Detector order matters (specific before generic: tsc inside tool errors is classified BEFORE the generic error catch). Empty search results count as signal — a porter who drops arm 4 loses "the thing you asked for doesn't exist". The 8-cap applies AFTER tagging so resolution rewrites can't push items out.
**Probe:** `grep -cn "slice(-25)\|slice(0, 8)" src/compaction/build-sections.ts` → 2; `grep -c "\[RESOLVED\]" src/compaction/build-sections.ts` → 2. Direct test: `tests/full-fidelity-snapshot.test.ts:172` "captures tool errors in outstanding context".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-supervisor", query: "extractOutstandingContext priority tags tsc resolved", limit: 10 });
```

## Verdict
Adopt prioritized multi-detector outstanding-context extraction with temporal resolution marking. Adapt detector set to your host's failure surface (exit codes, test runners, linters) and BLOCKER vocabulary. Omit the tsc-specific resolver only by replacing it with your own compile-error→fix pairing — the resolve-don't-repeat property is the point.
