<!-- capsule-v2 -->
# streamed-runs-reuse — when can the final document skip recomputing the diff, and why does whitespace mode opt out?

**Source:** oh-my-pi MIT `main@2b66ee69f2`; Codebase Memory `oh-my-pi`. **Question:** The native differ already computed exact runs during streaming — when does `buildDiffDocument` trust them, and when must it recompute?

## buildDiffDocument streamResult path
**Path/Symbol:** `packages/coding-agent/src/cli/git-tui/diff-pane.ts` (`buildDiffDocument`, `DiffBuildOptions.streamResult`).
**Signature:** `buildDiffDocument(oldRaw: string, newRaw: string, filePath: string, options: DiffBuildOptions = {}): DiffDocument` with `streamResult?: DiffStreamResult`.
**Data Shape:** `streamResult.runs = DiffRun[] { count, added, removed }` over interned lines (exact code-unit equality); `DIFF_CONTEXT_LINES = 3` is the context budget requested from the native finish.

### Decisive source
```ts
const streamed = ignoreWs ? undefined : options.streamResult;
```
plus the walk: removed runs push `pendingDel`, added runs push `pendingAdd`, an equal run first `flush()`es the pending block into paired `change` rows and then emits `context` rows.

**Flow:** With whitespace mode off and a `streamResult` present, rows come from walking the precomputed runs (del/add blocks flushed exactly at equal-run boundaries — same pairing as the hunk walker); with whitespace-ignore on, the alignment basis is TRIMMED lines, which can produce a DIFFERENT alignment than the native raw-line diff, so the runs are discarded and the synchronous path recomputes. Hunk patching is disabled in that mode (`patchable === false`: "False when built with whitespace-ignore: hunk patches would not apply").
**Invariant:** A reused `streamResult` must have been computed from EXACTLY the two texts being rendered (`stream.text(side)` snapshots taken in the same `FileContents` that carries the result) — mixing a stale result with re-read texts silently misnumbers every row.
**Probe:** `grep -nF 'const streamed = ignoreWs ? undefined : options.streamResult;' packages/coding-agent/src/cli/git-tui/diff-pane.ts` → line `326` and `grep -nF 'hunk patches would not apply' packages/coding-agent/src/cli/git-tui/diff-pane.ts` → line `69`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "buildDiffDocument streamResult runs ignoreWs whitespace", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt run-walking + reuse gating; adapt row/pairing types; omit formatting-demotion (`demoteBlock`) unless you port whitespace modes too. Coverage caveat: reuse path exercised by git-tui-stream integration tests rather than a dedicated unit.
