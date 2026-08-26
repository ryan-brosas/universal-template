<!-- capsule-v2 -->
# JSONL append-only source of truth — how does experiment state survive restarts without a DB?

**Source:** pi-autoresearch-harness MIT `main@511760df8905c7b6e6bbd3a028de734becff69e6`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-autoresearch-harness`. **Question:** Where does authoritative experiment state live, which writes create vs extend it, and what must a porter preserve so manual edits stay legal?

## dispatchAction init/log — write-once header, forever-append runs
**Path/Symbol:** `harness/server.ts:dispatchAction` (`init` :855–877, `log` persist :1364–1372).
**Signature:** `fs.writeFileSync(jsonlPath, config+'\n')` on first init; `fs.appendFileSync(jsonlPath, config+'\n')` on re-init; every logged run appends.
**Data Shape:** line 1..n: `{type:'config', name, metric_name, metric_unit, direction, target_value, max_experiments, segment}` headers interleaved with `{run, commit, metric, metrics, status, description, timestamp, segment, confidence, asi?}` results; one JSON object per line.

### Decisive source
```ts
// server.ts:867-871 — first init REPLACES the file; re-init APPENDS a new config header
if (isReinit) {
  fs.appendFileSync(jsonlPath, config + '\n');
} else {
  fs.writeFileSync(jsonlPath, config + '\n');
}
// server.ts:1367-1369 — run entries are always appended; asi omitted when empty
const jsonlEntry: Record<string, unknown> = { run: state.results.length, ...experiment };
if (!experiment.asi) delete jsonlEntry.asi;
fs.appendFileSync(jsonlPath, JSON.stringify(jsonlEntry) + '\n');
```

**Flow:** init (no file) → writeFileSync config → log appends run lines → re-init detects existing file (`isReinit = fs.existsSync(jsonlPath)` :840) → appends NEW config header (old results stay on disk as archive) → reconstructStateFromJsonl (:638–711) replays ALL lines top-to-bottom: config headers overwrite state fields, run lines push to `state.results`, malformed lines skipped silently (`catch {}` :690), corrupted whole file ⇒ fresh empty state.
**Invariant:** the JSONL is the ONLY persistence — there is no database and no session-history fallback (`docs/jsonl-source-of-truth.md`: "State is never reconstructed from pi session message history"). Deleting the file deletes the experiment. Manual edits are supported BY DESIGN: the extension watches the file (500ms poll) and rebuilds UI state from disk, so hand-edits appear in real time. A porter who adds any second source of truth breaks the crash-resume contract.
**Probe:** anchors: `grep -n 'appendFileSync' harness/server.ts` → :470 (gitignore), :868 (re-init config), :1369 (run entries), :1584 (server log); `grep -n 'writeFileSync(jsonlPath' harness/server.ts` → exactly :870 (first-init only); `grep -n 'session.state.bestMetric = session.state.results\[0\]' harness/server.ts` → :696 (reconstruction) and its updateStateAfterLog twin at :319 reads `state.bestMetric = state.results[0]?.metric ?? null`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-autoresearch-harness", query: "reconstructStateFromJsonl autoresearch.jsonl config header", limit: 10 });
```

## Verdict
Adopt the single-file append-only protocol verbatim (write-once header + append-only runs + silent-skip replay); adapt file paths/watch mechanism to host; omit pi-specific session-id bridging. Coverage caveat: reconstruction logic itself has no direct vitest driving `server.ts` (server-side copy untested); the extension-side mirror is exercised by `__tests__/unit/jsonl.test.ts` ('JSONL reconstruction', 'handles malformed JSONL lines by skipping them').
